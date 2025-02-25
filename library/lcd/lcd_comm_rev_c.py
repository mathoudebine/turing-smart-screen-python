# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2023-2023  Alex W. Baulé (alexwbaule)
# Copyright (C) 2023-2023  Arthur Ferrai (arthurferrai)
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

import queue
import string
import time
from enum import Enum
from math import ceil
from typing import Optional, Tuple

import serial
from PIL import Image
from serial.tools.list_ports import comports

from library.lcd.lcd_comm import Orientation, LcdComm
from library.lcd.serialize import image_to_BGRA, image_to_BGR, chunked
from library.log import logger


class Count:
    Start = 0


# READ HELLO ALWAYS IS 23.
# ALL READS IS 1024

# ORDER:
# SEND HELLO
# READ HELLO (23)
# SEND STOP_VIDEO
# SEND STOP_MEDIA
# READ STATUS (1024)
# SEND SET_BRIGHTNESS
# SEND SET_OPTIONS WITH ORIENTATION ?
# SEND PRE_UPDATE_BITMAP
# SEND START_DISPLAY_BITMAP
# SEND DISPLAY_BITMAP
# READ STATUS (1024)
# SEND QUERY_STATUS
# READ STATUS (1024)
# WHILE:
#   SEND UPDATE_BITMAP
#   SEND QUERY_STATUS
#   READ STATUS(1024)

