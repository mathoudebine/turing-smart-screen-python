import os
import queue
import sys
import threading
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
            lcd_com_port = self.auto_detect_com_port()
            if not lcd_com_port:
                logger.error("Cannot find COM port automatically, please set it manually in config.yaml")
                try:
                    sys.exit(0)
                except:
                    os._exit(0)
            logger.debug(f"Auto detected COM port: {lcd_com_port}")
            self.lcd_serial = serial.Serial(lcd_com_port, 115200, timeout=1, rtscts=1)
        else:
            lcd_com_port = self.com_port
            logger.debug(f"Static COM port: {lcd_com_port}")
            self.lcd_serial = serial.Serial(lcd_com_port, 115200, timeout=1, rtscts=1)

    def closeSerial(self):
        try:
            self.lcd_serial.close()
        except:
            pass

    def WriteData(self, byteBuffer: bytearray):
        try:
            self.lcd_serial.write(bytes(byteBuffer))
        except serial.serialutil.SerialTimeoutException:
            # We timed-out trying to write to our device, slow things down.
            logger.warning("(Write data) Too fast! Slow down!")

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

    @abstractmethod
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
            background_image: str = None
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

        # Draw text with specified color & font
        font = ImageFont.truetype("./res/fonts/" + font, font_size)
        d = ImageDraw.Draw(text_image)
        d.text((x, y), text, font=font, fill=font_color)

        # Crop text bitmap to keep only the text (also crop if text overflows display)
        left, top, text_width, text_height = d.textbbox((0, 0), text, font=font)
        text_image = text_image.crop(box=(
            x, y,
            min(x + text_width, self.get_width()),
            min(y + text_height, self.get_height())
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
        bar_filled_width = value / (max_value - min_value) * width
        draw = ImageDraw.Draw(bar_image)
        draw.rectangle([0, 0, bar_filled_width - 1, height - 1], fill=bar_color, outline=bar_color)

        if bar_outline:
            # Draw outline
            draw.rectangle([0, 0, width - 1, height - 1], fill=None, outline=bar_color)

        self.DisplayPILImage(bar_image, x, y)
