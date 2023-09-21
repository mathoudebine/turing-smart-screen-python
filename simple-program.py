#!/usr/bin/env python
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

# This file is a simple Python test program using the library code to display custom content on screen (see README)

import os
import signal
import sys
import time
from datetime import datetime

# Import only the modules for LCD communication
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd.lcd_comm_rev_b import LcdCommRevB
from library.lcd.lcd_comm_rev_c import LcdCommRevC
from library.lcd.lcd_comm_rev_d import LcdCommRevD
from library.lcd.lcd_simulated import LcdSimulated
from library.log import logger

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux, etc. or "AUTO" for auto-discovery
# COM_PORT = "/dev/ttyACM0"
# COM_PORT = "COM5"
COM_PORT = "AUTO"

# Display revision:
# - A      for Turing 3.5" and UsbPCMonitor 3.5"/5"
# - B      for Xuanfang 3.5" (inc. flagship)
# - C      for Turing 5"
# - D      for Kipye Qiye Smart Display 3.5"
# - SIMU   for 3.5" simulated LCD (image written in screencap.png)
# - SIMU5  for 5" simulated LCD
# To identify your smart screen: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions
REVISION = "A"

stop = False

if __name__ == "__main__":

    def sighandler(signum, frame):
        global stop
        stop = True


    # Set the signal handlers, to send a complete frame to the LCD before exit
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    is_posix = os.name == 'posix'
    if is_posix:
        signal.signal(signal.SIGQUIT, sighandler)

    # Build your LcdComm object based on the HW revision
    lcd_comm = None
    if REVISION == "A":
        logger.info("Selected Hardware Revision A (Turing Smart Screen 3.5\" & UsbPCMonitor 3.5\"/5\")")
        # NOTE: If you have UsbPCMonitor 5" you need to change the width/height to 480x800 below
        lcd_comm = LcdCommRevA(com_port=COM_PORT, display_width=320, display_height=480)
    elif REVISION == "B":
        logger.info("Selected Hardware Revision B (XuanFang screen 3.5\" version B / flagship)")
        lcd_comm = LcdCommRevB(com_port=COM_PORT)
    elif REVISION == "C":
        logger.info("Selected Hardware Revision C (Turing Smart Screen 5\")")
        lcd_comm = LcdCommRevC(com_port=COM_PORT)
    elif REVISION == "D":
        logger.info("Selected Hardware Revision D (Kipye Qiye Smart Display 3.5\")")
        lcd_comm = LcdCommRevD(com_port=COM_PORT)
    elif REVISION == "SIMU":
        logger.info("Selected 3.5\" Simulated LCD")
        lcd_comm = LcdSimulated(display_width=320, display_height=480)
    elif REVISION == "SIMU5":
        logger.info("Selected 5\" Simulated LCD")
        lcd_comm = LcdSimulated(display_width=480, display_height=800)
    else:
        logger.error("Unknown revision")
        try:
            sys.exit(1)
        except:
            os._exit(1)

    # Reset screen in case it was in an unstable state (screen is also cleared)
    lcd_comm.Reset()

    # Send initialization commands
    lcd_comm.InitializeComm()

    # Set brightness in % (warning: revision A display can get hot at high brightness! Keep value at 50% max for rev. A)
    lcd_comm.SetBrightness(level=10)

    # Set backplate RGB LED color (for supported HW only)
    lcd_comm.SetBackplateLedColor(led_color=(255, 255, 255))

    # Set orientation (screen starts in Portrait)
    lcd_comm.SetOrientation(orientation=Orientation.LANDSCAPE)

    # Define background picture
    background = f"res/backgrounds/example_{lcd_comm.get_width()}x{lcd_comm.get_height()}.png"

    # Display sample picture
    logger.debug("setting background picture")
    start = time.perf_counter()
    lcd_comm.DisplayBitmap(background)
    end = time.perf_counter()
    logger.debug(f"background picture set (took {end - start:.3f} s)")

    # Display sample text
    lcd_comm.DisplayText("Basic text", 50, 85)

    # Display custom text with solid background
    lcd_comm.DisplayText("Custom italic multiline text\nright-aligned", 5, 120,
                         font="roboto/Roboto-Italic.ttf",
                         font_size=20,
                         font_color=(0, 0, 255),
                         background_color=(255, 255, 0),
                         align='right')

    # Display custom text with transparent background
    lcd_comm.DisplayText("Transparent bold text", 5, 180,
                         font="geforce/GeForce-Bold.ttf",
                         font_size=30,
                         font_color=(255, 255, 255),
                         background_image=background)

    # Display the current time and some progress bars as fast as possible
    bar_value = 0
    while not stop:
        start = time.perf_counter()
        lcd_comm.DisplayText(str(datetime.now().time()), 160, 2,
                             font="roboto/Roboto-Bold.ttf",
                             font_size=20,
                             font_color=(255, 0, 0),
                             background_image=background)

        lcd_comm.DisplayProgressBar(10, 40,
                                    width=140, height=30,
                                    min_value=0, max_value=100, value=bar_value,
                                    bar_color=(255, 255, 0), bar_outline=True,
                                    background_image=background)

        lcd_comm.DisplayProgressBar(160, 40,
                                    width=140, height=30,
                                    min_value=0, max_value=19, value=bar_value % 20,
                                    bar_color=(0, 255, 0), bar_outline=False,
                                    background_image=background)

        lcd_comm.DisplayRadialProgressBar(98, 260, 25, 4,
                                          min_value=0,
                                          max_value=100,
                                          value=bar_value,
                                          angle_sep=0,
                                          bar_color=(0, 255, 0),
                                          font_color=(255, 255, 255),
                                          background_image=background)

        lcd_comm.DisplayRadialProgressBar(222, 260, 40, 13,
                                          min_value=0,
                                          max_value=100,
                                          angle_start=405,
                                          angle_end=135,
                                          angle_steps=10,
                                          angle_sep=5,
                                          clockwise=False,
                                          value=bar_value,
                                          bar_color=(255, 255, 0),
                                          text=f"{10 * int(bar_value / 10)}°C",
                                          font="geforce/GeForce-Bold.ttf",
                                          font_size=20,
                                          font_color=(255, 255, 0),
                                          background_image=background)

        bar_value = (bar_value + 2) % 101
        end = time.perf_counter()
        logger.debug(f"refresh done (took {end - start:.3f} s)")

    # Close serial connection at exit
    lcd_comm.closeSerial()
