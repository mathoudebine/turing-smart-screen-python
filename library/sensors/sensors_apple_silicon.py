# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
# Copyright (C) 2024 Carl (tamingchaos)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Apple Silicon sensor provider using three data sources:
# 1. SMC (System Management Controller) via IOKit/ctypes - temperatures, fans
# 2. IOReport via libIOReport.dylib - power/energy, CPU/GPU P-state residency
# 3. ioreg AGXAccelerator - GPU utilization %, GPU memory

import ctypes
import math
import re
import struct
import subprocess
import threading
import time
from typing import Tuple

import psutil

import library.sensors.sensors as sensors
from library.log import logger

PNIC_BEFORE = {}


class _SMCReader:
    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._conn = None
        self._smc_lock = threading.Lock()
        self._iokit = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
        self._cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self._setup_functions()
        self._open()

    def _setup_functions(self):
        iokit = self._iokit
        cf = self._cf

        cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFRelease.argtypes = [ctypes.c_void_p]

        iokit.IOServiceMatching.restype = ctypes.c_void_p
        iokit.IOServiceMatching.argtypes = [ctypes.c_char_p]
        iokit.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        iokit.IOServiceGetMatchingService.restype = ctypes.c_uint32
        iokit.IOServiceOpen.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
        iokit.IOServiceOpen.restype = ctypes.c_uint32
        iokit.IOServiceClose.argtypes = [ctypes.c_uint32]
        iokit.IOServiceClose.restype = ctypes.c_uint32

        self._mach_task_self = ctypes.cdll.LoadLibrary('/usr/lib/libSystem.B.dylib').mach_task_self
        self._mach_task_self.restype = ctypes.c_uint32

        iokit.IOConnectCallStructMethod.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_size_t,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)
        ]
        iokit.IOConnectCallStructMethod.restype = ctypes.c_uint32

    def _open(self):
        matching = self._iokit.IOServiceMatching(b"AppleSMC")
        if not matching:
            logger.warning("Apple SMC service not found")
            return
        service = self._iokit.IOServiceGetMatchingService(0, matching)
        if not service:
            logger.warning("Could not get Apple SMC service")
            return
        conn = ctypes.c_uint32()
        result = self._iokit.IOServiceOpen(service, self._mach_task_self(), 0, ctypes.byref(conn))
        if result != 0:
            logger.warning(f"Could not open Apple SMC connection: {result:#x}")
            return
        self._conn = conn.value

    def _fcc(self, s):
        return int.from_bytes(s.encode('ascii'), byteorder='big')

    def _smc_call(self, buf):
        out = bytearray(80)
        out_size = ctypes.c_size_t(80)
        result = self._iokit.IOConnectCallStructMethod(
            self._conn, 2,
            (ctypes.c_uint8 * 80).from_buffer(buf), 80,
            (ctypes.c_uint8 * 80).from_buffer(out), ctypes.byref(out_size)
        )
        return result, out

    def read_key(self, key_name):
        if not self._conn:
            return None
        with self._smc_lock:
            try:
                buf = bytearray(80)
                struct.pack_into('<I', buf, 0, self._fcc(key_name))
                buf[42] = 9  # getKeyInfo
                r, info = self._smc_call(buf)
                if r != 0 or info[40] != 0:
                    return None
                ki = info[26:42]
                ds = struct.unpack_from('<I', info, 28)[0]
                if ds == 0:
                    return None
                dt = info[32:36]

                buf2 = bytearray(80)
                struct.pack_into('<I', buf2, 0, self._fcc(key_name))
                buf2[42] = 5  # readKey
                for i, b in enumerate(ki):
                    buf2[26 + i] = b
                r2, val = self._smc_call(buf2)
                if r2 != 0 or val[40] != 0:
                    return None

                raw = val[48:48 + ds]
                dt_str = bytes(reversed(dt)).decode('ascii', errors='replace').strip('\x00')

                if dt_str == 'flt ' and ds == 4:
                    return struct.unpack('<f', raw)[0]
                elif dt_str == 'ui8 ' and ds == 1:
                    return raw[0]
                elif dt_str == 'ui16' and ds == 2:
                    return struct.unpack('>H', raw)[0]
                elif dt_str == 'ui32' and ds == 4:
                    return struct.unpack('>I', raw)[0]
                elif dt_str == 'sp78' and ds == 2:
                    return struct.unpack('>h', raw)[0] / 256.0
                elif dt_str == 'fpe2' and ds == 2:
                    return struct.unpack('>H', raw)[0] / 4.0
                else:
                    return raw
            except Exception as e:
                logger.debug(f"SMC read error for key '{key_name}': {e}")
                return None

    def read_float(self, key_name):
        val = self.read_key(key_name)
        if isinstance(val, (int, float)):
            return float(val)
        return math.nan

    def read_temp_max(self, prefix):
        max_temp = math.nan
        for suffix in range(20):
            for c in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                       'a', 'b', 'c', 'd', 'e', 'f']:
                key = f"{prefix}{suffix:01d}{c}"
                if len(key) != 4:
                    continue
                val = self.read_float(key)
                if not math.isnan(val) and 0 < val < 150:
                    if math.isnan(max_temp) or val > max_temp:
                        max_temp = val
        return max_temp


