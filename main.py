#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022 Rollbacke
# Copyright (C) 2022 Ebag333
# Copyright (C) 2022 w1ld3r
# Copyright (C) 2022 Charles Ferguson (gerph)
# Copyright (C) 2022 Russ Nelson (RussNelson)
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

# This file is the system monitor main program to display HW sensors on your screen using themes (see README)

from library.pythoncheck import check_python_version
check_python_version()

import os
import sys

try:
    import argparse
    import atexit
    import locale
    import platform
    import signal
    import subprocess
    import time
    from pathlib import Path
    from PIL import Image

    if platform.system() == 'Windows':
        import win32api
        import win32con
        import win32gui

    from library.log import logger
    import library.scheduler as scheduler
    from library.display import display

except Exception as e:
    print("""Import error: %s
Please follow start guide to install required packages: https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start
Or the troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed""" % str(
        e))
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import pystray
except:
    # If pystray cannot be loaded do not stop the program, just ignore it. The tray icon will not be displayed.
    pass

MAIN_DIRECTORY = Path(__file__).resolve().parent
DELAY_BETWEEN_THREADS = 0.25

if __name__ == "__main__":

    # Apply system locale to this program
    locale.setlocale(locale.LC_ALL, '')

    logger.debug("Using Python %s" % sys.version)


    def wait_for_empty_queue(timeout: int = 5):
        # Waiting for all pending request to be sent to display
        logger.info("Waiting for all pending request to be sent to display (%ds max)..." % timeout)

        wait_time = 0
        while not scheduler.is_queue_empty() and wait_time < timeout:
            time.sleep(0.1)
            wait_time = wait_time + 0.1

        logger.debug("(Waited %.1fs)" % wait_time)

    def clean_stop(tray_icon=None):
        # Turn screen and LEDs off before stopping
        display.turn_off()

        # Do not stop the program now in case data transmission was in progress
        # Instead, ask the scheduler to empty the action queue before stopping
        scheduler.STOPPING = True

        # Waiting for all pending request to be sent to display
        wait_for_empty_queue(5)

        # Remove tray icon just before exit
        if tray_icon:
            tray_icon.visible = False

        # We force the exit to avoid waiting for other scheduled tasks: they may have a long delay!
        try:
            sys.exit(0)
        except:
            os._exit(0)

    def on_signal_caught(signum, frame=None):
        logger.info("Caught signal %d, exiting" % signum)
        clean_stop()

    def on_configure_tray(tray_icon, item):
        logger.info("Configure from tray icon")

        try:
            # Load Python file with local python interpreter (useful for venvs)
            configure_file = next(MAIN_DIRECTORY.glob("configure.py"))
            subprocess.Popen([sys.executable, str(configure_file)])
        except:
            # Load binary (for releases) or Python file with system interpreter
            configure_file = next(MAIN_DIRECTORY.glob("configure*"))
            if platform.system() == "Windows":
                subprocess.Popen([str(configure_file)], creationflags=0x08000000)
            else:
                subprocess.Popen([str(configure_file)])

        clean_stop(tray_icon)

    def on_exit_tray(tray_icon, item):
        logger.info("Exit from tray icon")
        clean_stop(tray_icon)


    def on_clean_exit(*args):
        logger.info("Program will now exit")
        clean_stop()


    if platform.system() == "Windows":
        def on_win32_ctrl_event(event):
            """Handle Windows console control events (like Ctrl-C)."""
            if event in (win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT, win32con.CTRL_CLOSE_EVENT):
                logger.debug("Caught Windows control event %s, exiting" % event)
                clean_stop()
            return 0


        def on_win32_wm_event(hWnd, msg, wParam, lParam):
            """Handle Windows window message events (like ENDSESSION, CLOSE, DESTROY)."""
            logger.debug("Caught Windows window message event %s" % msg)
            if msg == win32con.WM_POWERBROADCAST:
                # WM_POWERBROADCAST is used to detect computer going to/resuming from sleep
                if wParam == win32con.PBT_APMSUSPEND:
                    logger.info("Computer is going to sleep, display will turn off")
                    display.turn_off()
                elif wParam == win32con.PBT_APMRESUMEAUTOMATIC:
                    logger.info("Computer is resuming from sleep, display will turn on")
                    display.turn_on()
                    # Some models have troubles displaying back the previous bitmap after being turned off/on
                    display.display_static_images()
                    display.display_static_text()
            else:
                # For any other events, the program will stop
                logger.info("Program will now exit")
                clean_stop()

    # Create a tray icon for the program, with an Exit entry in menu
    try:
        tray_icon = pystray.Icon(
            name='Turing System Monitor',
            title='Turing System Monitor',
            icon=Image.open(MAIN_DIRECTORY / "res/icons/monitor-icon-17865/64.png"),
            menu=pystray.Menu(
                pystray.MenuItem(
                    text='Configure',
                    action=on_configure_tray),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    text='Exit',
                    action=on_exit_tray)
            )
        )

        # For platforms != macOS, display the tray icon now with non-blocking function
        if platform.system() != "Darwin":
            tray_icon.run_detached()
            logger.info("Tray icon has been displayed")
    except:
        tray_icon = None
        logger.warning("Tray icon is not supported on your platform")

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Turing System Monitor")
    parser.add_argument(
        "-t", "--theme-screenshots",
        type=int,
        default=None,
        help="Run n iterations in automated mode to generate themes screenshots."
    )
    args = parser.parse_args()

    # Set the different stopping event handlers, to send a complete frame to the LCD before exit
    atexit.register(on_clean_exit)
    signal.signal(signal.SIGINT, on_signal_caught)
    signal.signal(signal.SIGTERM, on_signal_caught)
    is_posix = os.name == 'posix'
    if is_posix:
        signal.signal(signal.SIGQUIT, on_signal_caught)
    if platform.system() == "Windows":
        win32api.SetConsoleCtrlHandler(on_win32_ctrl_event, True)

    # Initialize the display
    logger.info("Initialize display")
    display.initialize_display()

    # Start serial queue handler
    if not args.theme_screenshots:
        scheduler.QueueHandler()

    # Create all static images
    display.display_static_images()

    # Create all static texts
    display.display_static_text()

    # Wait for static images/text to be displayed before starting monitoring (to avoid filling the queue while waiting)
    if not args.theme_screenshots:
        wait_for_empty_queue(10)

    # Start sensor scheduled reading. Avoid starting them all at the same time to optimize load
    logger.info("Starting system monitoring")
    import library.stats as stats

    if not args.theme_screenshots:
        scheduler.CPUPercentage(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.CPUFrequency(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.CPULoad(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.CPUTemperature(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.CPUFanSpeed(); time.sleep(DELAY_BETWEEN_THREADS)
        if stats.Gpu.is_available():
            scheduler.GpuStats(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.MemoryStats(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.DiskStats(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.NetStats(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.DateStats(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.SystemUptimeStats(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.CustomStats(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.WeatherStats(); time.sleep(DELAY_BETWEEN_THREADS)
        scheduler.PingStats(); time.sleep(DELAY_BETWEEN_THREADS)
    else:
        logger.info("Theme screenshots mode enabled - program will run %d iterations then close." % args.theme_screenshots)
        # Run a predefined number of time to generate theme screenshot then close
        for i in range(0, args.theme_screenshots):
            logger.debug("Iteration #" + str(i))
            stats.CPU.percentage()
            stats.CPU.frequency()
            stats.CPU.load()
            stats.CPU.temperature()
            stats.CPU.fan_speed()
            stats.Gpu.stats()
            stats.Memory.stats()
            stats.Disk.stats()
            stats.Net.stats()
            stats.Date.stats()
            stats.SystemUptime.stats()
            stats.Custom.stats()
            stats.Weather.stats()
            stats.Ping.stats()
        logger.debug("Finished theme generation, program will close.")
        clean_stop()

    # OS-specific tasks
    if tray_icon and platform.system() == "Darwin":  # macOS-specific
        from AppKit import NSBundle, NSApp, NSApplicationActivationPolicyProhibited

        # Hide Python Launcher icon from macOS dock
        info = NSBundle.mainBundle().infoDictionary()
        info["LSUIElement"] = "1"
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

        # For macOS: display the tray icon now with blocking function
        tray_icon.run()

    elif platform.system() == "Windows":  # Windows-specific
        # Create a hidden window just to be able to receive window message events (for shutdown/logoff clean stop)
        hinst = win32api.GetModuleHandle(None)
        wndclass = win32gui.WNDCLASS()
        wndclass.hInstance = hinst
        wndclass.lpszClassName = "turingEventWndClass"
        messageMap = {win32con.WM_QUERYENDSESSION: on_win32_wm_event,
                      win32con.WM_ENDSESSION: on_win32_wm_event,
                      win32con.WM_QUIT: on_win32_wm_event,
                      win32con.WM_DESTROY: on_win32_wm_event,
                      win32con.WM_CLOSE: on_win32_wm_event,
                      win32con.WM_POWERBROADCAST: on_win32_wm_event}

        wndclass.lpfnWndProc = messageMap

        try:
            myWindowClass = win32gui.RegisterClass(wndclass)
            hwnd = win32gui.CreateWindowEx(win32con.WS_EX_LEFT,
                                           myWindowClass,
                                           "turingEventWnd",
                                           0,
                                           0,
                                           0,
                                           win32con.CW_USEDEFAULT,
                                           win32con.CW_USEDEFAULT,
                                           0,
                                           0,
                                           hinst,
                                           None)
            while True:
                # Receive and dispatch window messages
                win32gui.PumpWaitingMessages()
                time.sleep(0.5)

        except Exception as e:
            logger.error("Exception while creating event window: %s" % str(e))
