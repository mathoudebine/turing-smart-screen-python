# turing-smart-screen-python - a Python system monitor and library for 3.5" USB-C displays like Turing Smart Screen or XuanFang
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

# This file will use LibreHardwareMonitor.dll library to get hardware sensors
# Some metrics are still fetched by psutil when not available on LibreHardwareMonitor
# For Windows platforms only

import ctypes
import math
import os
import sys
from statistics import mean
from typing import Tuple

import clr  # Clr is from pythonnet package. Do not install clr package
import psutil
from win32api import *

import library.sensors.sensors as sensors
from library.log import logger

# Import LibreHardwareMonitor dll to Python
lhm_dll = os.getcwd() + '\\external\\LibreHardwareMonitor\\LibreHardwareMonitorLib.dll'
# noinspection PyUnresolvedReferences
clr.AddReference(lhm_dll)
# noinspection PyUnresolvedReferences
clr.AddReference(os.getcwd() + '\\external\\LibreHardwareMonitor\\HidSharp.dll')
# noinspection PyUnresolvedReferences
from LibreHardwareMonitor import Hardware

File_information = GetFileVersionInfo(lhm_dll, "\\")

ms_file_version = File_information['FileVersionMS']
ls_file_version = File_information['FileVersionLS']

logger.debug("Found LibreHardwareMonitorLib %s" % ".".join([str(HIWORD(ms_file_version)), str(LOWORD(ms_file_version)),
                                                            str(HIWORD(ls_file_version)),
                                                            str(LOWORD(ls_file_version))]))

if ctypes.windll.shell32.IsUserAnAdmin() == 0:
    logger.error(
        "Program is not running as administrator. Please run with admin rights or choose another HW_SENSORS option in "
        "config.yaml")
    try:
        sys.exit(0)
    except:
        os._exit(0)

handle = Hardware.Computer()
handle.IsCpuEnabled = True
handle.IsGpuEnabled = True
handle.IsMemoryEnabled = True
handle.IsMotherboardEnabled = False
handle.IsControllerEnabled = False
handle.IsNetworkEnabled = True
handle.IsStorageEnabled = True
handle.Open()
for hardware in handle.Hardware:
    if hardware.HardwareType == Hardware.HardwareType.Cpu:
        logger.info("Found CPU: %s" % hardware.Name)
    elif hardware.HardwareType == Hardware.HardwareType.Memory:
        logger.info("Found Memory: %s" % hardware.Name)
    elif hardware.HardwareType == Hardware.HardwareType.GpuNvidia:
        logger.info("Found Nvidia GPU: %s" % hardware.Name)
    elif hardware.HardwareType == Hardware.HardwareType.GpuAmd:
        logger.info("Found AMD GPU: %s" % hardware.Name)
    elif hardware.HardwareType == Hardware.HardwareType.GpuIntel:
        logger.info("Found Intel GPU: %s" % hardware.Name)
    elif hardware.HardwareType == Hardware.HardwareType.Storage:
        logger.info("Found Storage: %s" % hardware.Name)
    elif hardware.HardwareType == Hardware.HardwareType.Network:
        logger.info("Found Network interface: %s" % hardware.Name)


def get_hw_and_update(hwtype: Hardware.HardwareType) -> Hardware.Hardware:
    for hardware in handle.Hardware:
        if hardware.HardwareType == hwtype:
            hardware.Update()
            return hardware
    return None


def get_net_interface_and_update(if_name: str) -> Hardware.Hardware:
    for hardware in handle.Hardware:
        if hardware.HardwareType == Hardware.HardwareType.Network and hardware.Name == if_name:
            hardware.Update()
            return hardware

    logger.warning("Network interface '%s' not found. Check names in config.yaml." % if_name)
    return None


