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

import time
from enum import Enum
from typing import Optional

from serial.tools.list_ports import comports

from library.lcd.lcd_comm import *
from library.lcd.serialize import image_to_RGB565, chunked
from library.log import logger


class Command(IntEnum):
    RESET = 101  # Resets the display
    CLEAR = 102  # Clears the display to a white screen
    TO_BLACK = 103  # Makes the screen go black. NOT TESTED
    SCREEN_OFF = 108  # Turns the screen off
    SCREEN_ON = 109  # Turns the screen on
    SET_BRIGHTNESS = 110  # Sets the screen brightness
    SET_ORIENTATION = 121  # Sets the screen orientation
    DISPLAY_BITMAP = 197  # Displays an image on the screen

    # Commands below are only supported by next generation Turing Smart screens
    LCD_28 = 40  # ?
    LCD_29 = 41  # ?
    HELLO = 69  # Asks the screen for its model: 3.5", 5" or 7"
    SET_MIRROR = 122  # Mirrors the rendering on the screen
    DISPLAY_PIXELS = 195  # Displays a list of pixels than can be non-contiguous in one command, useful for line charts


class SubRevision(Enum):
    TURING_3_5 = 0  # Official Turing 3.5 do not answer to HELLO command
    USBMONITOR_3_5 = bytearray([0x01, 0x01, 0x01, 0x01, 0x01, 0x01])
    USBMONITOR_5 = bytearray([0x02, 0x02, 0x02, 0x02, 0x02, 0x02])
    USBMONITOR_7 = bytearray([0x03, 0x03, 0x03, 0x03, 0x03, 0x03])

# This class is for Turing Smart Screen (rev. A) 3.5" and UsbMonitor screens (all sizes)
class LcdCommRevA(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 320, display_height: int = 480,
                 update_queue: Optional[queue.Queue] = None):
        logger.debug("HW revision: A")
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port() -> Optional[str]:
        com_ports = comports()

        for com_port in com_ports:
            if com_port.serial_number == "USB35INCHIPSV2":
                return com_port.device
            if com_port.vid == 0x1a86 and com_port.pid == 0x5722:
                return com_port.device

        return None

    def SendCommand(self, cmd: Command, x: int, y: int, ex: int, ey: int, bypass_queue: bool = False):
        byteBuffer = bytearray(6)
        byteBuffer[0] = (x >> 2)
        byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
        byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
        byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
        byteBuffer[4] = (ey & 255)
        byteBuffer[5] = cmd

        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(byteBuffer)
        else:
            # Lock queue mutex then queue the request
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [byteBuffer]))

    def _hello(self):
        hello = bytearray([Command.HELLO, Command.HELLO, Command.HELLO, Command.HELLO, Command.HELLO, Command.HELLO])

        # This command reads LCD answer on serial link, so it bypasses the queue
        self.WriteData(hello)
        response = self.serial_read(6)
        self.serial_flush_input()

        if response == SubRevision.USBMONITOR_3_5.value:
            self.sub_revision = SubRevision.USBMONITOR_3_5
            self.display_width = 320
            self.display_height = 480
        elif response == SubRevision.USBMONITOR_5.value:
            self.sub_revision = SubRevision.USBMONITOR_5
            self.display_width = 480
            self.display_height = 800
        elif response == SubRevision.USBMONITOR_7.value:
            self.sub_revision = SubRevision.USBMONITOR_7
            self.display_width = 600
            self.display_height = 1024
        else:
            self.sub_revision = SubRevision.TURING_3_5
            self.display_width = 320
            self.display_height = 480

        logger.debug("HW sub-revision: %s" % (str(self.sub_revision)))

    def InitializeComm(self):
        self._hello()

    def Reset(self):
        logger.info("Display reset (COM port may change)...")
        # Reset command bypasses queue because it is run when queue threads are not yet started
        self.SendCommand(Command.RESET, 0, 0, 0, 0, bypass_queue=True)
        self.closeSerial()
        # Wait for display reset then reconnect
        time.sleep(5)
        self.openSerial()

    def Clear(self):
        self.SetOrientation(Orientation.PORTRAIT)  # Bug: orientation needs to be PORTRAIT before clearing
        self.SendCommand(Command.CLEAR, 0, 0, 0, 0)
        self.SetOrientation()  # Restore default orientation

    def ScreenOff(self):
        self.SendCommand(Command.SCREEN_OFF, 0, 0, 0, 0)

    def ScreenOn(self):
        self.SendCommand(Command.SCREEN_ON, 0, 0, 0, 0)

    def SetBrightness(self, level: int = 25):
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        # Display scales from 0 to 255, with 0 being the brightest and 255 being the darkest.
        # Convert our brightness % to an absolute value.
        level_absolute = int(255 - ((level / 100) * 255))

        # Level : 0 (brightest) - 255 (darkest)
        self.SendCommand(Command.SET_BRIGHTNESS, level_absolute, 0, 0, 0)

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        self.orientation = orientation
        width = self.get_width()
        height = self.get_height()
        x = 0
        y = 0
        ex = 0
        ey = 0
        byteBuffer = bytearray(16)
        byteBuffer[0] = (x >> 2)
        byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
        byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
        byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
        byteBuffer[4] = (ey & 255)
        byteBuffer[5] = Command.SET_ORIENTATION
        byteBuffer[6] = (orientation + 100)
        byteBuffer[7] = (width >> 8)
        byteBuffer[8] = (width & 255)
        byteBuffer[9] = (height >> 8)
        byteBuffer[10] = (height & 255)
        self.serial_write(bytes(byteBuffer))

    def DisplayPILImage(
            self,
            image: Image.Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
    ):
        width, height = self.get_width(), self.get_height()

        # If the image height/width isn't provided, use the native image size
        if not image_height:
            image_height = image.size[1]
        if not image_width:
            image_width = image.size[0]

        assert x <= width, 'Image X coordinate must be <= display width'
        assert y <= height, 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'

        # If our image size + the (x, y) position offsets are bigger than
        # our display, reduce the image size to fit our screen
        if x + image_width > width:
            image_width = width - x
        if y + image_height > height:
            image_height = height - y

        if image_width != image.size[0] or image_height != image.size[1]:
            image = image.crop((0, 0, image_width, image_height))

        (x0, y0) = (x, y)
        (x1, y1) = (x + image_width - 1, y + image_height - 1)

        rgb565le = image_to_RGB565(image, "little")

        self.SendCommand(Command.DISPLAY_BITMAP, x0, y0, x1, y1)

        # Lock queue mutex then queue all the requests for the image data
        with self.update_queue_mutex:
            # Send image data by multiple of "display width" bytes
            for chunk in chunked(rgb565le, width * 8):
                self.SendLine(chunk)
