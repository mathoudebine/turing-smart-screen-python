# SPDX-License-Identifier: GPL-3.0-or-later
#
# Apple Silicon CPU / GPU sensors, without sudo.
#
# Frequencies: psutil.cpu_freq() returns placeholder values on Apple Silicon, and GPUtil/pyamdgpuinfo don't know
# the Apple GPU. Like macmon, this reads the private IOReport framework ("CPU Stats" / "CPU Complex Performance
# States" and "GPU Stats" / "GPU Performance States"), which gives how long each CPU cluster / the GPU spent in
# each DVFS state since the last sample. The frequency of each state comes from the pmgr device in the IORegistry
# (voltage-states*). Average frequency = residency-weighted mean over the active states.
#
# GPU load and memory: the "PerformanceStatistics" dictionary of the IOAccelerator service (as used by
# Activity Monitor): "Device Utilization %" and "In use system memory" (unified memory, in bytes).

import ctypes
import ctypes.util
import struct
from typing import Dict, List, Optional

_cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
_iokit = ctypes.CDLL(ctypes.util.find_library("IOKit"))
_ior = ctypes.CDLL("/usr/lib/libIOReport.dylib")

_vp = ctypes.c_void_p
kCFStringEncodingUTF8 = 0x08000100

_cf.CFStringCreateWithCString.restype = _vp
_cf.CFStringCreateWithCString.argtypes = [_vp, ctypes.c_char_p, ctypes.c_uint32]
_cf.CFStringGetCString.restype = ctypes.c_bool
_cf.CFStringGetCString.argtypes = [_vp, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
_cf.CFDictionaryGetValue.restype = _vp
_cf.CFDictionaryGetValue.argtypes = [_vp, _vp]
_cf.CFArrayGetCount.restype = ctypes.c_long
_cf.CFArrayGetCount.argtypes = [_vp]
_cf.CFArrayGetValueAtIndex.restype = _vp
_cf.CFArrayGetValueAtIndex.argtypes = [_vp, ctypes.c_long]
_cf.CFDataGetLength.restype = ctypes.c_long
_cf.CFDataGetLength.argtypes = [_vp]
_cf.CFDataGetBytePtr.restype = ctypes.POINTER(ctypes.c_ubyte)
_cf.CFDataGetBytePtr.argtypes = [_vp]
_cf.CFRelease.restype = None
_cf.CFRelease.argtypes = [_vp]
_cf.CFNumberGetValue.restype = ctypes.c_bool
_cf.CFNumberGetValue.argtypes = [_vp, ctypes.c_int, _vp]
kCFNumberSInt64Type = 4

_iokit.IOServiceMatching.restype = _vp
_iokit.IOServiceMatching.argtypes = [ctypes.c_char_p]
_iokit.IOServiceGetMatchingService.restype = ctypes.c_uint32
_iokit.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, _vp]
_iokit.IOServiceGetMatchingServices.restype = ctypes.c_int
_iokit.IOServiceGetMatchingServices.argtypes = [ctypes.c_uint32, _vp, ctypes.POINTER(ctypes.c_uint32)]
_iokit.IOIteratorNext.restype = ctypes.c_uint32
_iokit.IOIteratorNext.argtypes = [ctypes.c_uint32]
_iokit.IORegistryEntryGetName.restype = ctypes.c_int
_iokit.IORegistryEntryGetName.argtypes = [ctypes.c_uint32, ctypes.c_char_p]
_iokit.IORegistryEntryCreateCFProperty.restype = _vp
_iokit.IORegistryEntryCreateCFProperty.argtypes = [ctypes.c_uint32, _vp, _vp, ctypes.c_uint32]
_iokit.IOObjectRelease.restype = ctypes.c_int
_iokit.IOObjectRelease.argtypes = [ctypes.c_uint32]

_ior.IOReportCopyChannelsInGroup.restype = _vp
_ior.IOReportCopyChannelsInGroup.argtypes = [_vp, _vp, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64]
_ior.IOReportCreateSubscription.restype = _vp
_ior.IOReportCreateSubscription.argtypes = [_vp, _vp, ctypes.POINTER(_vp), ctypes.c_uint64, _vp]
_ior.IOReportCreateSamples.restype = _vp
_ior.IOReportCreateSamples.argtypes = [_vp, _vp, _vp]
_ior.IOReportCreateSamplesDelta.restype = _vp
_ior.IOReportCreateSamplesDelta.argtypes = [_vp, _vp, _vp]
for _name in ("IOReportChannelGetGroup", "IOReportChannelGetSubGroup", "IOReportChannelGetChannelName"):
    getattr(_ior, _name).restype = _vp
    getattr(_ior, _name).argtypes = [_vp]
