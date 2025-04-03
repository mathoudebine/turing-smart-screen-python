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
from collections import namedtuple
from enum import IntEnum, auto
from typing import Tuple, List # Added List

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


# Function inspired of psutil/psutil/_pslinux.py:sensors_fans()
# Adapted to also get fan speed percentage instead of raw value
def sensors_fans():
    """Return hardware fans info (for CPU and other peripherals) as a
    dict including hardware label and current speed.

    Implementation notes:
    - /sys/class/hwmon looks like the most recent interface to
      retrieve this info, and this implementation relies on it
      only (old distros will probably use something else)
    - lm-sensors on Ubuntu 16.04 relies on /sys/class/hwmon
    """
    from psutil._common import bcat, cat
    import collections, glob, os

    ret = collections.defaultdict(list)
    basenames = glob.glob('/sys/class/hwmon/hwmon*/fan*_*')
    if not basenames:
        # CentOS has an intermediate /device directory:
        # https://github.com/giampaolo/psutil/issues/971
        basenames = glob.glob('/sys/class/hwmon/hwmon*/device/fan*_*')

    basenames = sorted(set([x.split('_')[0] for x in basenames]))
    for base in basenames:
        try:
            current_rpm = int(bcat(base + '_input'))
            try:
                max_rpm = int(bcat(base + '_max'))
            except:
                max_rpm = 1500  # Approximated: max fan speed is 1500 RPM
            try:
                min_rpm = int(bcat(base + '_min'))
            except:
                min_rpm = 0  # Approximated: min fan speed is 0 RPM

            # Avoid division by zero if max_rpm equals min_rpm
            if max_rpm > min_rpm:
                percent = int((current_rpm - min_rpm) / (max_rpm - min_rpm) * 100)
                # Clamp percentage between 0 and 100
                percent = max(0, min(100, percent))
            else:
                percent = 0

        except (IOError, OSError) as err:
            continue
        unit_name = cat(os.path.join(os.path.dirname(base), 'name')).strip()
        label = cat(base + '_label', fallback=os.path.basename(base)).strip()

        custom_sfan = namedtuple('sfan', ['label', 'current', 'percent'])
        ret[unit_name].append(custom_sfan(label, current_rpm, percent))

    return dict(ret)


def is_cpu_fan(label: str) -> bool:
    return ("cpu" in label.lower()) or ("proc" in label.lower())


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
    def load() -> Tuple[float, float, float]:  # 1 / 5 / 15min avg (%):
        try:
            return psutil.getloadavg()
        except:
            return math.nan, math.nan, math.nan

    @staticmethod
    def temperature() -> float:
        cpu_temp = math.nan
        try:
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
        except:
            # psutil.sensors_temperatures not available on Windows / MacOS
            pass
        return cpu_temp

    @staticmethod
    def fan_percent(fan_name: str = None) -> float:
        try:
            fans = sensors_fans()
            if fans:
                for name, entries in fans.items():
                    for entry in entries:
                        if fan_name is not None and fan_name == "%s/%s" % (name, entry.label):
                            # Manually selected fan
                            return entry.percent
                        elif is_cpu_fan(entry.label) or is_cpu_fan(name):
                            # Auto-detected fan
                            return entry.percent
        except:
            pass

        return math.nan