class Cpu(sensors.Cpu):
    @staticmethod
    def percentage(interval: float) -> float:
        cpu = get_hw_and_update(Hardware.HardwareType.Cpu)
        for sensor in cpu.Sensors:
            if sensor.SensorType == Hardware.SensorType.Load and str(sensor.Name).startswith("CPU Total"):
                return float(sensor.Value)

        logger.error("CPU load cannot be read")
        return math.nan

    @staticmethod
    def frequency() -> float:
        frequencies = []
        cpu = get_hw_and_update(Hardware.HardwareType.Cpu)
        for sensor in cpu.Sensors:
            if sensor.SensorType == Hardware.SensorType.Clock:
                # Keep only real core clocks, ignore effective core clocks
                if "Core #" in str(sensor.Name) and "Effective" not in str(sensor.Name):
                    frequencies.append(float(sensor.Value))
        # Take mean of all core clock as "CPU clock"
        return mean(frequencies)

    @staticmethod
    def load() -> Tuple[float, float, float]:  # 1 / 5 / 15min avg:
        # Get this data from psutil because it is not available from LibreHardwareMonitor
        return psutil.getloadavg()

    @staticmethod
    def is_temperature_available() -> bool:
        cpu = get_hw_and_update(Hardware.HardwareType.Cpu)
        for sensor in cpu.Sensors:
            if sensor.SensorType == Hardware.SensorType.Temperature:
                if str(sensor.Name).startswith("Core") or str(sensor.Name).startswith("CPU Package"):
                    return True

        return False

    @staticmethod
    def temperature() -> float:
        cpu = get_hw_and_update(Hardware.HardwareType.Cpu)
        # By default, the average temperature of all CPU cores will be used
        for sensor in cpu.Sensors:
            if sensor.SensorType == Hardware.SensorType.Temperature and str(sensor.Name).startswith("Core Average"):
                return float(sensor.Value)
        # If not available, the max core temperature will be used
        for sensor in cpu.Sensors:
            if sensor.SensorType == Hardware.SensorType.Temperature and str(sensor.Name).startswith("Core Max"):
                return float(sensor.Value)
        # If not available, the CPU Package temperature (usually same as max core temperature) will be used
        for sensor in cpu.Sensors:
            if sensor.SensorType == Hardware.SensorType.Temperature and str(sensor.Name).startswith("CPU Package"):
                return float(sensor.Value)
        # Otherwise any sensor named "Core..." will be used
        for sensor in cpu.Sensors:
            if sensor.SensorType == Hardware.SensorType.Temperature and str(sensor.Name).startswith("Core"):
                return float(sensor.Value)

        return math.nan