_ior.IOReportStateGetCount.restype = ctypes.c_int32
_ior.IOReportStateGetCount.argtypes = [_vp]
_ior.IOReportStateGetNameForIndex.restype = _vp
_ior.IOReportStateGetNameForIndex.argtypes = [_vp, ctypes.c_int32]
_ior.IOReportStateGetResidency.restype = ctypes.c_int64
_ior.IOReportStateGetResidency.argtypes = [_vp, ctypes.c_int32]

_IDLE_STATES = {"IDLE", "DOWN", "OFF"}


def _cfstr(s: str):
    return _cf.CFStringCreateWithCString(None, s.encode(), kCFStringEncodingUTF8)


def _pystr(ref) -> str:
    if not ref:
        return ""
    buf = ctypes.create_string_buffer(256)
    return buf.value.decode() if _cf.CFStringGetCString(ref, buf, 256, kCFStringEncodingUTF8) else ""


# pmgr DVFS tables: E-cluster, P-cluster(s), GPU
_PMGR_TABLES = (("E", "voltage-states1-sram"), ("P", "voltage-states5-sram"), ("GPU", "voltage-states9"))


def _pmgr_freqs_mhz() -> Dict[str, List[float]]:
    """DVFS frequency tables (MHz) for the CPU clusters and the GPU, from the pmgr IORegistry entry."""
    tables = {}
    it = ctypes.c_uint32()
    if _iokit.IOServiceGetMatchingServices(0, _iokit.IOServiceMatching(b"AppleARMIODevice"), ctypes.byref(it)) != 0:
        return tables
    while True:
        entry = _iokit.IOIteratorNext(it.value)
        if not entry:
            break
        name = ctypes.create_string_buffer(128)
        _iokit.IORegistryEntryGetName(entry, name)
        if name.value == b"pmgr":
            for kind, key in _PMGR_TABLES:
                k = _cfstr(key)
                data = _iokit.IORegistryEntryCreateCFProperty(entry, k, None, 0)
                _cf.CFRelease(k)
                if data:
                    raw = ctypes.string_at(_cf.CFDataGetBytePtr(data), _cf.CFDataGetLength(data))
                    _cf.CFRelease(data)
                    # pairs of (frequency, voltage) as little-endian uint32
                    freqs = [struct.unpack_from("<I", raw, i)[0] for i in range(0, len(raw) - 7, 8)]
                    freqs = [f for f in freqs if f]  # GPU tables start with 0 for the OFF state
                    # CPU tables: Hz on M1-M3, kHz on M4. GPU tables: Hz
                    scale = 1e6 if freqs and max(freqs) > 1e8 else 1e3
                    tables[kind] = [f / scale for f in freqs]
        _iokit.IOObjectRelease(entry)
    _iokit.IOObjectRelease(it.value)
    return tables


def _residency_mhz(ch, table: List[float]) -> Optional[float]:
    """Residency-weighted average frequency over the active (non-idle) states of one IOReport channel."""
    weighted, active, idx = 0.0, 0, 0
    for st in range(_ior.IOReportStateGetCount(ch)):
        state = _pystr(_ior.IOReportStateGetNameForIndex(ch, st))
        if state in _IDLE_STATES:
            continue
        res = _ior.IOReportStateGetResidency(ch, st)
        if idx < len(table):
            weighted += res * table[idx]
            active += res
        idx += 1
    return weighted / active if active else None