class Gpu(sensors.Gpu):
    @staticmethod
    def stats() -> List[Tuple[float, float, float, float, float]]:
        # Returns list of: load (%) / used mem (%) / used mem (Mb) / total mem (Mb) / temp (°C) per GPU
        global DETECTED_GPU
        if DETECTED_GPU == GpuType.AMD:
            return GpuAmd.stats()
        elif DETECTED_GPU == GpuType.NVIDIA:
            return GpuNvidia.stats()
        else:
            return [] # Return empty list if no supported GPU

    @staticmethod
    def fps() -> List[int]:
        global DETECTED_GPU
        if DETECTED_GPU == GpuType.AMD:
            return GpuAmd.fps()
        elif DETECTED_GPU == GpuType.NVIDIA:
            return GpuNvidia.fps()
        else:
            return []

    @staticmethod
    def fan_percent() -> List[float]:
        global DETECTED_GPU
        num_gpus = 0
        expected_fan_dev_names = []

        # Determine number of GPUs and expected device names for fan lookup
        if DETECTED_GPU == GpuType.NVIDIA:
            try:
                num_gpus = len(GPUtil.getGPUs())
                expected_fan_dev_names = ['nouveau', 'nvidia']
            except: return []
        elif DETECTED_GPU == GpuType.AMD:
            try:
                if pyamdgpuinfo:
                    num_gpus = pyamdgpuinfo.detect_gpus()
                    expected_fan_dev_names = ['amdgpu', 'radeon']
                elif pyadl:
                    num_gpus = len(pyadl.ADLManager.getInstance().getDevices())
                    expected_fan_dev_names = ['amdgpu', 'radeon']
                else: return []
            except: return []
        else:
            return []

        fan_percentages = [math.nan] * num_gpus
        
        try:
            if platform.system() == "Linux": # Linux : sensors_fans
                fans = sensors_fans()
                fans_found_for_type = []
                # Find fans related to the GPU
                for dev_name, entries in fans.items():
                    if any(expected_name in dev_name.lower() for expected_name in expected_fan_dev_names):
                        for entry in entries:
                            if "gpu" in entry.label.lower() or "fan" in entry.label.lower(): # Broader check
                                fans_found_for_type.append(entry.percent)

                # Sequential mapping
                for i in range(min(num_gpus, len(fans_found_for_type))):
                    fan_percentages[i] = fans_found_for_type[i]
        except Exception as e:
            logger.debug(f"sensors_fans check failed or not applicable: {e}")
            pass

        if DETECTED_GPU == GpuType.AMD and pyadl and platform.system() == "Windows": # AMD gpu on Windows : pyadl
            try:
                devices = pyadl.ADLManager.getInstance().getDevices()
                for i, device in enumerate(devices):
                     if i < num_gpus and math.isnan(fan_percentages[i]): # Only overwrite if the previous method resulted in NaN
                         try:
                             fan_percentages[i] = device.getCurrentFanSpeed(pyadl.ADL_DEVICE_FAN_SPEED_TYPE_PERCENTAGE)
                         except:
                             fan_percentages[i] = math.nan # Keep nan if pyadl fails
            except Exception as e:
                logger.debug(f"pyadl fan check failed: {e}")
                pass

        return fan_percentages

    @staticmethod
    def get_gpu_names() -> List[str]:
        global DETECTED_GPU
        if DETECTED_GPU == GpuType.AMD:
            return GpuAmd.get_gpu_names()
        elif DETECTED_GPU == GpuType.NVIDIA:
            return GpuNvidia.get_gpu_names()
        else:
            return []

    @staticmethod
    def frequency() -> List[float]:
        global DETECTED_GPU
        if DETECTED_GPU == GpuType.AMD:
            return GpuAmd.frequency()
        elif DETECTED_GPU == GpuType.NVIDIA:
            return GpuNvidia.frequency()
        else:
            return []

    @staticmethod
    def is_available() -> bool:
        global DETECTED_GPU
        # Always use Nvidia GPU if available
        if GpuNvidia.is_available():
            logger.info("Detected Nvidia GPU(s)")
            DETECTED_GPU = GpuType.NVIDIA
        # Otherwise, use the AMD GPU / APU if available
        elif GpuAmd.is_available():
            logger.info("Detected AMD GPU(s)")
            DETECTED_GPU = GpuType.AMD
        else:
            logger.warning("No supported GPU found")
            DETECTED_GPU = GpuType.UNSUPPORTED
            if sys.version_info >= (3, 11) and (platform.system() == "Linux" or platform.system() == "Darwin"):
                logger.warning("If you have an AMD GPU, you may need to install some  libraries manually: see "
                               "https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#linux--macos-no-supported-gpu-found-with-an-amd-gpu-and-python-311")

        return DETECTED_GPU != GpuType.UNSUPPORTED