class _IOReportReader:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._available = False
        self._sub = None
        self._channels = None
        self._last_sample = None
        self._last_delta = None
        self._last_time = None
        self._sample_interval = 1.0
        self._data_lock = threading.Lock()
        self._parsed = {}

        try:
            self._iorep = ctypes.cdll.LoadLibrary('/usr/lib/libIOReport.dylib')
            self._cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
            self._setup_functions()
            self._subscribe()
            if self._sub:
                self._available = True
                self._take_initial_sample()
                self._start_background_sampling()
        except Exception as e:
            logger.warning(f"IOReport not available: {e}")

    def _setup_functions(self):
        cf = self._cf
        iorep = self._iorep

        cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        cf.CFDictionaryGetCount.argtypes = [ctypes.c_void_p]
        cf.CFDictionaryGetCount.restype = ctypes.c_long
        cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
        cf.CFArrayGetCount.restype = ctypes.c_long
        cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
        cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
        cf.CFGetTypeID.argtypes = [ctypes.c_void_p]
        cf.CFGetTypeID.restype = ctypes.c_ulong
        cf.CFArrayGetTypeID.restype = ctypes.c_ulong
        cf.CFDictionaryGetTypeID.restype = ctypes.c_ulong
        cf.CFStringGetCStringPtr.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        cf.CFStringGetCStringPtr.restype = ctypes.c_char_p
        cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        cf.CFNumberGetValue.restype = ctypes.c_bool

        cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cf.CFDictionaryGetValue.restype = ctypes.c_void_p

        iorep.IOReportCopyChannelsInGroup.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64]
        iorep.IOReportCopyChannelsInGroup.restype = ctypes.c_void_p
        iorep.IOReportMergeChannels.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        iorep.IOReportMergeChannels.restype = None
        iorep.IOReportCreateSubscription.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint64, ctypes.c_void_p]
        iorep.IOReportCreateSubscription.restype = ctypes.c_void_p
        iorep.IOReportCreateSamples.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        iorep.IOReportCreateSamples.restype = ctypes.c_void_p
        iorep.IOReportCreateSamplesDelta.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        iorep.IOReportCreateSamplesDelta.restype = ctypes.c_void_p

        iorep.IOReportChannelGetGroup.argtypes = [ctypes.c_void_p]
        iorep.IOReportChannelGetGroup.restype = ctypes.c_void_p
        iorep.IOReportChannelGetChannelName.argtypes = [ctypes.c_void_p]
        iorep.IOReportChannelGetChannelName.restype = ctypes.c_void_p
        iorep.IOReportSimpleGetIntegerValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        iorep.IOReportSimpleGetIntegerValue.restype = ctypes.c_int64
        iorep.IOReportChannelGetFormat.argtypes = [ctypes.c_void_p]
        iorep.IOReportChannelGetFormat.restype = ctypes.c_uint32
        iorep.IOReportStateGetCount.argtypes = [ctypes.c_void_p]
        iorep.IOReportStateGetCount.restype = ctypes.c_int32
        iorep.IOReportStateGetResidency.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        iorep.IOReportStateGetResidency.restype = ctypes.c_int64
        iorep.IOReportStateGetNameForIndex.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        iorep.IOReportStateGetNameForIndex.restype = ctypes.c_void_p

    def _make_cfstr(self, s):
        return self._cf.CFStringCreateWithCString(None, s.encode('utf-8'), 0x08000100)

    def _cfstr_to_str(self, cfstr):
        if not cfstr:
            return ""
        ptr = self._cf.CFStringGetCStringPtr(cfstr, 0x08000100)
        if ptr:
            return ptr.decode('utf-8', errors='replace')
        buf = ctypes.create_string_buffer(256)
        if self._cf.CFStringGetCString(cfstr, buf, 256, 0x08000100):
            return buf.value.decode('utf-8', errors='replace')
        return ""

    def _subscribe(self):
        groups = ["Energy Model", "CPU Stats", "GPU Stats"]
        merged = None
        for g in groups:
            cfg = self._make_cfstr(g)
            ch = self._iorep.IOReportCopyChannelsInGroup(cfg, None, 0, 0, 0)
            self._cf.CFRelease(cfg)
            if ch:
                if merged is None:
                    merged = ch
                else:
                    self._iorep.IOReportMergeChannels(merged, ch, None)

        if not merged:
            logger.warning("IOReport: no channels found")
            return

        sub_channels = ctypes.c_void_p()
        self._sub = self._iorep.IOReportCreateSubscription(
            None, merged, ctypes.byref(sub_channels), 0, None
        )
        self._channels = sub_channels.value if sub_channels.value else merged

    def _take_initial_sample(self):
        self._last_sample = self._iorep.IOReportCreateSamples(self._sub, self._channels, None)
        self._last_time = time.monotonic()

    def _start_background_sampling(self):
        t = threading.Thread(target=self._sample_loop, daemon=True)
        t.start()

    def _sample_loop(self):
        while True:
            time.sleep(self._sample_interval)
            try:
                new_sample = self._iorep.IOReportCreateSamples(self._sub, self._channels, None)
                if not new_sample:
                    continue
                now = time.monotonic()
                delta = self._iorep.IOReportCreateSamplesDelta(self._last_sample, new_sample, None)
                dt = now - self._last_time

                if delta:
                    parsed = self._parse_delta(delta, dt)
                    with self._data_lock:
                        self._parsed = parsed
                        self._last_delta = delta
                    self._cf.CFRelease(self._last_sample)
                else:
                    self._cf.CFRelease(self._last_sample)

                self._last_sample = new_sample
                self._last_time = now
            except Exception as e:
                logger.debug(f"IOReport sample error: {e}")

    def _parse_delta(self, delta, dt):
        result = {
            'energy': {},
            'cpu_freq': math.nan,
            'gpu_freq': math.nan,
            'cpu_power': math.nan,
            'gpu_power': math.nan,
            'dram_power': math.nan,
            'total_power': math.nan,
        }

        cf = self._cf
        iorep = self._iorep
        arr_type_id = cf.CFArrayGetTypeID()

        items_key = self._make_cfstr("IOReportChannels")
        channels_arr = cf.CFDictionaryGetValue(delta, items_key)
        cf.CFRelease(items_key)
        if not channels_arr:
            return result
        if cf.CFGetTypeID(channels_arr) != arr_type_id:
            return result

        count = cf.CFArrayGetCount(channels_arr)
        energy_values = {}
        cpu_residencies = {}
        gpu_residencies = {}

        SIMPLE_FORMAT = 1
        STATE_FORMAT = 2

        for i in range(count):
            ch = cf.CFArrayGetValueAtIndex(channels_arr, i)
            if not ch:
                continue
            group_cf = iorep.IOReportChannelGetGroup(ch)
            name_cf = iorep.IOReportChannelGetChannelName(ch)
            group = self._cfstr_to_str(group_cf)
            name = self._cfstr_to_str(name_cf)
            fmt = iorep.IOReportChannelGetFormat(ch)

            if group == "Energy Model" and fmt == SIMPLE_FORMAT:
                val = iorep.IOReportSimpleGetIntegerValue(ch, None)
                energy_values[name] = val

            elif "CPU Stats" in group and fmt == STATE_FORMAT:
                state_count = iorep.IOReportStateGetCount(ch)
                if state_count > 0:
                    states = {}
                    for si in range(state_count):
                        residency = iorep.IOReportStateGetResidency(ch, si)
                        sname_cf = iorep.IOReportStateGetNameForIndex(ch, si)
                        sname = self._cfstr_to_str(sname_cf)
                        states[sname] = residency
                    cpu_residencies[name] = states

            elif "GPU Stats" in group and fmt == STATE_FORMAT:
                state_count = iorep.IOReportStateGetCount(ch)
                if state_count > 0:
                    states = {}
                    for si in range(state_count):
                        residency = iorep.IOReportStateGetResidency(ch, si)
                        sname_cf = iorep.IOReportStateGetNameForIndex(ch, si)
                        sname = self._cfstr_to_str(sname_cf)
                        states[sname] = residency
                    gpu_residencies[name] = states

        result['energy'] = energy_values

        cpu_total_energy = 0
        gpu_total_energy = 0
        dram_total_energy = 0
        for k, v in energy_values.items():
            kl = k.lower()
            if 'cpu' in kl and ('acc' in kl or k.startswith('EACC') or k.startswith('PACC')):
                cpu_total_energy += v
            elif 'gpu' in kl and k != 'GPU Energy':
                gpu_total_energy += v
            elif 'dram' in kl or 'dcs' in kl:
                dram_total_energy += v

        if 'CPU Energy' in energy_values:
            cpu_total_energy = energy_values['CPU Energy']
        if 'GPU Energy' in energy_values:
            gpu_total_energy = energy_values['GPU Energy']

        if dt > 0:
            scale = 1e-3 / dt
            if cpu_total_energy > 0:
                result['cpu_power'] = cpu_total_energy * scale
            if gpu_total_energy > 0:
                result['gpu_power'] = gpu_total_energy * scale
            if dram_total_energy > 0:
                result['dram_power'] = dram_total_energy * scale
            total = cpu_total_energy + gpu_total_energy + dram_total_energy
            if total > 0:
                result['total_power'] = total * scale

        return result

    def get_data(self):
        with self._data_lock:
            return dict(self._parsed)


