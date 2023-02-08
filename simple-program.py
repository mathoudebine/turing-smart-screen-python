# turing-smart-screen-python - a Python system monitor and library for 3.5" USB-C displays like Turing Smart Screen or XuanFang
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
from datetime import datetime

# Import only the modules for LCD communication
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd.lcd_comm_rev_b import LcdCommRevB
from library.lcd.lcd_simulated import LcdSimulated
from library.log import logger

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux, etc. or "AUTO" for auto-discovery
# COM_PORT = "/dev/ttyACM0"
# COM_PORT = "COM5"
COM_PORT = "AUTO"

# Display revision: A or B (for "flagship" version, use B) or SIMU for simulated LCD (image written in screencap.png)
# To identify your revision: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions
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
        logger.info("Selected Hardware Revision A (Turing Smart Screen)")
        lcd_comm = LcdCommRevA(com_port=COM_PORT,
                               display_width=320,
                               display_height=480)
    elif REVISION == "B":
        print("Selected Hardware Revision B (XuanFang screen version B / flagship)")
        lcd_comm = LcdCommRevB(com_port=COM_PORT,
                               display_width=320,
                               display_height=480)
    elif REVISION == "SIMU":
        print("Selected Simulated LCD")
        lcd_comm = LcdSimulated(display_width=320,
                                display_height=480)
    else:
        print("ERROR: Unknown revision")
        try:
            sys.exit(0)
        except:
            os._exit(0)

    # Reset screen in case it was in an unstable state (screen is also cleared)
    lcd_comm.Reset()

    # Send initialization commands
    lcd_comm.InitializeComm()

    # Set brightness in % (warning: revision A display can get hot at high brightness!)
    lcd_comm.SetBrightness(level=10)

    # Set backplate RGB LED color (for supported HW only)
    lcd_comm.SetBackplateLedColor(led_color=(255, 255, 255))

    # Set orientation (screen starts in Portrait)
    orientation = Orientation.PORTRAIT
    lcd_comm.SetOrientation(orientation=orientation)

    # Define background picture
    if orientation == Orientation.PORTRAIT or orientation == orientation.REVERSE_PORTRAIT:
        background = "res/backgrounds/example.png"
    else:
        background = "res/backgrounds/example_landscape.png"

    # Display sample picture
    lcd_comm.DisplayBitmap(background)

    # Display sample text
    lcd_comm.DisplayText("Basic text", 50, 100)

    # Display custom text with solid background
    lcd_comm.DisplayText("Custom italic text", 5, 150,
                         font="roboto/Roboto-Italic.ttf",
                         font_size=30,
                         font_color=(0, 0, 255),
                         background_color=(255, 255, 0))

    # Display custom text with transparent background
    lcd_comm.DisplayText("Transparent bold text", 5, 250,
                         font="geforce/GeForce-Bold.ttf",
                         font_size=30,
                         font_color=(255, 255, 255),
                         background_image=background)

    # Display the current time and some progress bars as fast as possible
    bar_value = 0
    while not stop:
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

        lcd_comm.DisplayRadialProgressBar(160, 400,
                                          radius=20, linewidth=5,
                                          min_value=0,
                                          max_value=100,
                                          value=bar_value,
                                          angle_start=-90,
                                          bar_color=(255, 255, 0),
                                          background_image=background)


        bar_value = (bar_value + 2) % 101

    # Close serial connection at exit
    lcd_comm.closeSerial()
