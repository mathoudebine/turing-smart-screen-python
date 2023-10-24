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

# This file allows to add custom data source as sensors and display them in System Monitor themes
# There is no limitation on how much custom data source classes can be added to this file
# See CustomDataExample theme for the theme implementation part

import platform
from abc import ABC, abstractmethod

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

# Import RTSSSharedMemoryNET dll to Python
clr.AddReference(os.getcwd() + '\\external\\RTSSSharedMemoryNET\\RTSSSharedMemoryNET.dll')
from RTSSSharedMemoryNET import OSD


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
handle.IsMotherboardEnabled = True
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


def get_hw_and_update(hwtype: Hardware.HardwareType, name: str = None) -> Hardware.Hardware:
    for hardware in handle.Hardware:
        if hardware.HardwareType == hwtype:
            if (name and hardware.Name == name) or not name:
                hardware.Update()
                return hardware
    return None


# Custom data classes must be implemented in this file, inherit the CustomDataSource and implement its 2 methods
class CustomDataSource(ABC):
    @abstractmethod
    def as_numeric(self) -> float:
        # Numeric value will be used for graph and radial progress bars
        # If there is no numeric value, keep this function empty
        pass

    @abstractmethod
    def as_string(self) -> str:
        # Text value will be used for text display and radial progress bar inner text
        # Numeric value can be formatted here to be displayed as expected
        # It is also possible to return a text unrelated to the numeric value
        # If this function is empty, the numeric value will be used as string without formatting
        pass

    @abstractmethod
    def as_histo(self) -> list[float]:
        # List of numeric values will be used for plot graph
        # If there is no histo values, keep this function empty
        pass

# Example for a custom data class that has numeric and text values
class ExampleCustomNumericData(CustomDataSource):
    def as_numeric(self) -> float:
        # Numeric value will be used for graph and radial progress bars
        # Here a Python function from another module can be called to get data
        # Example: return my_module.get_rgb_led_brightness() / return audio.system_volume() ...
        return 75.845

    def as_string(self) -> str:
        # Text value will be used for text display and radial progress bar inner text.
        # Numeric value can be formatted here to be displayed as expected
        # It is also possible to return a text unrelated to the numeric value
        # If this function is empty, the numeric value will be used as string without formatting
        # Example here: format numeric value: add unit as a suffix, and keep 1 digit decimal precision
        return f'{self.as_numeric(): .1f}%'
        # Important note! If your numeric value can vary in size, be sure to display it with a default size.
        # E.g. if your value can range from 0 to 9999, you need to display it with at least 4 characters every time.
        # --> return f'{self.as_numeric():>4}%'
        # Otherwise, part of the previous value can stay displayed ("ghosting") after a refresh

    def as_histo(self) -> list[float]:
        pass


# Example for a custom data class that only has text values
class ExampleCustomTextOnlyData(CustomDataSource):
    def as_numeric(self) -> float:
        # If there is no numeric value, keep this function empty
        pass

    def as_string(self) -> str:
        # If a custom data class only has text values, it won't be possible to display graph or radial bars
        return "Python version: " + platform.python_version()

    def as_histo(self) -> list[float]:
        pass


class GpuNvidiaFanPercent(CustomDataSource):
    def as_numeric(self) -> float:
        gpu = get_hw_and_update(Hardware.HardwareType.GpuNvidia)
        for sensor in gpu.Sensors:
            if sensor.SensorType == Hardware.SensorType.Control:
                return float(sensor.Value)
                #return float(50)

        logger.error("GPU Nvidia fan percent cannot be read")
        return math.nan

    def as_string(self) -> str:
        return f'{int(self.as_numeric())}%'

    def as_histo(self) -> list[float]:
        pass

class CpuFanPercent(CustomDataSource):
    def as_numeric(self) -> float:
        mb = get_hw_and_update(Hardware.HardwareType.Motherboard)
        for sh in mb.SubHardware:
            sh.Update()
            for sensor in sh.Sensors:
                if sensor.SensorType == Hardware.SensorType.Control and "#2" in str(sensor.Name):
                    return float(sensor.Value)

        logger.error("CPU fan percent cannot be read")
        return math.nan

    def as_string(self) -> str:
        return f'{int(self.as_numeric())}%'

    def as_histo(self) -> list[float]:
        pass

class RTSSFps(CustomDataSource):

    histo = [-1] * 100

    def as_numeric(self) -> float:
        appEntries = OSD.GetAppEntries()
        for app in appEntries:
            if app.InstantaneousFrames > 0:
                return float(app.InstantaneousFrames)

        return float(0)

    def as_string(self) -> str:
        return f'{int(self.as_numeric())}'

    def as_histo(self) -> list[float]:
        appEntries = OSD.GetAppEntries()
        for app in appEntries:
            if app.InstantaneousFrames > 0:
                RTSSFps.histo.append(app.InstantaneousFrames)
                RTSSFps.histo.pop(0)
                return RTSSFps.histo

        return RTSSFps.histo


