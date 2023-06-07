# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
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

# This file will use Python libraries (psutil, GPUtil, etc.) to get hardware sensors
# For all platforms (Linux, Windows, macOS) but not all HW is supported

import math
import platform
import sys
from enum import IntEnum, auto
from typing import Tuple

# Nvidia GPU
import GPUtil
# CPU & disk sensors
import psutil

import library.sensors.sensors as sensors
from library.log import logger

# AMD GPU on Linux
try:
    import pyamdgpuinfo
except:
    pyamdgpuinfo = None

# AMD GPU on Windows
try:
    import pyadl
except:
    pyadl = None

PNIC_BEFORE = {}


class GpuType(IntEnum):
    UNSUPPORTED = auto()
    AMD = auto()
    NVIDIA = auto()


DETECTED_GPU = GpuType.UNSUPPORTED


class Cpu(sensors.Cpu):
    @staticmethod
    def percentage(interval: float) -> float:
        return psutil.cpu_percent(interval=interval)

    @staticmethod
    def frequency() -> float:
        return psutil.cpu_freq().current

    @staticmethod
    def load() -> Tuple[float, float, float]:  # 1 / 5 / 15min avg (%):
        return psutil.getloadavg()

    @staticmethod
    def is_temperature_available() -> bool:
        try:
            sensors_temps = psutil.sensors_temperatures()
            if 'coretemp' in sensors_temps or 'k10temp' in sensors_temps or 'cpu_thermal' in sensors_temps or 'zenpower' in sensors_temps:
                return True
            else:
                return False
        except AttributeError:
            # sensors_temperatures may not be available at all
            return False

    @staticmethod
    def temperature() -> float:
        cpu_temp = 0
        sensors_temps = psutil.sensors_temperatures()
        if 'coretemp' in sensors_temps:
            # Intel CPU
            cpu_temp = sensors_temps['coretemp'][0].current
        elif 'k10temp' in sensors_temps:
            # AMD CPU
            cpu_temp = sensors_temps['k10temp'][0].current
        elif 'cpu_thermal' in sensors_temps:
            # ARM CPU
            cpu_temp = sensors_temps['cpu_thermal'][0].current
        elif 'zenpower' in sensors_temps:
            # AMD CPU with zenpower (k10temp is in blacklist)
            cpu_temp = sensors_temps['zenpower'][0].current
        return cpu_temp


