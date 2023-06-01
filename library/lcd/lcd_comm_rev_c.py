# turing-smart-screen-python - a Python system monitor and library for 3.5" USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
import time

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

import numpy
import cv2
from math import ceil
from serial.tools.list_ports import comports
from library.lcd.lcd_comm import *
from library.log import logger
from enum import Enum
import sys


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
# SEND UPDATE_BITMAP
# SEND QUERY_STATUS
# READ STATUS(1024)


# 1705ff251705ff 251705ff251705ff25
# 1705ff251705ff 261805ff251705ff23


class Command(Enum):
    # COMMANDS
    HELLO = bytearray([0x01, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0xc5, 0xd3])
    OPTIONS = bytearray([0x7d, 0xef, 0x69, 0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x2d])
    TURNOFF = bytearray([0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01])
    TURNON = bytearray([0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x00])
    SET_BRIGHTNESS = bytearray(
        [0x7b, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00])  # Sets the screen brightness

    # STOP COMMANDS
    STOP_VIDEO = bytearray([0x79, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01])
    STOP_MEDIA = bytearray([0x96, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01])

    # IMAGE QUERY STATUS
    QUERY_STATUS = bytearray([0xcf, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01])

    # STATIC IMAGE
    START_DISPLAY_BITMAP = bytearray([0x2c])
    PRE_UPDATE_BITMAP = bytearray([0x86, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01])
    UPDATE_BITMAP = bytearray([0xcc, 0xef, 0x69, 0x00, 0x00])

    RESTARTSCREEN = bytearray([0x84, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01])
    DISPLAY_BITMAP = bytearray([0xc8, 0xef, 0x69, 0x00, 0x17, 0x70])  # Displays an image on the screen

    STARTMODE_DEFAULT = bytearray([0x00])
    STARTMODE_IMAGE = bytearray([0x01])
    STARTMODE_VIDEO = bytearray([0x02])
    ORIENTATION_PORTRAIT = bytearray([0x00])
    ORIENTATION_LANDSCAPE = bytearray([0x01])
    ORIENTATION_REVERSE_PORTRAIT = bytearray([0x00])
    ORIENTATION_REVERSE_LANDSCAPE = bytearray([0x01])
    SEND_PAYLOAD = bytearray([0xFF])

    def __init__(self, command):
        self.command = command


class Padding(Enum):
    NULL = bytearray([0x00])
    START_DISPLAY_BITMAP = bytearray([0x2c])

    def __init__(self, command):
        self.command = command


class Orientation(IntEnum):
    PORTRAIT = 0
    LANDSCAPE = 2
    REVERSE_PORTRAIT = 1
    REVERSE_LANDSCAPE = 3


class SleepInterval(Enum):
    OFF = bytearray([0x00])
    ONE = bytearray([0x01])
    TWO = bytearray([0x02])
    THREE = bytearray([0x03])
    FOUR = bytearray([0x04])
    FIVE = bytearray([0x05])
    SIX = bytearray([0x06])
    SEVEN = bytearray([0x07])
    EIGHT = bytearray([0x08])
    NINE = bytearray([0x09])
    TEN = bytearray([0x0a])

    def __init__(self, command):
        self.command = command


class SubRevision(Enum):
    UNKNOWN = bytearray([0x00])
    FIVEINCH = bytearray(
        [0x63, 0x68, 0x73, 0x5f, 0x35, 0x69, 0x6e, 0x63, 0x68, 0x2e, 0x64, 0x65, 0x76, 0x31, 0x5f, 0x72, 0x6f, 0x6d,
         0x31, 0x2e, 0x38, 0x37, 0x00])

    def __init__(self, command):
        self.command = command


