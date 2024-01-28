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
COM_PORT = "COM4"

# Display revision:
# - A      for Turing 3.5" and UsbPCMonitor 3.5"/5"
# - B      for Xuanfang 3.5" (inc. flagship)
# - C      for Turing 5"
# - D      for Kipye Qiye Smart Display 3.5"
# - SIMU   for 3.5" simulated LCD (image written in screencap.png)
# - SIMU5  for 5" simulated LCD
# To identify your smart screen: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions
REVISION = "C"

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

    # Build your LcdComm object for Turing 5"
    logger.info("Selected Hardware Revision C (Turing Smart Screen 5\")")
    lcd_comm = LcdCommRevC(com_port=COM_PORT)

    # Set LANDSCAPE orientation.
    orientation = Orientation.LANDSCAPE
    lcd_comm.SetOrientation(orientation=orientation)

    # Send initialization commands
    lcd_comm.InitializeComm()

    # Set brightness in % (warning: revision A display can get hot at high brightness! Keep value at 50% max for rev. A)
    lcd_comm.SetBrightness(level=50)

    # Check if video is loaded and upload video if needed.
    video_size = lcd_comm.GetFileSize("/mnt/SDCARD/video/particle_wave.mp4")

    if video_size == 0:
        # Upload a background video.
        print("Uploading video ...")
        lcd_comm.UploadFile(local_path="res/videos/particle_wave.mp4", destination_path="/mnt/SDCARD/video/particle_wave.mp4")
        print("Upload done")

    # Print size of the uploaded video.
    print(lcd_comm.GetFileSize("/mnt/SDCARD/video/particle_wave.mp4"))

    # Clear screen.
    lcd_comm.StopVideo()
    lcd_comm.Clear()

    # Start the backgroud video.
    lcd_comm.StartVideo("/mnt/SDCARD/video/particle_wave.mp4")

    # Initialize the video overlay.
    # Must be called before drawing anything on the video!
    lcd_comm.InitializeVideoOverlay()

    # Display sample text
    lcd_comm.DrawTextOnVideo("Basic text", 50, 85)

    # Display custom text with solid background
    lcd_comm.DrawTextOnVideo("Custom italic multiline text\nright-aligned", 5, 120,
                         font="roboto/Roboto-Italic.ttf",
                         font_size=20,
                         font_color=(0, 0, 255),
                         background_color=(255, 255, 0),
                         align='right')

    # Display custom text with transparent background
    lcd_comm.DrawTextOnVideo("Transparent bold text", 5, 180,
                         font="geforce/GeForce-Bold.ttf",
                         font_size=30,
                         font_color=(255, 255, 255))

    lcd_comm.ResfreshVideoOverlay()

    # Display the current time and some progress bars as fast as possible
    bar_value = 0
    while not stop:
        start = time.perf_counter()
        lcd_comm.DrawTextOnVideo(str(datetime.now().time()), 160, 2,
                                font="roboto/Roboto-Bold.ttf",
                                font_size=20,
                                font_color=(255, 0, 0))

        lcd_comm.DrawProgressBarOnVideo(10, 40,
                                        width=140, height=30,
                                        min_value=0, max_value=100, value=bar_value,
                                        bar_color=(255, 255, 0), bar_outline=True)

        lcd_comm.DrawProgressBarOnVideo(160, 40,
                                        width=140, height=30,
                                        min_value=0, max_value=19, value=bar_value % 20,
                                        bar_color=(0, 255, 0), bar_outline=False)

        lcd_comm.DrawRadialProgressBarOnVideo(98, 260, 25, 4,
                                            min_value=0,
                                            max_value=100,
                                            value=bar_value,
                                            angle_sep=0,
                                            bar_color=(0, 255, 0),
                                            font_color=(255, 255, 255))

        lcd_comm.DrawRadialProgressBarOnVideo(222, 260, 40, 13,
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
                                            font_color=(255, 255, 0))

        lcd_comm.ResfreshVideoOverlay()

        bar_value = (bar_value + 2) % 101
        end = time.perf_counter()
        logger.debug(f"refresh done (took {end - start:.3f} s)")

    # Close serial connection at exit
    lcd_comm.closeSerial()