class _IOReportSampler:
    """Subscribes to one IOReport group/subgroup; each sample() returns the channels' deltas since the last one."""

    def __init__(self, group: str, subgroup: str):
        g, sg = _cfstr(group), _cfstr(subgroup)
        self._channels = _ior.IOReportCopyChannelsInGroup(g, sg, 0, 0, 0)
        _cf.CFRelease(g)
        _cf.CFRelease(sg)
        if not self._channels:
            raise RuntimeError(f"IOReport group not found: {group} / {subgroup}")
        self._subbed = _vp()
        self._sub = _ior.IOReportCreateSubscription(None, self._channels, ctypes.byref(self._subbed), 0, None)
        if not self._sub:
            raise RuntimeError("IOReport subscription failed")
        self._prev = _ior.IOReportCreateSamples(self._sub, self._subbed, None)
        self._key_channels = _cfstr("IOReportChannels")

    def sample(self, fn) -> dict:
        """Calls fn(channel_name, channel) for each channel of the delta; returns {name: result} for non-None."""
        cur = _ior.IOReportCreateSamples(self._sub, self._subbed, None)
        delta = _ior.IOReportCreateSamplesDelta(self._prev, cur, None)
        _cf.CFRelease(self._prev)
        self._prev = cur
        result = {}
        if not delta:
            return result
        chans = _cf.CFDictionaryGetValue(delta, self._key_channels)
        for i in range(_cf.CFArrayGetCount(chans) if chans else 0):
            ch = _cf.CFArrayGetValueAtIndex(chans, i)
            name = _pystr(_ior.IOReportChannelGetChannelName(ch))
            value = fn(name, ch)
            if value is not None:
                result[name] = value
        _cf.CFRelease(delta)
        return result


class AppleCpuFrequency:
    def __init__(self, freqs: Optional[Dict[str, List[float]]] = None):
        self.freqs = freqs or _pmgr_freqs_mhz()
        if "E" not in self.freqs or "P" not in self.freqs:
            raise RuntimeError("pmgr CPU DVFS tables not found")
        self._sampler = _IOReportSampler("CPU Stats", "CPU Complex Performance States")

    def clusters_mhz(self) -> Dict[str, float]:
        """Average active frequency (MHz) per cluster (ECPU, PCPU, PCPU1...) since the previous call."""

        def cluster(name, ch):
            if not name.endswith(("CPU", "CPU1", "CPU2", "CPU3")):
                return None
            return _residency_mhz(ch, self.freqs["E" if name.startswith("E") else "P"])

        return self._sampler.sample(cluster)

    def current_mhz(self) -> Optional[float]:
        """Frequency of the fastest-running cluster, in MHz (None until a cluster has been active)."""
        clusters = self.clusters_mhz()
        return max(clusters.values()) if clusters else None


class AppleGpu:
    def __init__(self, freqs: Optional[Dict[str, List[float]]] = None):
        freqs = freqs or _pmgr_freqs_mhz()
        self.table = freqs.get("GPU")
        self._sampler = _IOReportSampler("GPU Stats", "GPU Performance States") if self.table else None
        self._key_stats = _cfstr("PerformanceStatistics")
        self._keys = {k: _cfstr(k) for k in ("Device Utilization %", "In use system memory")}
        self._service = _iokit.IOServiceGetMatchingService(0, _iokit.IOServiceMatching(b"IOAccelerator"))
        if not self._service:
            raise RuntimeError("IOAccelerator service not found")
        try:
            self._smc = AppleSmc()
            self._temp_keys = self._smc.temperature_sensors("Tg")  # GPU die sensors
        except RuntimeError:
            self._smc, self._temp_keys = None, []

    def temperature(self) -> Optional[float]:
        """Average of the SMC GPU temperature sensors (°C)."""
        return self._smc.average(self._temp_keys) if self._smc and self._temp_keys else None

    def performance_statistics(self) -> Dict[str, int]:
        """Device utilization (%) and in-use memory (bytes) from the GPU driver."""
        result = {}
        stats = _iokit.IORegistryEntryCreateCFProperty(self._service, self._key_stats, None, 0)
        if not stats:
            return result
        for name, key in self._keys.items():
            num = _cf.CFDictionaryGetValue(stats, key)
            out = ctypes.c_int64()
            if num and _cf.CFNumberGetValue(num, kCFNumberSInt64Type, ctypes.byref(out)):
                result[name] = out.value
        _cf.CFRelease(stats)
        return result

    def frequency_mhz(self) -> Optional[float]:
        """Average active GPU frequency (MHz) since the previous call; None if the GPU was off the whole time."""
        if not self._sampler:
            return None
        return self._sampler.sample(
            lambda name, ch: _residency_mhz(ch, self.table) if name == "GPUPH" else None).get("GPUPH")


# --- SMC (System Management Controller) temperatures, read-only, no sudo ---