class _AGXReader:
    _instance = None
    _lock = threading.Lock()
    _TTL = 2.0

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._cache = {}
        self._cache_time = 0
        self._data_lock = threading.Lock()

    def _parse_value(self, val):
        val = val.strip()
        if val.isdigit():
            return int(val)
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        try:
            return float(val)
        except ValueError:
            return val

    def _parse_inline_dict(self, s):
        result = {}
        s = s.strip()
        if s.startswith('{') and s.endswith('}'):
            s = s[1:-1]
        for part in re.finditer(r'"([^"]+)"=([^,}]+)', s):
            key, val = part.group(1), part.group(2)
            result[key] = self._parse_value(val)
        return result

    def _refresh(self):
        now = time.monotonic()
        if now - self._cache_time < self._TTL:
            return
        try:
            result = subprocess.run(
                ['ioreg', '-c', 'AGXAccelerator', '-r', '-d', '2'],
                capture_output=True, text=True, timeout=5
            )
            data = {}
            for line in result.stdout.split('\n'):
                line = line.lstrip('| \t')
                m = re.match(r'"([^"]+)"\s*=\s*(.+)', line)
                if m:
                    key, val = m.group(1), m.group(2).strip()
                    if val.startswith('{') and '=' in val:
                        for k, v in self._parse_inline_dict(val).items():
                            data[k] = v
                    else:
                        data[key] = self._parse_value(val)
            with self._data_lock:
                self._cache = data
                self._cache_time = now
        except Exception as e:
            logger.debug(f"AGX ioreg read error: {e}")

    def get(self, key, default=None):
        self._refresh()
        with self._data_lock:
            return self._cache.get(key, default)


