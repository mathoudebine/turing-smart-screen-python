#!/usr/bin/env python3
# A simple Python manager for "Turing Smart Screen" 3.5" IPS USB-C display
# https://github.com/mathoudebine/turing-smart-screen-python

import os
import signal
import sys

import library.scheduler as scheduler
from library.static_display import StaticDisplay

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
    StaticDisplay.initialize_display()

    # Create all static images
    StaticDisplay.display_static_images()

    # Create all static texts
    StaticDisplay.display_static_text()

    # Run our jobs that update data
    import library.stats as stats

    scheduler.CPUPercentage()
    scheduler.CPUFrequency()
    scheduler.CPULoad()
    if stats.GPU.is_available():
        scheduler.GPUStats()
    else:
        print("STATS: Your GPU is not supported yet")
    scheduler.MemoryStats()
    scheduler.DiskStats()
    scheduler.QueueHandler()