_iokit.IOServiceOpen.restype = ctypes.c_int
_iokit.IOServiceOpen.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
_iokit.IOConnectCallStructMethod.restype = ctypes.c_int
_iokit.IOConnectCallStructMethod.argtypes = [ctypes.c_uint32, ctypes.c_uint32, _vp, ctypes.c_size_t, _vp,
                                             ctypes.POINTER(ctypes.c_size_t)]
_libsystem = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
_libsystem.mach_task_self.restype = ctypes.c_uint32

_SMC_READ_KEY, _SMC_KEY_FROM_INDEX, _SMC_KEY_INFO = 5, 8, 9


class AppleSmc:
    """Minimal AppleSMC reader. Temperature sensor key names change between chip generations, so keys are
    discovered from the SMC's own key list by prefix (e.g. "Tg" = GPU) rather than hard-coded."""

    def __init__(self):
        svc = _iokit.IOServiceGetMatchingService(0, _iokit.IOServiceMatching(b"AppleSMC"))
        if not svc:
            raise RuntimeError("AppleSMC service not found")
        self._conn = ctypes.c_uint32()
        r = _iokit.IOServiceOpen(svc, _libsystem.mach_task_self(), 0, ctypes.byref(self._conn))
        _iokit.IOObjectRelease(svc)
        if r != 0:
            raise RuntimeError(f"AppleSMC open failed: {r:#x}")
        self._info = {}  # key -> keyInfo bytes (size, type, attributes)

    def _call(self, buf: bytearray) -> Optional[bytes]:
        inp = (ctypes.c_uint8 * 80).from_buffer_copy(bytes(buf))
        out = (ctypes.c_uint8 * 80)()
        size = ctypes.c_size_t(80)
        if _iokit.IOConnectCallStructMethod(self._conn.value, 2, inp, 80, out, ctypes.byref(size)) != 0:
            return None
        out = bytes(out)
        return None if out[40] else out  # out[40] = SMC result code

    @staticmethod
    def _request(key: str, selector: int) -> bytearray:
        buf = bytearray(80)
        struct.pack_into("<I", buf, 0, struct.unpack(">I", key.encode())[0])
        buf[42] = selector
        return buf

    def _key_info(self, key: str) -> Optional[bytes]:
        if key not in self._info:
            out = self._call(self._request(key, _SMC_KEY_INFO))
            self._info[key] = out[28:37] if out else None
        return self._info[key]

    def read_float(self, key: str) -> Optional[float]:
        info = self._key_info(key)
        if not info:
            return None
        size, typ = struct.unpack_from("<I", info, 0)[0], info[4:8][::-1]
        buf = self._request(key, _SMC_READ_KEY)
        buf[28:37] = info
        out = self._call(buf)
        if not out:
            return None
        if typ == b"flt " and size == 4:
            return struct.unpack_from("<f", out, 48)[0]
        if typ == b"sp78" and size == 2:
            return struct.unpack_from(">h", out, 48)[0] / 256.0
        return None

    def keys(self, prefix: str) -> List[str]:
        """All SMC keys starting with prefix (enumerates the SMC key table; call once and cache)."""
        count_info = self._call(self._request("#KEY", _SMC_KEY_INFO))
        if not count_info:
            return []
        buf = self._request("#KEY", _SMC_READ_KEY)
        buf[28:37] = count_info[28:37]
        out = self._call(buf)
        count = struct.unpack_from(">I", out, 48)[0] if out else 0
        found = []
        for i in range(count):
            req = bytearray(80)
            req[42] = _SMC_KEY_FROM_INDEX
            struct.pack_into("<I", req, 44, i)
            out = self._call(req)
            if out:
                key = struct.pack(">I", struct.unpack_from("<I", out, 0)[0]).decode(errors="replace")
                if key.startswith(prefix):
                    found.append(key)
        return found

    def temperature_sensors(self, prefix: str) -> List[str]:
        """Float keys under prefix. Not filtered on their current value: sensors of powered-down cores read
        0 or a placeholder until the core wakes up."""
        return [k for k in self.keys(prefix) if self.read_float(k) is not None]

    # Sensors of parked CPU cores report exactly 40.0 until the core wakes up; real readings have decimals
    _PLACEHOLDER = 40.0

    def average(self, keys: List[str]) -> Optional[float]:
        values = [v for k in keys
                  if (v := self.read_float(k)) is not None and 0 < v < 130 and v != self._PLACEHOLDER]
        return sum(values) / len(values) if values else None