class LcdCommRevC(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 480, display_height: int = 800,
                 update_queue: queue.Queue = None):
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    def is_flagship(self):
        return False

    def is_brightness_range(self):
        return True

    @staticmethod
    def auto_detect_com_port():
        com_ports = comports()
        auto_com_port = None

        for com_port in com_ports:
            if com_port.serial_number == "2017-2-25":
                auto_com_port = com_port.device

        return auto_com_port

    def SendCommand(self, cmd: Command, payload: bytearray = None, padding: Padding = None, bypass_queue: bool = False,
                    readsize: int = None):
        message = bytearray()

        if cmd != Command.SEND_PAYLOAD:
            message = cmd.value

        logger.info("Command: {}".format(cmd.name))

        # logger.info("Original Size: {}".format(len(message)))

        if not padding:
            padding = Padding.NULL

        if payload:
            message.extend(payload)

        msg_size = len(message)

        logger.info("Payloaded Size: {}".format(len(message)))

        if cmd == Command.UPDATE_BITMAP:
            logger.info("Command: {}".format(cmd.value))
            logger.info("Payload: {}".format(payload))

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
                self.update_queue.put((self.ReadData, readsize))

    def Hello(self):
        # logger.info("Call Hello")
        self.sub_revision = SubRevision.UNKNOWN
        # This command reads LCD answer on serial link, so it bypasses the queue
        self.SendCommand(Command.HELLO, bypass_queue=False)
        response = self.lcd_serial.read(23)
        msg_size = len(response)
        self.lcd_serial.flushInput()
        sys.stdout.write("0x01\t{}\t{}\r\n".format(msg_size, ''.join(format(x, '02x') for x in response)))
        logger.info(response)
        if response == SubRevision.FIVEINCH.value:
            self.sub_revision = SubRevision.FIVEINCH
        else:
            logger.warning("Display returned unknown sub-revision on Hello answer")

        logger.debug("HW sub-revision: %s" % (str(self.sub_revision)))

    def InitializeComm(self):
        # logger.info("Call InitializeComm")
        self.Hello()

    def Reset(self):
        # logger.info("Calling RESET")
        return

    def Clear(self):
        # logger.info("Calling CLEAR")
        # HW revision B does not implement a Clear command: display a blank image on the whole screen
        # Force an orientation in case the screen is currently configured with one different from the theme3

        return
        backup_orientation = self.orientation
        self.SetOrientation(orientation=Orientation.PORTRAIT)

        blank = Image.new("RGB", (self.get_width(), self.get_height()), (255, 255, 255))
        self.DisplayPILImage(blank)

        # Restore orientation
        self.SetOrientation(orientation=backup_orientation)

    def ScreenOff(self):
        logger.info("Calling ScreenOff")
        self.SendCommand(Command.STOP_VIDEO, bypass_queue=False)
        self.SendCommand(Command.STOP_MEDIA, bypass_queue=False, readsize=1024)

    def ScreenOn(self):
        logger.info("Calling ScreenOn")
        self.SendCommand(Command.STOP_VIDEO, bypass_queue=False)
        self.SendCommand(Command.STOP_MEDIA, bypass_queue=False, readsize=1024)

    def SetBrightness(self, level: int = 25):
        # logger.info("Call SetBrightness")
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        if self.is_brightness_range():
            # Brightness scales from 0 to 255, with 255 being the brightest and 0 being the darkest.
            # Convert our brightness % to an absolute value.
            converted_level = int((level / 100) * 255)
        else:
            # Brightness is 1 (off) or 0 (full brightness)
            # logger.info("Your display does not support custom brightness level")
            converted_level = 1 if level == 0 else 0

        self.SendCommand(Command.SET_BRIGHTNESS, payload=bytearray([converted_level]), bypass_queue=False)

    def SetBackplateLedColor(self, led_color: Tuple[int, int, int] = (255, 255, 255)):
        # logger.info("Call SetBackplateLedColor")
        pass

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT, new_width: int = 480,
                       new_height: int = 800):
        logger.info("Call SetOrientation")
        return
        self.orientation = orientation
        logger.info(self.orientation)
        if self.orientation.name == Orientation.PORTRAIT.name or self.orientation.name == Orientation.REVERSE_PORTRAIT.name:
            b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + Command.ORIENTATION_PORTRAIT.value + SleepInterval.OFF.value
            self.SendCommand(Command.OPTIONS, payload=b, bypass_queue=False)
        else:
            b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + Command.ORIENTATION_LANDSCAPE.value + SleepInterval.OFF.value
            self.SendCommand(Command.OPTIONS, payload=b, bypass_queue=False)

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

        logger.info(
            "Call DisplayPILImage {} {} {} {}={} {}={}".format(image, x, y, image_width, self.get_width(), image_height,
                                                               self.get_height()))

        # If our image is bigger than our display, resize it to fit our screen
        if image.size[1] > self.get_height():
            image_height = self.get_height()
        if image.size[0] > self.get_width():
            image_width = self.get_width()

        assert x <= self.get_width(), 'Image X coordinate must be <= display width'
        assert y <= self.get_height(), 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'

        device_height = self.get_height()
        device_width = self.get_width()

        #if self.orientation == Orientation.LANDSCAPE:
        #    (x, y) = y, x


        if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.LANDSCAPE:
            (x0, y0) = (x, y)
            (x1, y1) = (x + image_width - 1, y + image_height - 1)
        else:
            (x, y) = y, x
            (x0, y0) = (self.get_width() - x - image_width, self.get_height() - y - image_height)
            (x1, y1) = (self.get_width() - x - 1, self.get_height() - y - 1)

        # logger.info("Calling DisplayPILImage {} {} {} {}={} {}={}".format(image, x, y, image_width, device_width, image_height, device_height))



        #opencvImage = cv2.cvtColor(numpy.array(image), cv2.COLOR_RGB2BGR)
        opencvImage = image


        if x == 0 and y == 0:
            logger.info("Call DisplayPILImage DISPLAY_BITMAP x={} y={} width={} height={}".format(x, y, image_width, image_height))
            image.save("images/DISPLAY_BITMAP-{}-{}-{}-{}.png".format(x, y, image_width, image_height))
            #cv2.imwrite("images-cv2/DISPLAY_BITMAP-{}-{}-{}-{}.png".format(x, y, image_width, image_height), opencvImage)
            with self.update_queue_mutex:

                self.SendCommand(Command.PRE_UPDATE_BITMAP, bypass_queue=False)
                self.SendCommand(Command.START_DISPLAY_BITMAP, padding=Padding.START_DISPLAY_BITMAP, bypass_queue=False)
                self.SendCommand(Command.DISPLAY_BITMAP, bypass_queue=False)
                self.SendCommand(Command.SEND_PAYLOAD, payload=bytearray(_generateFullImage(opencvImage)), bypass_queue=False, readsize=1024)
                self.SendCommand(Command.QUERY_STATUS, bypass_queue=False, readsize=1024)
        else:
            logger.info("Call DisplayPILImage UPDATE_BITMAP x={} y={} width={} height={}".format(x, y, image_width, image_height))
            image.save("images/UPDATE_BITMAP-{}-{}-{}-{}-{}.png".format(Count.Start, x, y, image_width, image_height))
            #cv2.imwrite("images-cv2/UPDATE_BITMAP-{}-{}-{}-{}-{}.png".format(Count.Start, 30, 50, image_width, image_height), opencvImage)
            with self.update_queue_mutex:

                img, pyd = _generateUpdateImage(opencvImage, x, y, Count.Start, Command.UPDATE_BITMAP)
                self.SendCommand(Command.SEND_PAYLOAD, payload=pyd, bypass_queue=False)
                self.SendCommand(Command.SEND_PAYLOAD, payload=img, bypass_queue=False)
                self.SendCommand(Command.QUERY_STATUS, bypass_queue=False, readsize=1024)
            Count.Start += 1



