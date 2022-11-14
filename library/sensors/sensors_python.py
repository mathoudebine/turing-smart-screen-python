import math

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

PNIC_BEFORE = None


class CPU:
    @staticmethod
    def percentage(interval):
        return psutil.cpu_percent(interval=interval)

    @staticmethod
    def frequency():
        return psutil.cpu_freq()

    @staticmethod
    def load():
        return psutil.getloadavg()

    @staticmethod
    def is_temperature_available():
        try:
            if 'coretemp' in psutil.sensors_temperatures() or 'k10temp' in psutil.sensors_temperatures():
                return True
            else:
                return False
        except AttributeError:
            # sensors_temperatures may not be available at all
            return False

    @staticmethod
    def temperature():
        cpu_temp = 0
        if 'coretemp' in psutil.sensors_temperatures():
            # Intel CPU
            cpu_temp = psutil.sensors_temperatures()['coretemp'][0].current
        elif 'k10temp' in psutil.sensors_temperatures():
            # AMD CPU
            cpu_temp = psutil.sensors_temperatures()['k10temp'][0].current
        return cpu_temp


class GpuNvidia:
    @staticmethod
    def stats():
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
    def is_available():
        return len(GPUtil.getGPUs()) > 0


class GpuAmd:
    @staticmethod
    def stats():
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
    def is_available():
        if pyamdgpuinfo and pyamdgpuinfo.detect_gpus() > 0:
            return True
        elif pyadl and len(pyadl.ADLManager.getInstance().getDevices()) > 0:
            return True
        else:
            return False


class Memory:
    @staticmethod
    def swap_percent():
        return psutil.swap_memory().percent

    @staticmethod
    def virtual_percent():
        return psutil.virtual_memory().percent

    @staticmethod
    def virtual_used():
        return psutil.virtual_memory().used

    @staticmethod
    def virtual_free():
        return psutil.virtual_memory().free


class Disk:
    @staticmethod
    def disk_usage():
        return psutil.disk_usage("/")


class Net:
    @staticmethod
    def stats(wlo_card, eth_card):
        pnic_after = psutil.net_io_counters(pernic=True)
        global PNIC_BEFORE
        if PNIC_BEFORE:
            pnic_before = PNIC_BEFORE
        else:
            pnic_before = pnic_after

        if wlo_card in pnic_after:
            upload_wlo = pnic_after[wlo_card].bytes_sent - pnic_before[wlo_card].bytes_sent
            uploaded_wlo = pnic_after[wlo_card].bytes_sent
            download_wlo = pnic_after[wlo_card].bytes_recv - pnic_before[wlo_card].bytes_recv
            downloaded_wlo = pnic_after[wlo_card].bytes_recv
        else:
            upload_wlo = math.nan
            uploaded_wlo = math.nan
            download_wlo = math.nan
            downloaded_wlo = math.nan

        if eth_card in pnic_after:
            upload_eth = pnic_after[eth_card].bytes_sent - pnic_before[eth_card].bytes_sent
            uploaded_eth = pnic_after[eth_card].bytes_sent
            download_eth = pnic_after[eth_card].bytes_recv - pnic_before[eth_card].bytes_recv
            downloaded_eth = pnic_after[eth_card].bytes_recv
        else:
            upload_eth = math.nan
            uploaded_eth = math.nan
            download_eth = math.nan
            downloaded_eth = math.nan

        PNIC_BEFORE = psutil.net_io_counters(pernic=True)

        return upload_wlo, uploaded_wlo, download_wlo, downloaded_wlo, upload_eth, uploaded_eth, download_eth, downloaded_eth