class Gpu(sensors.Gpu):
    @staticmethod
    def stats() -> Tuple[float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / temp (°C)
        gpu_to_use = get_hw_and_update(Hardware.HardwareType.GpuAmd)
        if gpu_to_use is None:
            gpu_to_use = get_hw_and_update(Hardware.HardwareType.GpuNvidia)
        if gpu_to_use is None:
            gpu_to_use = get_hw_and_update(Hardware.HardwareType.GpuIntel)
        if gpu_to_use is None:
            # GPU not supported
            return math.nan, math.nan, math.nan, math.nan

        load = math.nan
        used_mem = math.nan
        total_mem = math.nan
        temp = math.nan

        for sensor in gpu_to_use.Sensors:
            if sensor.SensorType == Hardware.SensorType.Load and str(sensor.Name).startswith("GPU Core"):
                load = float(sensor.Value)
            elif sensor.SensorType == Hardware.SensorType.SmallData and str(sensor.Name).startswith("GPU Memory Used"):
                used_mem = float(sensor.Value)
            elif sensor.SensorType == Hardware.SensorType.SmallData and str(sensor.Name).startswith("GPU Memory Total"):
                total_mem = float(sensor.Value)
            elif sensor.SensorType == Hardware.SensorType.Temperature and str(sensor.Name).startswith("GPU Core"):
                temp = float(sensor.Value)

        return load, (used_mem / total_mem * 100.0), used_mem, temp

    @staticmethod
    def is_available() -> bool:
        found_amd = (get_hw_and_update(Hardware.HardwareType.GpuAmd) is not None)
        found_nvidia = (get_hw_and_update(Hardware.HardwareType.GpuNvidia) is not None)
        found_intel = (get_hw_and_update(Hardware.HardwareType.GpuIntel) is not None)

        if found_amd and (found_nvidia or found_intel) or (found_nvidia and found_intel):
            logger.warning(
                "Found multiple GPUs on your system. Will use dedicated GPU (AMD/Nvidia) for stats if possible.")

        return found_amd or found_nvidia or found_intel


class Memory(sensors.Memory):
    @staticmethod
    def swap_percent() -> float:
        memory = get_hw_and_update(Hardware.HardwareType.Memory)

        virtual_mem_used = math.nan
        mem_used = math.nan
        virtual_mem_available = math.nan
        mem_available = math.nan

        # Get virtual / physical memory stats
        for sensor in memory.Sensors:
            if sensor.SensorType == Hardware.SensorType.Data and str(sensor.Name).startswith("Virtual Memory Used"):
                virtual_mem_used = int(sensor.Value)
            elif sensor.SensorType == Hardware.SensorType.Data and str(sensor.Name).startswith("Memory Used"):
                mem_used = int(sensor.Value)
            elif sensor.SensorType == Hardware.SensorType.Data and str(sensor.Name).startswith(
                    "Virtual Memory Available"):
                virtual_mem_available = int(sensor.Value)
            elif sensor.SensorType == Hardware.SensorType.Data and str(sensor.Name).startswith("Memory Available"):
                mem_available = int(sensor.Value)

        # Compute swap stats from virtual / physical memory stats
        swap_used = virtual_mem_used - mem_used
        swap_available = virtual_mem_available - mem_available
        swap_total = swap_used + swap_available

        return swap_used / swap_total * 100.0

    @staticmethod
    def virtual_percent() -> float:
        memory = get_hw_and_update(Hardware.HardwareType.Memory)
        for sensor in memory.Sensors:
            if sensor.SensorType == Hardware.SensorType.Load and str(sensor.Name).startswith("Memory"):
                return float(sensor.Value)

        return math.nan

    @staticmethod
    def virtual_used() -> int:  # In bytes
        memory = get_hw_and_update(Hardware.HardwareType.Memory)
        for sensor in memory.Sensors:
            if sensor.SensorType == Hardware.SensorType.Data and str(sensor.Name).startswith("Memory Used"):
                return int(sensor.Value * 1000000000.0)

        return 0

    @staticmethod
    def virtual_free() -> int:  # In bytes
        memory = get_hw_and_update(Hardware.HardwareType.Memory)
        for sensor in memory.Sensors:
            if sensor.SensorType == Hardware.SensorType.Data and str(sensor.Name).startswith("Memory Available"):
                return int(sensor.Value * 1000000000.0)

        return 0


# NOTE: all disk data are fetched from psutil Python library, because LHM does not have it.
# This is because LHM is a hardware-oriented library, whereas used/free/total space is for partitions, not disks
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

        upload_rate = 0
        uploaded = 0
        download_rate = 0
        downloaded = 0

        if if_name != "":
            net_if = get_net_interface_and_update(if_name)
            if net_if is not None:
                for sensor in net_if.Sensors:
                    if sensor.SensorType == Hardware.SensorType.Data and str(sensor.Name).startswith("Data Uploaded"):
                        uploaded = int(sensor.Value * 1000000000.0)
                    elif sensor.SensorType == Hardware.SensorType.Data and str(sensor.Name).startswith(
                            "Data Downloaded"):
                        downloaded = int(sensor.Value * 1000000000.0)
                    elif sensor.SensorType == Hardware.SensorType.Throughput and str(sensor.Name).startswith(
                            "Upload Speed"):
                        upload_rate = int(sensor.Value)
                    elif sensor.SensorType == Hardware.SensorType.Throughput and str(sensor.Name).startswith(
                            "Download Speed"):
                        download_rate = int(sensor.Value)

        return upload_rate, uploaded, download_rate, downloaded
