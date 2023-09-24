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

import copy
import math
import os
import queue
import sys
import threading
import time
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Tuple

import serial
from PIL import Image, ImageDraw, ImageFont

from library.log import logger


class Orientation(IntEnum):
    PORTRAIT = 0
    LANDSCAPE = 2
    REVERSE_PORTRAIT = 1
    REVERSE_LANDSCAPE = 3


class LcdComm(ABC):
    def __init__(self, com_port: str = "AUTO", display_width: int = 320, display_height: int = 480,
                 update_queue: queue.Queue = None):
        self.lcd_serial = None

        # String containing absolute path to serial port e.g. "COM3", "/dev/ttyACM1" or "AUTO" for auto-discovery
        self.com_port = com_port

        # Display always start in portrait orientation by default
        self.orientation = Orientation.PORTRAIT
        # Display width in default orientation (portrait)
        self.display_width = display_width
        # Display height in default orientation (portrait)
        self.display_height = display_height

        # Queue containing the serial requests to send to the screen. An external thread should run to process requests
        # on the queue. If you want serial requests to be done in sequence, set it to None
        self.update_queue = update_queue

        # Mutex to protect the queue in case a thread want to add multiple requests (e.g. image data) that should not be
        # mixed with other requests in-between
        self.update_queue_mutex = threading.Lock()

        # Create a cache to store opened images, to avoid opening and loading from the filesystem every time
        self.image_cache = {}  # { key=path, value=PIL.Image }

        # Create a cache to store opened fonts, to avoid opening and loading from the filesystem every time
        self.font_cache = {}  # { key=(font, size), value=PIL.ImageFont }

    def get_width(self) -> int:
        if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.REVERSE_PORTRAIT:
            return self.display_width
        else:
            return self.display_height

    def get_height(self) -> int:
        if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.REVERSE_PORTRAIT:
            return self.display_height
        else:
            return self.display_width

    def openSerial(self):
        if self.com_port == 'AUTO':
            self.com_port = self.auto_detect_com_port()
            if not self.com_port:
                logger.error(
                    "Cannot find COM port automatically, please run Configuration again and select COM port manually")
                try:
                    sys.exit(0)
                except:
                    os._exit(0)
            else:
                logger.debug(f"Auto detected COM port: {self.com_port}")
        else:
            logger.debug(f"Static COM port: {self.com_port}")

        try:
            self.lcd_serial = serial.Serial(self.com_port, 115200, timeout=1, rtscts=1)
        except Exception as e:
            logger.error(f"Cannot open COM port {self.com_port}: {e}")
            try:
                sys.exit(0)
            except:
                os._exit(0)

    def closeSerial(self):
        try:
            self.lcd_serial.close()
        except:
            pass

    def WriteData(self, byteBuffer: bytearray):
        self.WriteLine(bytes(byteBuffer))

    def SendLine(self, line: bytes):
        if self.update_queue:
            # Queue the request. Mutex is locked by caller to queue multiple lines
            self.update_queue.put((self.WriteLine, [line]))
        else:
            # If no queue for async requests: do request now
            self.WriteLine(line)

    def WriteLine(self, line: bytes):
        try:
            self.lcd_serial.write(line)
        except serial.serialutil.SerialTimeoutException:
            # We timed-out trying to write to our device, slow things down.
            logger.warning("(Write line) Too fast! Slow down!")
        except serial.serialutil.SerialException:
            # Error writing data to device: close and reopen serial port, try to write again
            logger.error(
                "SerialException: Failed to send serial data to device. Closing and reopening COM port before retrying once.")
            self.closeSerial()
            time.sleep(1)
            self.openSerial()
            self.lcd_serial.write(line)

    def ReadData(self, readSize: int):
        try:
            response = self.lcd_serial.read(readSize)
            # logger.debug("Received: [{}]".format(str(response, 'utf-8')))
            return response
        except serial.serialutil.SerialTimeoutException:
            # We timed-out trying to read from our device, slow things down.
            logger.warning("(Read data) Too fast! Slow down!")
        except serial.serialutil.SerialException:
            # Error writing data to device: close and reopen serial port, try to read again
            logger.error(
                "SerialException: Failed to read serial data from device. Closing and reopening COM port before retrying once.")
            self.closeSerial()
            time.sleep(1)
            self.openSerial()
            return self.lcd_serial.read(readSize)

    @staticmethod
    @abstractmethod
    def auto_detect_com_port():
        pass

    @abstractmethod
    def InitializeComm(self):
        pass

    @abstractmethod
    def Reset(self):
        pass

    @abstractmethod
    def Clear(self):
        pass

    @abstractmethod
    def ScreenOff(self):
        pass

    @abstractmethod
    def ScreenOn(self):
        pass

    @abstractmethod
    def SetBrightness(self, level: int):
        pass

    def SetBackplateLedColor(self, led_color: Tuple[int, int, int] = (255, 255, 255)):
        pass

    @abstractmethod
    def SetOrientation(self, orientation: Orientation):
        pass

    @abstractmethod
    def DisplayPILImage(
            self,
            image: Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
    ):
        pass

    def DisplayBitmap(self, bitmap_path: str, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        image = self.open_image(bitmap_path)
        self.DisplayPILImage(image, x, y, width, height)

    def DisplayText(
            self,
            text: str,
            x: int = 0,
            y: int = 0,
            font: str = "roboto-mono/RobotoMono-Regular.ttf",
            font_size: int = 20,
            font_color: Tuple[int, int, int] = (0, 0, 0),
            background_color: Tuple[int, int, int] = (255, 255, 255),
            background_image: str = None,
            align: str = 'left',
            anchor: str = None,
    ):
        # Convert text to bitmap using PIL and display it
        # Provide the background image path to display text with transparent background

        if isinstance(font_color, str):
            font_color = tuple(map(int, font_color.split(', ')))

        if isinstance(background_color, str):
            background_color = tuple(map(int, background_color.split(', ')))

        assert x <= self.get_width(), 'Text X coordinate ' + str(x) + ' must be <= display width ' + str(
            self.get_width())
        assert y <= self.get_height(), 'Text Y coordinate ' + str(y) + ' must be <= display height ' + str(
            self.get_height())
        assert len(text) > 0, 'Text must not be empty'
        assert font_size > 0, "Font size must be > 0"

        if background_image is None:
            # A text bitmap is created with max width/height by default : text with solid background
            text_image = Image.new(
                'RGB',
                (self.get_width(), self.get_height()),
                background_color
            )
        else:
            # The text bitmap is created from provided background image : text with transparent background
            text_image = self.open_image(background_image)

        # Get text bounding box
        if (font, font_size) not in self.font_cache:
            self.font_cache[(font, font_size)] = ImageFont.truetype("./res/fonts/" + font, font_size)
        font = self.font_cache[(font, font_size)]
        d = ImageDraw.Draw(text_image)
        left, top, right, bottom = d.textbbox((x, y), text, font=font, align=align, anchor=anchor)

        # textbbox may return float values, which is not good for the bitmap operations below.
        # Let's extend the bounding box to the next whole pixel in all directions
        left, top = math.floor(left), math.floor(top)
        right, bottom = math.ceil(right), math.ceil(bottom)

        # Draw text onto the background image with specified color & font
        d.text((x, y), text, font=font, fill=font_color, align=align, anchor=anchor)

        # Restrict the dimensions if they overflow the display size
        left = max(left, 0)
        top = max(top, 0)
        right = min(right, self.get_width())
        bottom = min(bottom, self.get_height())

        # Crop text bitmap to keep only the text
        text_image = text_image.crop(box=(left, top, right, bottom))

        self.DisplayPILImage(text_image, left, top)

    def DisplayProgressBar(self, x: int, y: int, width: int, height: int, min_value: int = 0, max_value: int = 100,
                           value: int = 50,
                           bar_color: Tuple[int, int, int] = (0, 0, 0),
                           bar_outline: bool = True,
                           background_color: Tuple[int, int, int] = (255, 255, 255),
                           background_image: str = None):
        # Generate a progress bar and display it
        # Provide the background image path to display progress bar with transparent background

        if isinstance(bar_color, str):
            bar_color = tuple(map(int, bar_color.split(', ')))

        if isinstance(background_color, str):
            background_color = tuple(map(int, background_color.split(', ')))

        assert x <= self.get_width(), 'Progress bar X coordinate must be <= display width'
        assert y <= self.get_height(), 'Progress bar Y coordinate must be <= display height'
        assert x + width <= self.get_width(), 'Progress bar width exceeds display width'
        assert y + height <= self.get_height(), 'Progress bar height exceeds display height'

        # Don't let the set value exceed our min or max value, this is bad :)
        if value < min_value:
            value = min_value
        elif max_value < value:
            value = max_value

        assert min_value <= value <= max_value, 'Progress bar value shall be between min and max'

        if background_image is None:
            # A bitmap is created with solid background
            bar_image = Image.new('RGB', (width, height), background_color)
        else:
            # A bitmap is created from provided background image
            bar_image = self.open_image(background_image)

            # Crop bitmap to keep only the progress bar background
            bar_image = bar_image.crop(box=(x, y, x + width, y + height))

        # Draw progress bar
        bar_filled_width = (value / (max_value - min_value) * width) - 1
        if bar_filled_width < 0:
            bar_filled_width = 0
        draw = ImageDraw.Draw(bar_image)
        draw.rectangle([0, 0, bar_filled_width, height - 1], fill=bar_color, outline=bar_color)

        if bar_outline:
            # Draw outline
            draw.rectangle([0, 0, width - 1, height - 1], fill=None, outline=bar_color)

        self.DisplayPILImage(bar_image, x, y)

    def DisplayRadialProgressBar(self, xc: int, yc: int, radius: int, bar_width: int,
                                 min_value: int = 0,
                                 max_value: int = 100,
                                 angle_start: int = 0,
                                 angle_end: int = 360,
                                 angle_sep: int = 5,
                                 angle_steps: int = 10,
                                 clockwise: bool = True,
                                 value: int = 50,
                                 text: str = None,
                                 with_text: bool = True,
                                 font: str = "roboto/Roboto-Black.ttf",
                                 font_size: int = 20,
                                 font_color: Tuple[int, int, int] = (0, 0, 0),
                                 bar_color: Tuple[int, int, int] = (0, 0, 0),
                                 background_color: Tuple[int, int, int] = (255, 255, 255),
                                 background_image: str = None):
        # Generate a radial progress bar and display it
        # Provide the background image path to display progress bar with transparent background

        if isinstance(bar_color, str):
            bar_color = tuple(map(int, bar_color.split(', ')))

        if isinstance(background_color, str):
            background_color = tuple(map(int, background_color.split(', ')))

        if isinstance(font_color, str):
            font_color = tuple(map(int, font_color.split(', ')))

        if angle_start % 361 == angle_end % 361:
            if clockwise:
                angle_start += 0.1
            else:
                angle_end += 0.1

        assert xc - radius >= 0 and xc + radius <= self.get_width(), 'Progress bar width exceeds display width'
        assert yc - radius >= 0 and yc + radius <= self.get_height(), 'Progress bar height exceeds display height'
        assert 0 < bar_width <= radius, f'Progress bar linewidth is {bar_width}, must be > 0 and <= radius'
        assert angle_end % 361 != angle_start % 361, f'Invalid angles values, start = {angle_start}, end = {angle_end}'
        assert isinstance(angle_steps, int), 'angle_steps value must be an integer'
        assert angle_sep >= 0, 'Provide an angle_sep value >= 0'
        assert angle_steps > 0, 'Provide an angle_step value > 0'
        assert angle_sep * angle_steps < 360, 'Given angle_sep and angle_steps values are not correctly set'

        # Don't let the set value exceed our min or max value, this is bad :)
        if value < min_value:
            value = min_value
        elif max_value < value:
            value = max_value

        assert min_value <= value <= max_value, 'Progress bar value shall be between min and max'

        diameter = 2 * radius
        bbox = (xc - radius, yc - radius, xc + radius, yc + radius)
        #
        if background_image is None:
            # A bitmap is created with solid background
            bar_image = Image.new('RGB', (diameter, diameter), background_color)
        else:
            # A bitmap is created from provided background image
            bar_image = self.open_image(background_image)

            # Crop bitmap to keep only the progress bar background
            bar_image = bar_image.crop(box=bbox)

        # Draw progress bar
        pct = (value - min_value) / (max_value - min_value)
        draw = ImageDraw.Draw(bar_image)

        # PIL arc method uses angles with
        #  . 3 o'clock for 0
        #  . clockwise from angle start to angle end
        angle_start %= 361
        angle_end %= 361
        #
        if clockwise:
            if angle_end < angle_start:
                ecart = 360 - angle_start + angle_end
            else:
                ecart = angle_end - angle_start
            #
            # solid bar case
            if angle_sep == 0:
                if angle_end < angle_start:
                    angleE = angle_start + pct * ecart
                    angleS = angle_start
                else:
                    angleS = angle_start
                    angleE = angle_start + pct * ecart
                draw.arc([0, 0, diameter - 1, diameter - 1], angleS, angleE,
                         fill=bar_color, width=bar_width)
            # discontinued bar case
            else:
                angleE = angle_start + pct * ecart
                angle_complet = ecart / angle_steps
                etapes = int((angleE - angle_start) / angle_complet)
                for i in range(etapes):
                    draw.arc([0, 0, diameter - 1, diameter - 1],
                             angle_start + i * angle_complet,
                             angle_start + (i + 1) * angle_complet - angle_sep,
                             fill=bar_color,
                             width=bar_width)

                draw.arc([0, 0, diameter - 1, diameter - 1],
                         angle_start + etapes * angle_complet,
                         angleE,
                         fill=bar_color,
                         width=bar_width)
        else:
            if angle_end < angle_start:
                ecart = angle_start - angle_end
            else:
                ecart = 360 - angle_end + angle_start
            # solid bar case
            if angle_sep == 0:
                if angle_end < angle_start:
                    angleE = angle_start
                    angleS = angle_start - pct * ecart
                else:
                    angleS = angle_start - pct * ecart
                    angleE = angle_start
                draw.arc([0, 0, diameter - 1, diameter - 1], angleS, angleE,
                         fill=bar_color, width=bar_width)
            # discontinued bar case
            else:
                angleS = angle_start - pct * ecart
                angle_complet = ecart / angle_steps
                etapes = int((angle_start - angleS) / angle_complet)
                for i in range(etapes):
                    draw.arc([0, 0, diameter - 1, diameter - 1],
                             angle_start - (i + 1) * angle_complet + angle_sep,
                             angle_start - i * angle_complet,
                             fill=bar_color,
                             width=bar_width)

                draw.arc([0, 0, diameter - 1, diameter - 1],
                         angleS,
                         angle_start - etapes * angle_complet,
                         fill=bar_color,
                         width=bar_width)

        # Draw text
        if with_text:
            if text is None:
                text = f"{int(pct * 100 + .5)}%"
            font = ImageFont.truetype("./res/fonts/" + font, font_size)
            left, top, right, bottom = font.getbbox(text)
            w, h = right - left, bottom - top
            draw.text((radius - w / 2, radius - top - h / 2), text,
                      font=font, fill=font_color)

        self.DisplayPILImage(bar_image, xc - radius, yc - radius)

    # Load image from the filesystem, or get from the cache if it has already been loaded previously
    def open_image(self, bitmap_path: str) -> Image:
        if bitmap_path not in self.image_cache:
            logger.debug("Bitmap " + bitmap_path + " is now loaded in the cache")
            self.image_cache[bitmap_path] = Image.open(bitmap_path)
        return copy.copy(self.image_cache[bitmap_path])
