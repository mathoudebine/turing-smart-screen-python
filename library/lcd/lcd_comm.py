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

import os
import queue
import signal
import sys
import threading
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Tuple

import serial
from PIL import Image, ImageDraw, ImageFont

from library.log import logger
from usb.core import find as finddev
from usb.core import USBError


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

        # This is used to reset the device if the computer sleeps and freeze the display.
        self.idVendor = None
        self.idProduct = None

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
            self.lcd_serial = serial.Serial(self.com_port, 115200, timeout=5, rtscts=1, write_timeout=5)
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
        except serial.serialutil.SerialException:
            logger.warning("(WriteLine) error, reseting device.")
            self.reset_by_usb()

    def ReadData(self, readSize: int):
        try:
            response = self.lcd_serial.read(readSize)
            # logger.debug("Received: [{}]".format(str(response, 'utf-8')))
            return response
        except serial.serialutil.SerialException:
            logger.warning("(ReadData) error, reseting device.")
            self.reset_by_usb()

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

    def reset_by_usb(self):
        logger.info(f"Reseting device via USB...cleaning all {self.update_queue.qsize()} queue entries")
        with self.update_queue_mutex:
            while not self.update_queue.empty():
                try:
                    self.update_queue.get()
                except queue.Empty:
                    continue
                self.update_queue.task_done()
            logger.info(f"Reseting device via USB queue cleaned: {self.update_queue.empty()}")
            try:
                dev = finddev(idVendor=self.idVendor, idProduct=self.idProduct)
                if dev is not None:
                    dev.reset()
                os.kill(os.getpid(), signal.SIGTERM)
            except USBError or OSError:
                logger.info("Error reseting device via USB...")
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
        image = Image.open(bitmap_path)
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
            align: str = 'left'
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
            text_image = Image.open(background_image)

        # Get text bounding box
        font = ImageFont.truetype("./res/fonts/" + font, font_size)
        d = ImageDraw.Draw(text_image)
        left, top, text_width, text_height = d.textbbox((0, 0), text, font=font)

        # Draw text with specified color & font, remove left/top margins
        d.text((x - left, y - top), text, font=font, fill=font_color, align=align)

        # Crop text bitmap to keep only the text (also crop if text overflows display)
        text_image = text_image.crop(box=(
            x, y,
            min(x + text_width - left, self.get_width()),
            min(y + text_height - top, self.get_height())
        ))

        self.DisplayPILImage(text_image, x, y)

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
            bar_image = Image.open(background_image)

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
            bar_image = Image.open(background_image)

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
