#!/usr/bin/env python3
# A simple Python manager for "Turing Smart Screen" 3.5" IPS USB-C display
# https://github.com/mathoudebine/turing-smart-screen-python

import os
import signal
import sys

MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    print("Error: Python %s.%s or later is required.\n" % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

import library.scheduler as scheduler
from library.display import display

if __name__ == "__main__":

    def sighandler(signum, frame):
        print(" Caught signal ", str(signum), ", exiting...")
        try:
            sys.exit(0)
        except:
            os._exit(0)

    # Set the signal handlers, to send a complete frame to the LCD before exit
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    is_posix = os.name == 'posix'
    if is_posix:
        signal.signal(signal.SIGQUIT, sighandler)

    # Initialize the display
    display.initialize_display()

    # Create all static images
    display.display_static_images()

    # Create all static texts
    display.display_static_text()

    # Run our jobs that update data
    import library.stats as stats

    scheduler.CPUPercentage()
    scheduler.CPUFrequency()
    scheduler.CPULoad()
    if stats.CPU.is_temperature_available():
        scheduler.CPUTemperature()
    else:
        print("STATS: Your CPU temperature is not supported yet")
    if stats.GpuNvidia.is_available():
        print("Detected Nvidia GPU(s)")
        scheduler.GpuNvidiaStats()
    elif stats.GpuAmd.is_available():
        print("Detected AMD GPU(s)")
        scheduler.GpuAmdStats()
    else:
        print("STATS: Your GPU is not supported yet")
    scheduler.MemoryStats()
    scheduler.DiskStats()
    scheduler.QueueHandler()