_smc = None
_ioreport = None
_agx = None

_MIN_CPU_TEMP = 15.0
_MIN_GPU_TEMP = 10.0
_last_good_cpu_temp = math.nan
_last_good_gpu_temp = math.nan
_temp_lock = threading.Lock()


def _get_smc():
    global _smc
    if _smc is None:
        _smc = _SMCReader()
    return _smc


def _get_ioreport():
    global _ioreport
    if _ioreport is None:
        _ioreport = _IOReportReader()
    return _ioreport


def _get_agx():
    global _agx
    if _agx is None:
        _agx = _AGXReader()
    return _agx


class Cpu(sensors.Cpu):
    @staticmethod
    def percentage(interval: float) -> float:
        try:
            return psutil.cpu_percent(interval=interval)
        except:
            return math.nan

    @staticmethod
    def frequency() -> float:
        try:
            return psutil.cpu_freq().current
        except:
            return math.nan

    @staticmethod
    def load() -> Tuple[float, float, float]:
        try:
            return psutil.getloadavg()
        except:
            return math.nan, math.nan, math.nan

    @staticmethod
    def temperature() -> float:
        global _last_good_cpu_temp
        smc = _get_smc()
        best = math.nan
        raw_best = math.nan
        for key in ['Tp09', 'Tp01', 'Tp05', 'Tp0D']:
            val = smc.read_float(key)
            if not math.isnan(val) and 0 < val < 150:
                if math.isnan(raw_best) or val > raw_best:
                    raw_best = val
                if val > _MIN_CPU_TEMP:
                    if math.isnan(best) or val > best:
                        best = val
        with _temp_lock:
            if not math.isnan(best):
                _last_good_cpu_temp = best
            elif not math.isnan(_last_good_cpu_temp):
                best = _last_good_cpu_temp
            elif not math.isnan(raw_best):
                best = raw_best
        return best

    @staticmethod
    def fan_percent(fan_name: str = None) -> float:
        smc = _get_smc()
        actual = smc.read_float('F0Ac')
        if math.isnan(actual):
            return math.nan
        mn = smc.read_float('F0Mn')
        mx = smc.read_float('F0Mx')
        if math.isnan(mn) or math.isnan(mx) or mx <= mn:
            return math.nan
        if actual <= 0:
            return 0.0
        pct = (actual - mn) / (mx - mn) * 100
        return max(0, min(100, pct))