class GpuNvidia(sensors.Gpu):
    @staticmethod
    def stats() -> List[Tuple[float, float, float, float, float]]:
        # Returns list of: load (%) / used mem (%) / used mem (Mb) / total mem (Mb) / temp (°C) per GPU
        all_stats = []
        try:
            nvidia_gpus = GPUtil.getGPUs()
            for gpu in nvidia_gpus:
                load = gpu.load * 100 if gpu.load is not None else math.nan
                memory_used_mb = gpu.memoryUsed if gpu.memoryUsed is not None else math.nan
                memory_total_mb = gpu.memoryTotal if gpu.memoryTotal is not None else math.nan

                if not math.isnan(memory_used_mb) and not math.isnan(memory_total_mb) and memory_total_mb > 0:
                    memory_percentage = (memory_used_mb / memory_total_mb) * 100
                else:
                    memory_percentage = math.nan

                temperature = gpu.temperature if gpu.temperature is not None else math.nan
                all_stats.append((load, memory_percentage, memory_used_mb, memory_total_mb, temperature))
        except Exception as e:
            logger.error(f"Error getting Nvidia stats with GPUtil: {e}")
            # Return list of nans if GPUtil fails entirely
            try: num_gpus = len(GPUtil.getGPUs()) # Try to get count even on error
            except: num_gpus = 1 # Assume 1 if count fails
            return [(math.nan, math.nan, math.nan, math.nan, math.nan)] * num_gpus
        return all_stats

    @staticmethod
    def get_gpu_names() -> List[str]:
        names = []
        try:
            nvidia_gpus = GPUtil.getGPUs()
            for gpu in nvidia_gpus:
                names.append(gpu.name if gpu.name else "NVIDIA GPU")
        except Exception as e:
            logger.error(f"Error getting Nvidia GPU names: {e}")
        return names

    @staticmethod
    def fps() -> List[int]:
        # Not supported by the GPUtil library
        try: num_gpus = len(GPUtil.getGPUs())
        except: num_gpus = 0
        return [-1] * num_gpus

    @staticmethod
    def fan_percent() -> List[float]:
         # Fan speed is handled by the main Gpu.fan_percent() method using OS interfaces, GPUtil doesn't provide fan speed directly.
        try: num_gpus = len(GPUtil.getGPUs())
        except: num_gpus = 0
        return [math.nan] * num_gpus

    @staticmethod
    def frequency() -> List[float]:
        # Not supported by the GPUtil library
        try: num_gpus = len(GPUtil.getGPUs())
        except: num_gpus = 0
        return [math.nan] * num_gpus

    @staticmethod
    def is_available() -> bool:
        try:
            return len(GPUtil.getGPUs()) > 0
        except:
            return False


