#!/usr/bin/env python
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022-2023  Rollbacke
# Copyright (C) 2022-2023  Ebag333
# Copyright (C) 2022-2023  w1ld3r
# Copyright (C) 2022-2023  Charles Ferguson (gerph)
# Copyright (C) 2022-2023  Russ Nelson (RussNelson)
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
import os
import sys

MIN_PYTHON = (3, 8)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import atexit
    import locale
    import platform
    import signal
    import subprocess
    import time
    from PIL import Image

    if platform.system() == 'Windows':
        import win32api
        import win32con
        import win32gui

    try:
        import pystray
    except:
        pass
except:
    print(
        "[ERROR] Python dependencies not installed. Please follow start guide: https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start")
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

    logger.debug("Using Python %s" % sys.version)


    def clean_stop(tray_icon=None):
        # Turn screen and LEDs off before stopping
        display.turn_off()

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
        subprocess.Popen(os.path.join(os.getcwd(), "configure.py"), shell=True)
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
            icon=Image.open("res/icons/monitor-icon-17865/64.png"),
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
    scheduler.CustomStats()
    scheduler.QueueHandler()

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