class Gpu(sensors.Gpu):
    @staticmethod
    def stats() -> Tuple[float, float, float, float, float]:
        agx = _get_agx()
        smc = _get_smc()

        load = agx.get('Device Utilization %', math.nan)
        if not isinstance(load, (int, float)):
            load = math.nan

        in_use = agx.get('In use system memory', 0)
        alloc = agx.get('Alloc system memory', 0)
        if isinstance(in_use, (int, float)) and isinstance(alloc, (int, float)) and alloc > 0:
            mem_used_mb = in_use / (1024 * 1024)
            mem_total_mb = alloc / (1024 * 1024)
            mem_pct = (in_use / alloc) * 100
        else:
            mem_used_mb = math.nan
            mem_total_mb = math.nan
            mem_pct = math.nan

        global _last_good_gpu_temp
        temp = math.nan
        raw_best = math.nan
        for key in ['Tg0f', 'Tg0j', 'Tg0D', 'Tg05', 'Tg09', 'Tg01']:
            val = smc.read_float(key)
            if not math.isnan(val) and 0 < val < 150:
                if math.isnan(raw_best) or val > raw_best:
                    raw_best = val
                if val > _MIN_GPU_TEMP:
                    if math.isnan(temp) or val > temp:
                        temp = val
        with _temp_lock:
            if not math.isnan(temp):
                _last_good_gpu_temp = temp
            elif not math.isnan(_last_good_gpu_temp):
                temp = _last_good_gpu_temp
            elif not math.isnan(raw_best):
                temp = raw_best

        return float(load), float(mem_pct), float(mem_used_mb), float(mem_total_mb), float(temp)

    @staticmethod
    def fps() -> int:
        return -1

    @staticmethod
    def fan_percent() -> float:
        return math.nan

    @staticmethod
    def frequency() -> float:
        return math.nan

    @staticmethod
    def is_available() -> bool:
        agx = _get_agx()
        model = agx.get('model', '')
        if model:
            logger.info(f"Detected Apple GPU: {model} ({agx.get('gpu-core-count', '?')} cores)")
            return True
        return False


class Memory(sensors.Memory):
    @staticmethod
    def swap_percent() -> float:
        try:
            return psutil.swap_memory().percent
        except:
            return math.nan

    @staticmethod
    def virtual_percent() -> float:
        try:
            return psutil.virtual_memory().percent
        except:
            return math.nan

    @staticmethod
    def virtual_used() -> int:
        try:
            return psutil.virtual_memory().total - psutil.virtual_memory().available
        except:
            return -1

    @staticmethod
    def virtual_free() -> int:
        try:
            return psutil.virtual_memory().available
        except:
            return -1


class Disk(sensors.Disk):
    @staticmethod
    def disk_usage_percent() -> float:
        try:
            return psutil.disk_usage("/").percent
        except:
            return math.nan

    @staticmethod
    def disk_used() -> int:
        try:
            return psutil.disk_usage("/").used
        except:
            return -1

    @staticmethod
    def disk_free() -> int:
        try:
            return psutil.disk_usage("/").free
        except:
            return -1


class Net(sensors.Net):
    @staticmethod
    def stats(if_name, interval) -> Tuple[int, int, int, int]:
        try:
            pnic_after = psutil.net_io_counters(pernic=True)
            upload_rate = 0
            uploaded = 0
            download_rate = 0
            downloaded = 0

            if if_name != "":
                if if_name in pnic_after:
                    try:
                        upload_rate = (pnic_after[if_name].bytes_sent - PNIC_BEFORE[if_name].bytes_sent) / interval
                        uploaded = pnic_after[if_name].bytes_sent
                        download_rate = (pnic_after[if_name].bytes_recv - PNIC_BEFORE[if_name].bytes_recv) / interval
                        downloaded = pnic_after[if_name].bytes_recv
                    except:
                        pass
                    PNIC_BEFORE.update({if_name: pnic_after[if_name]})
                else:
                    logger.warning("Network interface '%s' not found. Check names in config.yaml." % if_name)

            return upload_rate, uploaded, download_rate, downloaded
        except:
            return -1, -1, -1, -1