class GpuAmd(sensors.Gpu):
    @staticmethod
    def stats() -> List[Tuple[float, float, float, float, float]]:
        # Returns list of: load (%) / used mem (%) / used mem (Mb) / total mem (Mb) / temp (°C) per GPU
        all_stats = []
        if pyamdgpuinfo:
            try:
                num_gpus = pyamdgpuinfo.detect_gpus()
                for i in range(num_gpus):
                    load, memory_percentage, memory_used, memory_total, temperature = math.nan, math.nan, math.nan, math.nan, math.nan
                    try:
                        amd_gpu = pyamdgpuinfo.get_gpu(i)
                        try: memory_used_bytes = amd_gpu.query_vram_usage()
                        except: memory_used_bytes = math.nan
                        try: memory_total_bytes = amd_gpu.memory_info["vram_size"]
                        except: memory_total_bytes = math.nan

                        if not math.isnan(memory_used_bytes) and not math.isnan(memory_total_bytes) and memory_total_bytes > 0:
                             memory_percentage = (memory_used_bytes / memory_total_bytes) * 100
                             memory_used = memory_used_bytes / 1024 / 1024
                             memory_total = memory_total_bytes / 1024 / 1024
                        else:
                             memory_percentage, memory_used, memory_total = math.nan, math.nan, math.nan

                        try: load = amd_gpu.query_load() * 100
                        except: load = math.nan
                        try: temperature = amd_gpu.query_temperature()
                        except: temperature = math.nan
                    except Exception as gpu_err:
                        logger.debug(f"Error getting stats for AMD GPU {i} (pyamdgpuinfo): {gpu_err}")
                    all_stats.append((load, memory_percentage, memory_used, memory_total, temperature))
            except Exception as e:
                 logger.error(f"Error detecting AMD GPUs with pyamdgpuinfo: {e}")


        elif pyadl:
            try:
                devices = pyadl.ADLManager.getInstance().getDevices()
                for amd_gpu in devices:
                    load, temperature = math.nan, math.nan
                    try:
                        try: load = amd_gpu.getCurrentUsage()
                        except: load = math.nan
                        try: temperature = amd_gpu.getCurrentTemperature()
                        except: temperature = math.nan
                    except Exception as gpu_err:
                         logger.debug(f"Error getting stats for AMD GPU (pyadl): {gpu_err}")
                    # pyadl doesn't easily provide memory details
                    all_stats.append((load, math.nan, math.nan, math.nan, temperature))
            except Exception as e:
                logger.error(f"Error detecting AMD GPUs with pyadl: {e}")

        return all_stats

    @staticmethod
    def get_gpu_names() -> List[str]:
        names = []
        if pyamdgpuinfo:
            try:
                num_gpus = pyamdgpuinfo.detect_gpus()
                for i in range(num_gpus):
                    try:
                        name = pyamdgpuinfo.get_gpu(i).marketing_name
                        names.append(name if name else f"AMD GPU {i}")
                    except:
                        names.append(f"AMD GPU {i}")
            except Exception as e:
                 logger.error(f"Error getting AMD GPU names (pyamdgpuinfo): {e}")
        elif pyadl:
            try:
                devices = pyadl.ADLManager.getInstance().getDevices()
                for i, device in enumerate(devices):
                    try:
                        name = device.adapterName.decode('utf-8')
                        names.append(name if name else f"AMD GPU {i}")
                    except:
                        names.append(f"AMD GPU {i}")
            except Exception as e:
                logger.error(f"Error getting AMD GPU names (pyadl): {e}")
        return names

    @staticmethod
    def fps() -> List[int]:
        # Not supported by Python libraries
        num_gpus = 0
        try:
             if pyamdgpuinfo: num_gpus = pyamdgpuinfo.detect_gpus()
             elif pyadl: num_gpus = len(pyadl.ADLManager.getInstance().getDevices())
        except: pass
        return [-1] * num_gpus

    @staticmethod
    def fan_percent() -> List[float]:
         # Fan speed is handled by the main Gpu.fan_percent method using OS interfaces or pyadl
        num_gpus = 0
        try:
             if pyamdgpuinfo: num_gpus = pyamdgpuinfo.detect_gpus()
             elif pyadl: num_gpus = len(pyadl.ADLManager.getInstance().getDevices())
        except: pass
        return [math.nan] * num_gpus # Return list of nans, main method handles it

    @staticmethod
    def frequency() -> List[float]: # Returns list of MHz
        frequencies = []
        if pyamdgpuinfo:
            try:
                num_gpus = pyamdgpuinfo.detect_gpus()
                frequencies = [math.nan] * num_gpus
                for i in range(num_gpus):
                    try: frequencies[i] = pyamdgpuinfo.get_gpu(i).query_sclk()
                    except: pass # Keep nan on error

            except Exception as e:
                 logger.error(f"Error detecting AMD GPU frequency with pyamdgpuinfo: {e}")
                 try: num_gpus = pyamdgpuinfo.detect_gpus() # Try to determine num_gpus anyway
                 except: num_gpus = 1 # Assume 1 if count fails
                 return [math.nan] * num_gpus

        elif pyadl:
            try:
                devices = pyadl.ADLManager.getInstance().getDevices()
                frequencies = [math.nan] * len(devices)
                for i, device in enumerate(devices):
                    try: frequencies[i] = device.getCurrentEngineClock() # Returns MHz
                    except: pass # Keep nan on error

            except Exception as e:
                logger.error(f"Error detecting AMD GPU frequency with pyadl: {e}")
                try: num_gpus = len(pyadl.ADLManager.getInstance().getDevices()) # Try to determine num_gpus anyway
                except: num_gpus = 1 # Assume 1 if count fails
                return [math.nan] * num_gpus
        return frequencies


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
    def virtual_used() -> int:  # In bytes
        try:
            # Do not use psutil.virtual_memory().used: from https://psutil.readthedocs.io/en/latest/#memory
            # "It is calculated differently depending on the platform and designed for informational purposes only"
            return psutil.virtual_memory().total - psutil.virtual_memory().available
        except:
            return -1

    @staticmethod
    def virtual_free() -> int:  # In bytes
        try:
            # Do not use psutil.virtual_memory().free: from https://psutil.readthedocs.io/en/latest/#memory
            # "note that this doesn’t reflect the actual memory available (use available instead)."
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
    def disk_used() -> int:  # In bytes
        try:
            return psutil.disk_usage("/").used
        except:
            return -1

    @staticmethod
    def disk_free() -> int:  # In bytes
        try:
            return psutil.disk_usage("/").free
        except:
            return -1