class Command(Enum):
    # COMMANDS
    HELLO = bytearray((0x01, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0xc5, 0xd3))
    OPTIONS = bytearray((0x7d, 0xef, 0x69, 0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x2d))
    RESTART = bytearray((0x84, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    TURNOFF = bytearray((0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    TURNON = bytearray((0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x00))

    SET_BRIGHTNESS = bytearray((0x7b, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00))

    # STOP COMMANDS
    STOP_VIDEO = bytearray((0x79, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    STOP_MEDIA = bytearray((0x96, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))

    # IMAGE QUERY STATUS
    QUERY_STATUS = bytearray((0xcf, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))

    # STATIC IMAGE
    START_DISPLAY_BITMAP = bytearray((0x2c,))
    PRE_UPDATE_BITMAP = bytearray((0x86, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    UPDATE_BITMAP = bytearray((0xcc, 0xef, 0x69, 0x00))
    DISPLAY_BITMAP_2INCH = bytearray((0xc8, 0xef, 0x69, 0x00)) + bytearray((0x0E, 0x10))
    DISPLAY_BITMAP_5INCH = bytearray((0xc8, 0xef, 0x69, 0x00)) + bytearray((0x17, 0x70))
    DISPLAY_BITMAP_8INCH = bytearray((0xc8, 0xef, 0x69, 0x00)) + bytearray((0x38, 0x40))

    STARTMODE_DEFAULT = bytearray((0x00,))
    STARTMODE_IMAGE = bytearray((0x01,))
    STARTMODE_VIDEO = bytearray((0x02,))
    FLIP_180 = bytearray((0x01,))
    NO_FLIP = bytearray((0x00,))
    SEND_PAYLOAD = bytearray((0xFF,))

    def __init__(self, command):
        self.command = command


class Padding(Enum):
    NULL = bytearray([0x00])
    START_DISPLAY_BITMAP = bytearray([0x2c])

    def __init__(self, command):
        self.command = command


class SleepInterval(Enum):
    OFF = bytearray((0x00,))
    ONE = bytearray((0x01,))
    TWO = bytearray((0x02,))
    THREE = bytearray((0x03,))
    FOUR = bytearray((0x04,))
    FIVE = bytearray((0x05,))
    SIX = bytearray((0x06,))
    SEVEN = bytearray((0x07,))
    EIGHT = bytearray((0x08,))
    NINE = bytearray((0x09,))
    TEN = bytearray((0x0a,))

    def __init__(self, command):
        self.command = command


class SubRevision(Enum):
    UNKNOWN = ""
    REV_2INCH = "chs_21inch"
    REV_5INCH = "chs_5inch"
    REV_8INCH = "chs_88inch"

    def __init__(self, command):
        self.command = command


# This class is for Turing Smart Screen 2.1" / 5" / 8" screens
class LcdCommRevC(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 480, display_height: int = 800,
                 update_queue: Optional[queue.Queue] = None):
        logger.debug("HW revision: C")
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port() -> Optional[str]:
        com_ports = comports()

        # Try to find awake device through serial number or vid/pid
        for com_port in com_ports:
            if com_port.serial_number == '20080411':
                return com_port.device
            if com_port.vid == 0x0525 and com_port.pid == 0xa4a7:
                return com_port.device
            if com_port.vid == 0x1d6b and (com_port.pid == 0x0121 or com_port.pid == 0x0106):
                return com_port.device

        # Try to find sleeping device and wake it up
        for com_port in com_ports:
            if com_port.serial_number == 'USB7INCH' or com_port.serial_number == 'CT21INCH':
                LcdCommRevC._connect_to_reset_device_name(com_port)
                return LcdCommRevC.auto_detect_com_port()
            if com_port.serial_number == '20080411':
                return com_port.device

        return None

    @staticmethod
    def _connect_to_reset_device_name(com_port):
        # this device enumerates differently when off, we need to connect once to reset it to correct COM device
        try:
            logger.debug(f"Waiting for device {com_port} to be turned ON...")
            serial.Serial(com_port.device, 115200, timeout=1, rtscts=True)
        except serial.SerialException:
            pass
        time.sleep(10)

    def _send_command(self, cmd: Command, payload: Optional[bytearray] = None, padding: Optional[Padding] = None,
                      bypass_queue: bool = False, readsize: Optional[int] = None):
        message = bytearray()

        if cmd != Command.SEND_PAYLOAD:
            message = bytearray(cmd.value)

        # logger.debug("Command: {}".format(cmd.name))

        if not padding:
            padding = Padding.NULL

        if payload:
            message.extend(payload)

        msg_size = len(message)

        if not (msg_size / 250).is_integer():
            pad_size = (250 * ceil(msg_size / 250) - msg_size)
            message += bytearray(padding.value * pad_size)

        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(message)
            if readsize:
                self.ReadData(readsize)
        else:
            # Lock queue mutex then queue the request
            self.update_queue.put((self.WriteData, [message]))
            if readsize:
                self.update_queue.put((self.ReadData, [readsize]))

    def _hello(self):
        # This command reads LCD answer on serial link, so it bypasses the queue
        self.sub_revision = SubRevision.UNKNOWN
        self._send_command(Command.HELLO, bypass_queue=True)
        response = str(self.serial_read(23).decode(errors="ignore"))
        self.serial_flush_input()
        logger.debug("HW sub-revision returned: %s" % ''.join(filter(lambda x: x in set(string.printable), response)))

        # Note: sub-revisions returned by display are not reliable e.g. 2.1" displays return "chs_5inch"
        # if response.startswith(SubRevision.REV_5INCH.value):
        #     self.sub_revision = SubRevision.REV_5INCH
        #     self.display_width = 480
        #     self.display_height = 800
        # elif response.startswith(SubRevision.REV_2INCH.value):
        #     self.sub_revision = SubRevision.REV_2INCH
        #     self.display_width = 480
        #     self.display_height = 480
        # elif response.startswith(SubRevision.REV_8INCH.value):
        #     self.sub_revision = SubRevision.REV_8INCH
        #     self.display_width = 480
        #     self.display_height = 1920
        # else:
        #     logger.warning("Display returned unknown sub-revision on Hello answer (%s)" % str(response))
        # logger.debug("HW sub-revision detected: %s" % (str(self.sub_revision)))

        # Relay on width/height for sub-revision detection
        if self.display_width == 480 and self.display_height == 480:
            self.sub_revision = SubRevision.REV_2INCH
        elif self.display_width == 480 and self.display_height == 800:
            self.sub_revision = SubRevision.REV_5INCH
        elif self.display_width == 480 and self.display_height == 1920:
            self.sub_revision = SubRevision.REV_8INCH
        else:
            logger.error(f"Unsupported resolution {self.display_width}x{self.display_height} for revision C")

    def InitializeComm(self):
        self._hello()

    def Reset(self):
        logger.info("Display reset (COM port may change)...")
        # Reset command bypasses queue because it is run when queue threads are not yet started
        self._send_command(Command.RESTART, bypass_queue=True)
        self.closeSerial()
        # Wait for display reset then reconnect
        time.sleep(15)
        self.openSerial()

    def Clear(self):
        # This hardware does not implement a Clear command: display a blank image on the whole screen
        # Force an orientation in case the screen is currently configured with one different from the theme
        backup_orientation = self.orientation
        self.SetOrientation(orientation=Orientation.PORTRAIT)

        blank = Image.new("RGB", (self.get_width(), self.get_height()), (255, 255, 255))
        self.DisplayPILImage(blank)

        # Restore orientation
        self.SetOrientation(orientation=backup_orientation)

    def ScreenOff(self):
        logger.info("Calling ScreenOff")
        self._send_command(Command.STOP_VIDEO)
        self._send_command(Command.STOP_MEDIA, readsize=1024)
        self._send_command(Command.TURNOFF)

    def ScreenOn(self):
        logger.info("Calling ScreenOn")
        self._send_command(Command.STOP_VIDEO)
        self._send_command(Command.STOP_MEDIA, readsize=1024)
        # self._send_command(Command.SET_BRIGHTNESS, payload=bytearray([255]))

    def SetBrightness(self, level: int = 25):
        # logger.info("Call SetBrightness")
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        # Brightness scales from 0 to 255, with 255 being the brightest and 0 being the darkest.
        # Convert our brightness % to an absolute value.
        converted_level = int((level / 100) * 255)

        self._send_command(Command.SET_BRIGHTNESS, payload=bytearray((converted_level,)), bypass_queue=True)

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        self.orientation = orientation
        # logger.info(f"Call SetOrientation to: {self.orientation.name}")

        # if self.orientation == Orientation.REVERSE_LANDSCAPE or self.orientation == Orientation.REVERSE_PORTRAIT:
        #    b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + Command.FLIP_180.value + SleepInterval.OFF.value
        #    self._send_command(Command.OPTIONS, payload=b)
        # else:
        b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + Command.NO_FLIP.value + SleepInterval.OFF.value
        self._send_command(Command.OPTIONS, payload=b)

    def DisplayPILImage(
            self,
            image: Image.Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
    ):
        # If the image height/width isn't provided, use the native image size
        if not image_height:
            image_height = image.size[1]
        if not image_width:
            image_width = image.size[0]

        # If our image is bigger than our display, resize it to fit our screen
        if image.size[1] > self.get_height():
            image_height = self.get_height()
        if image.size[0] > self.get_width():
            image_width = self.get_width()

        if image_width != image.size[0] or image_height != image.size[1]:
            image = image.crop((0, 0, image_width, image_height))

        assert x <= self.get_width(), 'Image X coordinate must be <= display width'
        assert y <= self.get_height(), 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'

        if x == 0 and y == 0 and (image_width == self.get_width()) and (image_height == self.get_height()):
            with self.update_queue_mutex:
                self._send_command(Command.PRE_UPDATE_BITMAP)
                self._send_command(Command.START_DISPLAY_BITMAP, padding=Padding.START_DISPLAY_BITMAP)

                if self.sub_revision == SubRevision.REV_5INCH:
                    display_bmp_cmd = Command.DISPLAY_BITMAP_5INCH
                elif self.sub_revision == SubRevision.REV_2INCH:
                    display_bmp_cmd = Command.DISPLAY_BITMAP_2INCH
                elif self.sub_revision == SubRevision.REV_8INCH:
                    display_bmp_cmd = Command.DISPLAY_BITMAP_8INCH

                self._send_command(display_bmp_cmd,
                                   payload=bytearray(int(self.display_width * self.display_width / 64).to_bytes(2, "big")))
                self._send_command(Command.SEND_PAYLOAD,
                                   payload=bytearray(self._generate_full_image(image)),
                                   readsize=1024)
                self._send_command(Command.QUERY_STATUS, readsize=1024)
        else:
            with self.update_queue_mutex:
                img, pyd = self._generate_update_image(image, x, y, Count.Start, Command.UPDATE_BITMAP)
                self._send_command(Command.SEND_PAYLOAD, payload=pyd)
                self._send_command(Command.SEND_PAYLOAD, payload=img)
                self._send_command(Command.QUERY_STATUS, readsize=1024)
            Count.Start += 1

    def _generate_full_image(self, image: Image.Image) -> bytes:
        if self.sub_revision == SubRevision.REV_8INCH:
            if self.orientation == Orientation.LANDSCAPE:
                image = image.rotate(270, expand=True)
            elif self.orientation == Orientation.REVERSE_LANDSCAPE:
                image = image.rotate(90, expand=True)
            elif self.orientation == Orientation.PORTRAIT:
                image = image.rotate(180, expand=True)
            elif self.orientation == Orientation.REVERSE_PORTRAIT:
                pass
        else:
            if self.orientation == Orientation.PORTRAIT:
                image = image.rotate(90, expand=True)
            elif self.orientation == Orientation.REVERSE_PORTRAIT:
                image = image.rotate(270, expand=True)
            elif self.orientation == Orientation.REVERSE_LANDSCAPE:
                image = image.rotate(180)

        bgra_data = image_to_BGRA(image)

        return b'\x00'.join(chunked(bgra_data, 249))

    def _generate_update_image(
            self, image: Image.Image, x: int, y: int, count: int, cmd: Optional[Command] = None
    ) -> Tuple[bytearray, bytearray]:
        x0, y0 = x, y
        if self.sub_revision == SubRevision.REV_8INCH:
            if self.orientation == Orientation.LANDSCAPE:
                image = image.rotate(270, expand=True)
                y0 = self.get_height() - y - image.width
            elif self.orientation == Orientation.REVERSE_LANDSCAPE:
                image = image.rotate(90, expand=True)
                x0 = self.get_width() - x - image.height
            elif self.orientation == Orientation.PORTRAIT:
                image = image.rotate(180, expand=True)
                x0 = self.get_height() - y - image.height
                y0 = self.get_height() - x - image.width
            elif self.orientation == Orientation.REVERSE_PORTRAIT:
                x0 = y
                y0 = x
        else:
            if self.orientation == Orientation.PORTRAIT:
                image = image.rotate(90, expand=True)
                x0 = self.get_width() - x - image.height
            elif self.orientation == Orientation.REVERSE_PORTRAIT:
                image = image.rotate(270, expand=True)
                y0 = self.get_height() - y - image.width
            elif self.orientation == Orientation.REVERSE_LANDSCAPE:
                image = image.rotate(180)
                y0 = self.get_width() - x - image.width
                x0 = self.get_height() - y - image.height
            elif self.orientation == Orientation.LANDSCAPE:
                x0 = y
                y0 = x

        img_raw_data = bytearray()
        bgr_data = image_to_BGR(image)
        for h, line in enumerate(chunked(bgr_data, image.width * 3)):
            if self.sub_revision == SubRevision.REV_8INCH:
                img_raw_data += int(((x0 + h) * self.display_width) + y0).to_bytes(3, "big")
            else:
                img_raw_data += int(((x0 + h) * self.display_height) + y0).to_bytes(3, "big")
            img_raw_data += int(image.width).to_bytes(2, "big")
            img_raw_data += line

        image_size = int(len(img_raw_data) + 2).to_bytes(3, "big")  # The +2 is for the "ef69" that will be added later.

        # logger.debug("Render Count: {}".format(count))
        payload = bytearray()

        if cmd:
            payload.extend(cmd.value)
        payload.extend(image_size)
        payload.extend(Padding.NULL.value * 3)
        payload.extend(count.to_bytes(4, 'big'))

        if len(img_raw_data) > 250:
            img_raw_data = bytearray(b'\x00').join(chunked(bytes(img_raw_data), 249))
        img_raw_data += b'\xef\x69'

        return img_raw_data, payload
