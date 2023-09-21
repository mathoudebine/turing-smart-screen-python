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
import time
from enum import Enum
from math import ceil

import serial
from PIL import Image
from serial.tools.list_ports import comports

from library.lcd.lcd_comm import Orientation, LcdComm
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
    UPDATE_BITMAP = bytearray((0xcc, 0xef, 0x69, 0x00, 0x00))

    RESTARTSCREEN = bytearray((0x84, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    DISPLAY_BITMAP = bytearray((0xc8, 0xef, 0x69, 0x00, 0x17, 0x70))

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
    UNKNOWN = bytearray((0x00,))
    FIVEINCH = bytearray(
        (0x63, 0x68, 0x73, 0x5f, 0x35, 0x69, 0x6e, 0x63, 0x68, 0x2e, 0x64, 0x65, 0x76, 0x31, 0x5f, 0x72, 0x6f, 0x6d,
         0x31, 0x2e, 0x38, 0x37, 0x00)
    )

    def __init__(self, command):
        self.command = command


# This class is for Turing Smart Screen 5" screens
class LcdCommRevC(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 480, display_height: int = 800,
                 update_queue: queue.Queue = None):
        logger.debug("HW revision: C")
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port():
        com_ports = comports()

        for com_port in com_ports:
            if com_port.serial_number == 'USB7INCH':
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
            serial.Serial(com_port.device, 115200, timeout=1, rtscts=1)
        except serial.serialutil.SerialException:
            pass
        time.sleep(10)

    def _send_command(self, cmd: Command, payload: bytearray = None, padding: Padding = None,
                      bypass_queue: bool = False, readsize: int = None):
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
        response = self.lcd_serial.read(23)
        self.lcd_serial.flushInput()
        if response == SubRevision.FIVEINCH.value:
            self.sub_revision = SubRevision.FIVEINCH
        else:
            logger.warning("Display returned unknown sub-revision on Hello answer (%s)" % str(response))

        logger.debug("HW sub-revision: %s" % (str(self.sub_revision)))

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

        if self.orientation == Orientation.REVERSE_LANDSCAPE or self.orientation == Orientation.REVERSE_PORTRAIT:
            b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + Command.FLIP_180.value + SleepInterval.OFF.value
            self._send_command(Command.OPTIONS, payload=b)
        else:
            b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + Command.NO_FLIP.value + SleepInterval.OFF.value
            self._send_command(Command.OPTIONS, payload=b)

    def DisplayPILImage(
            self,
            image: Image,
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

        assert x <= self.get_width(), 'Image X coordinate must be <= display width'
        assert y <= self.get_height(), 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'

        if x == 0 and y == 0 and (image_width == self.get_width()) and (image_height == self.get_height()):
            with self.update_queue_mutex:
                self._send_command(Command.PRE_UPDATE_BITMAP)
                self._send_command(Command.START_DISPLAY_BITMAP, padding=Padding.START_DISPLAY_BITMAP)
                self._send_command(Command.DISPLAY_BITMAP)
                self._send_command(Command.SEND_PAYLOAD,
                                   payload=bytearray(self._generate_full_image(image, self.orientation)),
                                   readsize=1024)
                self._send_command(Command.QUERY_STATUS, readsize=1024)
        else:
            with self.update_queue_mutex:
                img, pyd = self._generate_update_image(image, x, y, Count.Start, Command.UPDATE_BITMAP,
                                                       self.orientation)
                self._send_command(Command.SEND_PAYLOAD, payload=pyd)
                self._send_command(Command.SEND_PAYLOAD, payload=img)
                self._send_command(Command.QUERY_STATUS, readsize=1024)
            Count.Start += 1

    @staticmethod
    def _generate_full_image(image: Image, orientation: Orientation = Orientation.PORTRAIT):
        if orientation == Orientation.PORTRAIT:
            image = image.rotate(90, expand=True)
        elif orientation == Orientation.REVERSE_PORTRAIT:
            image = image.rotate(270, expand=True)
        elif orientation == Orientation.REVERSE_LANDSCAPE:
            image = image.rotate(180)

        image_data = image.convert("RGBA").load()
        image_ret = ''
        for y in range(image.height):
            for x in range(image.width):
                pixel = image_data[x, y]
                image_ret += f'{pixel[2]:02x}{pixel[1]:02x}{pixel[0]:02x}{pixel[3]:02x}'

        hex_data = bytearray.fromhex(image_ret)
        return b'\x00'.join(hex_data[i:i + 249] for i in range(0, len(hex_data), 249))

    def _generate_update_image(self, image, x, y, count, cmd: Command = None,
                               orientation: Orientation = Orientation.PORTRAIT):
        x0, y0 = x, y

        if orientation == Orientation.PORTRAIT:
            image = image.rotate(90, expand=True)
            x0 = self.get_width() - x - image.height
        elif orientation == Orientation.REVERSE_PORTRAIT:
            image = image.rotate(270, expand=True)
            y0 = self.get_height() - y - image.width
        elif orientation == Orientation.REVERSE_LANDSCAPE:
            image = image.rotate(180, expand=True)
            y0 = self.get_width() - x - image.width
            x0 = self.get_height() - y - image.height
        elif orientation == Orientation.LANDSCAPE:
            x0, y0 = y, x

        img_raw_data = []
        image_data = image.convert("RGBA").load()
        for h in range(image.height):
            img_raw_data.append(f'{((x0 + h) * self.display_height) + y0:06x}{image.width:04x}')
            for w in range(image.width):
                current_pixel = image_data[w, h]
                img_raw_data.append(f'{current_pixel[2]:02x}{current_pixel[1]:02x}{current_pixel[0]:02x}')

        image_msg = ''.join(img_raw_data)
        image_size = f'{int((len(image_msg) / 2) + 2):04x}'  # The +2 is for the "ef69" that will be added later.

        # logger.debug("Render Count: {}".format(count))
        payload = bytearray()

        if cmd:
            payload.extend(cmd.value)
        payload.extend(bytearray.fromhex(image_size))
        payload.extend(Padding.NULL.value * 3)
        payload.extend(count.to_bytes(4, 'big'))

        if len(image_msg) > 500:
            image_msg = '00'.join(image_msg[i:i + 498] for i in range(0, len(image_msg), 498))
        image_msg += 'ef69'

        return bytearray.fromhex(image_msg), payload