def _generateFullImage(image):
    image = cv2.cvtColor(numpy.array(image), cv2.COLOR_RGB2BGRA)
    image = bytearray(numpy.array(image))
    image = b'\x00'.join(image[i:i + 249] for i in range(0, len(image), 249))
    return image


def _generateUpdateImage(image, x, y, count, cmd: Command = None):
    image = cv2.cvtColor(numpy.array(image), cv2.COLOR_RGB2BGRA)

    width = image.shape[1]
    height = image.shape[0]
    payload = bytearray()

    image_msg = ''
    for h in range(height):
        image_msg += f'{((x + h) * 800) + y:06x}' + f'{width:04x}'
        for w in range(width):
            # #logger.info("h: {} - w: {}".format(h, w))
            image_msg += f'{image[h][w][0]:02x}' + f'{image[h][w][1]:02x}' + f'{image[h][w][2]:02x}'

    image_size = f'{int((len(image_msg) / 2) + 2):04x}'  # The +2 is for the "ef69" that will be added later.

    logger.info("Render Count: {}".format(count))
    payload.extend(cmd.value)
    payload.extend(bytearray.fromhex(image_size))
    payload.extend(Padding.NULL.value * 3)
    payload.extend(count.to_bytes(4, 'big'))

    if len(image_msg) > 500:
        image_msg = '00'.join(image_msg[i:i + 498] for i in range(0, len(image_msg), 498))
    image_msg += 'ef69'

    return bytearray.fromhex(image_msg), payload