class Net(sensors.Net):
    @staticmethod
    def stats(if_name, interval) -> Tuple[
        int, int, int, int]:  # up rate (B/s), uploaded (B), dl rate (B/s), downloaded (B)
        global PNIC_BEFORE
        try:
            # Get current counters
            pnic_after = psutil.net_io_counters(pernic=True)

            upload_rate = 0
            uploaded = 0
            download_rate = 0
            downloaded = 0

            if if_name != "":
                if if_name in pnic_after:
                    try:
                        # Ensure interval is not zero and we have previous data
                        if interval > 0 and if_name in PNIC_BEFORE:
                           upload_rate = (pnic_after[if_name].bytes_sent - PNIC_BEFORE[if_name].bytes_sent) / interval
                           download_rate = (pnic_after[if_name].bytes_recv - PNIC_BEFORE[if_name].bytes_recv) / interval
                           # Prevent negative rates if counters reset
                           upload_rate = max(0, upload_rate)
                           download_rate = max(0, download_rate)
                        else:
                            upload_rate = 0
                            download_rate = 0

                        uploaded = pnic_after[if_name].bytes_sent
                        downloaded = pnic_after[if_name].bytes_recv

                    except KeyError: # Handles the case where if_name is not in PNIC_BEFORE yet
                         upload_rate = 0
                         download_rate = 0
                         uploaded = pnic_after[if_name].bytes_sent
                         downloaded = pnic_after[if_name].bytes_recv
                    except Exception as e:
                         logger.debug(f"Error calculating net stats for {if_name}: {e}")
                         upload_rate, uploaded, download_rate, downloaded = 0, 0, 0, 0

                    PNIC_BEFORE.update({if_name: pnic_after[if_name]})
                else:
                    # Log only once per missing interface to avoid spamming
                    if not hasattr(Net, '_logged_missing') or if_name not in Net._logged_missing:
                        logger.warning(f"Network interface '{if_name}' not found in psutil.net_io_counters(). Check names in config.yaml.")
                        if not hasattr(Net, '_logged_missing'): Net._logged_missing = set()
                        Net._logged_missing.add(if_name)
                    upload_rate, uploaded, download_rate, downloaded = 0, 0, 0, 0


            return int(upload_rate), int(uploaded), int(download_rate), int(downloaded)
        
        except Exception as e:
            logger.error(f"General error fetching network stats: {e}")
            return -1, -1, -1, -1