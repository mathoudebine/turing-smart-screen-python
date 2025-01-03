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

import struct
from enum import Enum

from serial.tools.list_ports import comports

from library.lcd.lcd_comm import *
from library.log import logger


class Command(Enum):
    GETINFO = bytearray((71, 00, 00, 00))
    SETORG = bytearray((67, 72, 00, 00))       # Set portrait orientation
    SET180 = bytearray((67, 71, 00, 00))       # Set reverse portrait orientation
    SETHF = bytearray((67, 68, 00, 00))        # Set portrait orientation with horizontal mirroring
    SETVF = bytearray((67, 70, 00, 00))        # Set reverse portrait orientation with horizontal mirroring
    SETBL = bytearray((67, 67))                # Brightness setting
    DISPCOLOR = bytearray((67, 66))            # Display RGB565 color on whole screen
    BLOCKWRITE = bytearray((67, 65))           # Send bitmap size
    INTOPICMODE = bytearray((68, 00, 00, 00))  # Start bitmap transmission
    OUTPICMODE = bytearray((65, 00, 00, 00))   # End bitmap transmission


# This class is for Kipye Qiye Smart Display 3.5"
class LcdCommRevD(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 320, display_height: int = 480,
                 update_queue: queue.Queue = None):
        logger.debug("HW revision: D")
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port():
        com_ports = comports()
        auto_com_port = None

        for com_port in com_ports:
            if com_port.vid == 0x454d and com_port.pid == 0x4e41:
                auto_com_port = com_port.device
                break

        return auto_com_port

    def WriteData(self, byteBuffer: bytearray):
        LcdComm.WriteData(self, byteBuffer)

        # Empty the input buffer after each write: we don't process acknowledgements the screen sends back
        self.lcd_serial.reset_input_buffer()

    def SendCommand(self, cmd: Command, payload: bytearray = None, bypass_queue: bool = False):
        message = bytearray(cmd.value)

        if payload:
            message.extend(payload)

        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(message)
        else:
            # Lock queue mutex then queue the request
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [message]))

    def InitializeComm(self):
        pass

    def Reset(self):
        # HW revision D does not implement a command to reset it: clear display instead
        self.Clear()

    def Clear(self):
        # HW revision D does not implement a Clear command: display a blank image on the whole screen
        color = 0xFFFF  # RGB565 White color
        color_bytes = bytearray(color.to_bytes(2))
        self.SendCommand(cmd=Command.DISPCOLOR, payload=color_bytes)

    def ScreenOff(self):
        # HW revision D does not implement a "ScreenOff" native command: using SetBrightness(0) instead
        self.SetBrightness(0)

    def ScreenOn(self):
        # HW revision D does not implement a "ScreenOn" native command: using SetBrightness() instead
        self.SetBrightness()

    def SetBrightness(self, level: int = 25):
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        # Brightness scales from 0 to 500, with 500 being the brightest and 0 being the darkest.
        # Convert our brightness % to an absolute value.
        converted_level = level * 5

        level_bytes = bytearray(converted_level.to_bytes(2))

        # Send the command twice because sometimes it is not applied...
        self.SendCommand(cmd=Command.SETBL, payload=level_bytes)
        self.SendCommand(cmd=Command.SETBL, payload=level_bytes)

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        # In revision D, reverse orientations (reverse portrait / reverse landscape) are managed by the display
        # Basic orientations (portrait / landscape) are software-managed because screen commands only support portrait
        self.orientation = orientation

        if self.orientation == Orientation.REVERSE_LANDSCAPE or self.orientation == Orientation.REVERSE_PORTRAIT:
            self.SendCommand(cmd=Command.SET180)
        else:
            self.SendCommand(cmd=Command.SETORG)

    def DisplayPILImage(
            self,
            image: Image,
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

        if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.REVERSE_PORTRAIT:
            (x0, y0) = (x, y)
            (x1, y1) = (x + image_width - 1, y + image_height - 1)
        else:
            # Landscape / reverse landscape orientations are software managed: rotate image -90° and get new coordinates
            image = image.rotate(270, expand=True)
            (x0, y0) = (self.display_width - y - image_height, x)
            (x1, y1) = (self.display_width - y - 1, x + image_width - 1)
            image_width, image_height = image_height, image_width

        # Send bitmap size
        image_data = bytearray(x0.to_bytes(2))
        image_data += bytearray(x1.to_bytes(2))
        image_data += bytearray(y0.to_bytes(2))
        image_data += bytearray(y1.to_bytes(2))
        self.SendCommand(cmd=Command.BLOCKWRITE, payload=image_data)

        # Prepare bitmap data transmission
        self.SendCommand(Command.INTOPICMODE)

        pix = image.load()
        line = bytes([80])

        # Lock queue mutex then queue all the requests for the image data
        with self.update_queue_mutex:
            for h in range(image_height):
                for w in range(image_width):
                    R = pix[w, h][0] >> 3
                    G = pix[w, h][1] >> 2
                    B = pix[w, h][2] >> 3

                    # Color information is 0bRRRRRGGGGGGBBBBB
                    # Revision A: Encode in Little-Endian (native x86/ARM encoding)
                    # Revition B: Encode in Big-Endian
                    rgb = (R << 11) | (G << 5) | B
                    line += struct.pack('>H', rgb)

                    # Send image data by multiple of 64 bytes + 1 command byte
                    if len(line) >= 65:
                        self.SendLine(line[0:64])
                        line = bytes([80]) + line[64:]

            # Write last line if needed
            if len(line) > 0:
                self.SendLine(line)

        # Indicate the complete bitmap has been transmitted
        self.SendCommand(Command.OUTPICMODE)
