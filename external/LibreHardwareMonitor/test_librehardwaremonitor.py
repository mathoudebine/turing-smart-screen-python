# Use this file to display all hardware & sensors available from LibreHardwareMonitor on your computer
# Windows only - needs administrative rights
import ctypes
import os
import sys

import clr  # Clr is from pythonnet package. Do not install clr package
from win32api import *

if ctypes.windll.shell32.IsUserAnAdmin() == 0:
    print("Program is not running as administrator. Please run again with admin rights.")
    try:
        sys.exit(0)
    except:
        os._exit(0)

# noinspection PyUnresolvedReferences
clr.AddReference(os.getcwd() + '\\LibreHardwareMonitorLib.dll')
# noinspection PyUnresolvedReferences
clr.AddReference(os.getcwd() + '\\HidSharp.dll')
# noinspection PyUnresolvedReferences
from LibreHardwareMonitor import Hardware

File_information = GetFileVersionInfo(os.getcwd() + '\\LibreHardwareMonitorLib.dll', "\\")
ms_file_version = File_information['FileVersionMS']
ls_file_version = File_information['FileVersionLS']
print("Found LibreHardwareMonitorLib %s" % ".".join([str(HIWORD(ms_file_version)), str(LOWORD(ms_file_version)),
                                                     str(HIWORD(ls_file_version)),
                                                     str(LOWORD(ls_file_version))]))

File_information = GetFileVersionInfo(os.getcwd() + '\\HidSharp.dll', "\\")
ms_file_version = File_information['FileVersionMS']
ls_file_version = File_information['FileVersionLS']
print("Found HidSharp %s" % ".".join([str(HIWORD(ms_file_version)), str(LOWORD(ms_file_version)),
                                      str(HIWORD(ls_file_version)),
                                      str(LOWORD(ls_file_version))]))

handle = Hardware.Computer()
handle.IsCpuEnabled = True
handle.IsGpuEnabled = True
handle.IsMemoryEnabled = True
handle.IsMotherboardEnabled = True
handle.IsControllerEnabled = True
handle.IsNetworkEnabled = True
handle.IsStorageEnabled = True
handle.IsPsuEnabled = True
handle.Open()

for hw in handle.Hardware:
    print("%s | %s | %s" % (hw.HardwareType, hw.Name, hw.Identifier))
    hw.Update()

    for sensor in hw.Sensors:
        print("    %s | %s | %s" % (sensor.SensorType, sensor.Name, sensor.Value))

    for subhw in hw.SubHardware:
        print("    %s | %s | %s" % (subhw.HardwareType, subhw.Name, subhw.Identifier))
        subhw.Update()

        for sensor in subhw.Sensors:
            print("        %s | %s | %s" % (sensor.SensorType, sensor.Name, sensor.Value))

    print("----------------------------------------------------")

handle.Close()
