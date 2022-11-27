import math
import library.sensors.sensors as sensors
from library.log import logger

# CPU & disk sensors
import psutil

# Nvidia GPU
import GPUtil

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


class CPU(sensors.CPU):
    @staticmethod
    def percentage(interval: float) -> float:
        return psutil.cpu_percent(interval=interval)

    @staticmethod
    def frequency() -> float:
        return psutil.cpu_freq().current

    @staticmethod
    def load() -> tuple[float, float, float]:  # 1 / 5 / 15min avg:
        return psutil.getloadavg()

    @staticmethod
    def is_temperature_available() -> bool:
        try:
            sensors_temps = psutil.sensors_temperatures()
            if 'coretemp' in sensors_temps or 'k10temp' in sensors_temps or 'cpu_thermal' in sensors_temps:
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
        return cpu_temp


class GpuNvidia(sensors.GPU):
    @staticmethod
    def stats() -> tuple[float, float, float, float]:
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
        return len(GPUtil.getGPUs()) > 0


class GpuAmd(sensors.GPU):
    @staticmethod
    def stats() -> tuple[float, float, float, float]:
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
        if pyamdgpuinfo and pyamdgpuinfo.detect_gpus() > 0:
            return True
        elif pyadl and len(pyadl.ADLManager.getInstance().getDevices()) > 0:
            return True
        else:
            return False


class Memory(sensors.Memory):
    @staticmethod
    def swap_percent() -> float:
        return psutil.swap_memory().percent

    @staticmethod
    def virtual_percent() -> float:
        return psutil.virtual_memory().percent

    @staticmethod
    def virtual_used() -> int:
        return psutil.virtual_memory().used

    @staticmethod
    def virtual_free() -> int:
        return psutil.virtual_memory().free


class Disk(sensors.Disk):
    @staticmethod
    def disk_usage_percent() -> float:
        return psutil.disk_usage("/").percent

    @staticmethod
    def disk_used() -> int:
        return psutil.disk_usage("/").used

    @staticmethod
    def disk_total() -> int:
        return psutil.disk_usage("/").total

    @staticmethod
    def disk_free() -> int:
        return psutil.disk_usage("/").free


class Net(sensors.Net):
    @staticmethod
    def stats(if_name, interval) -> tuple[int, int, int, int]:
        global PNIC_BEFORE
        # Get current counters
        pnic_after = psutil.net_io_counters(pernic=True)

        upload_rate = math.nan
        uploaded = math.nan
        download_rate = math.nan
        downloaded = math.nan

        try:
            if if_name in pnic_after:
                upload_rate = (pnic_after[if_name].bytes_sent - PNIC_BEFORE[if_name].bytes_sent) / interval
                uploaded = pnic_after[if_name].bytes_sent
                download_rate = (pnic_after[if_name].bytes_recv - PNIC_BEFORE[if_name].bytes_recv) / interval
                downloaded = pnic_after[if_name].bytes_recv
        except:
            # Interface might not be in PNIC_BEFORE for now
            logger.debug("Ignored %s" % if_name)
            pass

        PNIC_BEFORE[if_name] = pnic_after[if_name]

        return upload_rate, uploaded, download_rate, downloaded