class Gpu(sensors.Gpu):
    @staticmethod
    def stats() -> Tuple[float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / temp (°C)
        global DETECTED_GPU
        if DETECTED_GPU == GpuType.AMD:
            return GpuAmd.stats()
        elif DETECTED_GPU == GpuType.NVIDIA:
            return GpuNvidia.stats()
        else:
            return math.nan, math.nan, math.nan, math.nan

    @staticmethod
    def is_available() -> bool:
        global DETECTED_GPU
        if GpuAmd.is_available():
            logger.info("Detected AMD GPU(s)")
            DETECTED_GPU = GpuType.AMD
        elif GpuNvidia.is_available():
            logger.info("Detected Nvidia GPU(s)")
            DETECTED_GPU = GpuType.NVIDIA
        else:
            logger.warning("No supported GPU found")
            DETECTED_GPU = GpuType.UNSUPPORTED
            if sys.version_info >= (3, 11) and (platform.system() == "Linux" or platform.system() == "Darwin"):
                logger.warning("If you have an AMD GPU, you may need to install some  libraries manually: see "
                               "https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#linux--macos-no-supported-gpu-found-with-an-amd-gpu-and-python-311")

        return DETECTED_GPU != GpuType.UNSUPPORTED


class GpuNvidia(sensors.Gpu):
    @staticmethod
    def stats() -> Tuple[float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / temp (°C)
        # Unlike other sensors, Nvidia GPU with GPUtil pulls in all the stats at once
        nvidia_gpus = GPUtil.getGPUs()

        try:
            memory_used_all = [item.memoryUsed for item in nvidia_gpus]
            memory_used_mb = sum(memory_used_all) / len(memory_used_all)
        except:
            memory_used_mb = math.nan

        try:
            memory_total_all = [item.memoryTotal for item in nvidia_gpus]
            memory_total_mb = sum(memory_total_all) / len(memory_total_all)
            memory_percentage = (memory_used_mb / memory_total_mb) * 100
        except:
            memory_percentage = math.nan

        try:
            load_all = [item.load for item in nvidia_gpus]
            load = (sum(load_all) / len(load_all)) * 100
        except:
            load = math.nan

        try:
            temperature_all = [item.temperature for item in nvidia_gpus]
            temperature = sum(temperature_all) / len(temperature_all)
        except:
            temperature = math.nan

        return load, memory_percentage, memory_used_mb, temperature

    @staticmethod
    def is_available() -> bool:
        try:
            return len(GPUtil.getGPUs()) > 0
        except:
            return False


class GpuAmd(sensors.Gpu):
    @staticmethod
    def stats() -> Tuple[float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / temp (°C)
        if pyamdgpuinfo:
            # Unlike other sensors, AMD GPU with pyamdgpuinfo pulls in all the stats at once
            i = 0
            amd_gpus = []
            while i < pyamdgpuinfo.detect_gpus():
                amd_gpus.append(pyamdgpuinfo.get_gpu(i))
                i = i + 1

            try:
                memory_used_all = [item.query_vram_usage() for item in amd_gpus]
                memory_used_bytes = sum(memory_used_all) / len(memory_used_all)
                memory_used = memory_used_bytes / 1000000
            except:
                memory_used_bytes = math.nan
                memory_used = math.nan

            try:
                memory_total_all = [item.memory_info["vram_size"] for item in amd_gpus]
                memory_total_bytes = sum(memory_total_all) / len(memory_total_all)
                memory_percentage = (memory_used_bytes / memory_total_bytes) * 100
            except:
                memory_percentage = math.nan

            try:
                load_all = [item.query_load() for item in amd_gpus]
                load = (sum(load_all) / len(load_all)) * 100
            except:
                load = math.nan

            try:
                temperature_all = [item.query_temperature() for item in amd_gpus]
                temperature = sum(temperature_all) / len(temperature_all)
            except:
                temperature = math.nan

            return load, memory_percentage, memory_used, temperature
        elif pyadl:
            amd_gpus = pyadl.ADLManager.getInstance().getDevices()

            try:
                load_all = [item.getCurrentUsage() for item in amd_gpus]
                load = (sum(load_all) / len(load_all))
            except:
                load = math.nan

            try:
                temperature_all = [item.getCurrentTemperature() for item in amd_gpus]
                temperature = sum(temperature_all) / len(temperature_all)
            except:
                temperature = math.nan

            # Memory absolute (M) and relative (%) usage not supported by pyadl
            return load, math.nan, math.nan, temperature

    @staticmethod
    def is_available() -> bool:
        try:
            if pyamdgpuinfo and pyamdgpuinfo.detect_gpus() > 0:
                return True
            elif pyadl and len(pyadl.ADLManager.getInstance().getDevices()) > 0:
                return True
            else:
                return False
        except:
            return False


class Memory(sensors.Memory):
    @staticmethod
    def swap_percent() -> float:
        return psutil.swap_memory().percent

    @staticmethod
    def virtual_percent() -> float:
        return psutil.virtual_memory().percent

    @staticmethod
    def virtual_used() -> int:  # In bytes
        return psutil.virtual_memory().used

    @staticmethod
    def virtual_free() -> int:  # In bytes
        return psutil.virtual_memory().free


class Disk(sensors.Disk):
    @staticmethod
    def disk_usage_percent() -> float:
        return psutil.disk_usage("/").percent

    @staticmethod
    def disk_used() -> int:  # In bytes
        return psutil.disk_usage("/").used

    @staticmethod
    def disk_free() -> int:  # In bytes
        return psutil.disk_usage("/").free


class Net(sensors.Net):
    @staticmethod
    def stats(if_name, interval) -> Tuple[
        int, int, int, int]:  # up rate (B/s), uploaded (B), dl rate (B/s), downloaded (B)
        global PNIC_BEFORE
        # Get current counters
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
                    # Interface might not be in PNIC_BEFORE for now
                    pass

                PNIC_BEFORE.update({if_name: pnic_after[if_name]})
            else:
                logger.warning("Network interface '%s' not found. Check names in config.yaml." % if_name)

        return upload_rate, uploaded, download_rate, downloaded
