#!/usr/bin/env python3
# A simple Python manager for "Turing Smart Screen" 3.5" IPS USB-C display
# https://github.com/mathoudebine/turing-smart-screen-python

import os
import sys
import signal
from library.static_display import StaticDisplay
import library.scheduler as scheduler

from library import config

CONFIG_DATA = config.CONFIG_DATA
stop = False

if __name__ == "__main__":

    def sighandler(signum, frame):
        global stop
        stop = True

    try:
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

        # Overlay Static Text
        # StaticDisplay.display_static_text()

        # Run our jobs that update data
        import library.stats as stats
        # while True:
        #     stats.CPU.percentage()

        scheduler.CPUPercentage()
        scheduler.CPUFrequency()
        scheduler.CPULoad()
        scheduler.GPUStats()
        scheduler.MemoryStats()
        scheduler.DiskStats()
        scheduler.QueueHandler()

    except KeyboardInterrupt:

        print('Keyboard interrupt received from user')

        # Close communication with the screen
        config.lcd_comm.close()

        try:
            sys.exit(0)
        except:
            os._exit(0)
