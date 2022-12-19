#!/usr/bin/env python3
# A system monitor in Python for "Turing Smart Screen" 3.5" IPS USB-C display
# https://github.com/mathoudebine/turing-smart-screen-python
import locale
import os
import pystray
import signal
import sys
import time

from PIL import Image

MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

from library.log import logger
import library.scheduler as scheduler
from library.display import display

if __name__ == "__main__":

    # Apply system locale to this program
    locale.setlocale(locale.LC_ALL, '')


    def clean_stop(tray_icon=None):
        # Do not stop the program now in case data transmission was in progress
        # Instead, ask the scheduler to empty the action queue before stopping
        scheduler.STOPPING = True

        # Allow 5 seconds max. delay in case scheduler is not responding
        wait_time = 5
        logger.info("Waiting for all pending request to be sent to display (%ds max)..." % wait_time)

        while not scheduler.is_queue_empty() and wait_time > 0:
            time.sleep(0.1)
            wait_time = wait_time - 0.1

        logger.debug("(%.1fs)" % (5 - wait_time))

        # Remove icon just before the exit
        if tray_icon:
            tray_icon.visible = False

        # We force the exit to avoid waiting for other scheduled tasks: they may have a long delay!
        try:
            sys.exit(0)
        except:
            os._exit(0)


    def sighandler(signum, frame=None):
        logger.info("Caught signal %d, exiting" % signum)
        clean_stop()


    def on_exit_tray(tray_icon, item):
        logger.info("Exit from tray icon")
        clean_stop(tray_icon)


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
        logger.warning("Your CPU temperature is not supported yet")
    if stats.Gpu.is_available():
        scheduler.GpuStats()
    scheduler.MemoryStats()
    scheduler.DiskStats()
    scheduler.NetStats()
    scheduler.DateStats()
    scheduler.QueueHandler()

    # Create a tray icon for the program, with an Exit entry in menu
    tray_icon = pystray.Icon(
        name='Turing System Monitor',
        title='Turing System Monitor',
        icon=Image.open("res/icons/724873501557740364-64.png"),
        menu=pystray.Menu(
            pystray.MenuItem(
                'Exit',
                on_exit_tray))
    ).run()
