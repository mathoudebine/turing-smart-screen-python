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
import platform
import queue
import sys
import threading
import time
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Tuple, List, Optional, Dict

import serial
from PIL import Image, ImageDraw, ImageFont

from library.log import logger
from library.lcd.color import Color, parse_color


class Orientation(IntEnum):
    PORTRAIT = 0
    LANDSCAPE = 2
    REVERSE_PORTRAIT = 1
    REVERSE_LANDSCAPE = 3


class LcdComm(ABC):
    def __init__(self, com_port: str = "AUTO", display_width: int = 320, display_height: int = 480,
                 update_queue: Optional[queue.Queue] = None):
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
        self.font_cache: Dict[
            Tuple[str, int],  # key=(font, size)
            ImageFont.FreeTypeFont # value= a loaded freetype font
        ] = {}

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
            self.lcd_serial = serial.Serial(self.com_port, 115200, timeout=1, rtscts=True)
        except Exception as e:
            logger.error(f"Cannot open COM port {self.com_port}: {e}")
            try:
                sys.exit(0)
            except:
                os._exit(0)

    def closeSerial(self):
        if self.lcd_serial is not None:
            self.lcd_serial.close()

    def serial_write(self, data: bytes):
        assert self.lcd_serial is not None
        self.lcd_serial.write(data)

    def serial_read(self, size: int) -> bytes:
        assert self.lcd_serial is not None
        return self.lcd_serial.read(size)

    def serial_flush_input(self):
        if self.lcd_serial is not None:
            self.lcd_serial.reset_input_buffer()

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
            self.serial_write(line)
            if platform.system() == "Darwin":
                # macOS needs the serial buffer to be flushed regularly to avoid bitmap corruption on the display
                # See https://github.com/mathoudebine/turing-smart-screen-python/issues/7
                self.lcd_serial.flush()
        except serial.SerialTimeoutException:
            # We timed-out trying to write to our device, slow things down.
            logger.warning("(Write line) Too fast! Slow down!")
        except serial.SerialException:
            # Error writing data to device: close and reopen serial port, try to write again
            logger.error(
                "SerialException: Failed to send serial data to device. Closing and reopening COM port before retrying once.")
            self.closeSerial()
            time.sleep(1)
            self.openSerial()
            self.serial_write(line)

    def ReadData(self, readSize: int):
        try:
            response = self.serial_read(readSize)
            # logger.debug("Received: [{}]".format(str(response, 'utf-8')))
            return response
        except serial.SerialTimeoutException:
            # We timed-out trying to read from our device, slow things down.
            logger.warning("(Read data) Too fast! Slow down!")
        except serial.SerialException:
            # Error writing data to device: close and reopen serial port, try to read again
            logger.error(
                "SerialException: Failed to read serial data from device. Closing and reopening COM port before retrying once.")
            self.closeSerial()
            time.sleep(1)
            self.openSerial()
            return self.serial_read(readSize)

    @staticmethod
    @abstractmethod
    def auto_detect_com_port() -> Optional[str]:
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
            image: Image.Image,
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
            width: int = 0,
            height: int = 0,
            font: str = "./res/fonts/roboto-mono/RobotoMono-Regular.ttf",
            font_size: int = 20,
            font_color: Color = (0, 0, 0),
            background_color: Color = (255, 255, 255),
            background_image: Optional[str] = None,
            align: str = 'left',
            anchor: str = 'la',
    ):
        # Convert text to bitmap using PIL and display it
        # Provide the background image path to display text with transparent background

        font_color = parse_color(font_color)
        background_color = parse_color(background_color)

        assert x <= self.get_width(), 'Text X coordinate ' + str(x) + ' must be <= display width ' + str(
            self.get_width())
        assert y <= self.get_height(), 'Text Y coordinate ' + str(y) + ' must be <= display height ' + str(
            self.get_height())
        assert len(text) > 0, 'Text must not be empty'
        assert font_size > 0, "Font size must be > 0"

        # If only width is specified, assume height based on font size (one-line text)
        if width > 0 and height == 0:
            height = font_size

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
        ttfont = self.open_font(font, font_size)
        d = ImageDraw.Draw(text_image)

        if width == 0 or height == 0:
            left, top, right, bottom = d.textbbox((x, y), text, font=ttfont, align=align, anchor=anchor)

            # textbbox may return float values, which is not good for the bitmap operations below.
            # Let's extend the bounding box to the next whole pixel in all directions
            left, top = math.floor(left), math.floor(top)
            right, bottom = math.ceil(right), math.ceil(bottom)
        else:
            left, top, right, bottom = x, y, x + width, y + height

            if anchor.startswith("m"):
                x = int((right + left) / 2)
            elif anchor.startswith("r"):
                x = right
            else:
                x = left

            if anchor.endswith("m"):
                y = int((bottom + top) / 2)
            elif anchor.endswith("b"):
                y = bottom
            else:
                y = top

        # Draw text onto the background image with specified color & font
        d.text((x, y), text, font=ttfont, fill=font_color, align=align, anchor=anchor)

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
                           bar_color: Color = (0, 0, 0),
                           bar_outline: bool = True,
                           background_color: Color = (255, 255, 255),
                           background_image: Optional[str] = None):
        # Generate a progress bar and display it
        # Provide the background image path to display progress bar with transparent background

        bar_color = parse_color(bar_color)
        background_color = parse_color(background_color)

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

    def DisplayLineGraph(self, x: int, y: int, width: int, height: int,
                         values: List[float],
                         min_value: float = 0,
                         max_value: float = 100,
                         autoscale: bool = False,
                         line_color: Color = (0, 0, 0),
                         line_width: int = 2,
                         graph_axis: bool = True,
                         axis_color: Color = (0, 0, 0),
                         axis_font: str = "./res/fonts/roboto/Roboto-Black.ttf",
                         axis_font_size: int = 10,
                         background_color: Color = (255, 255, 255),
                         background_image: Optional[str] = None):
        # Generate a plot graph and display it
        # Provide the background image path to display plot graph with transparent background

        line_color = parse_color(line_color)
        axis_color = parse_color(axis_color)
        background_color = parse_color(background_color)

        assert x <= self.get_width(), 'Progress bar X coordinate must be <= display width'
        assert y <= self.get_height(), 'Progress bar Y coordinate must be <= display height'
        assert x + width <= self.get_width(), 'Progress bar width exceeds display width'
        assert y + height <= self.get_height(), 'Progress bar height exceeds display height'

        if background_image is None:
            # A bitmap is created with solid background
            graph_image = Image.new('RGB', (width, height), background_color)
        else:
            # A bitmap is created from provided background image
            graph_image = self.open_image(background_image)

            # Crop bitmap to keep only the plot graph background
            graph_image = graph_image.crop(box=(x, y, x + width, y + height))

        # if autoscale is enabled, define new min/max value to "zoom" the graph
        if autoscale:
            trueMin = max_value
            trueMax = min_value
            for value in values:
                if not math.isnan(value):
                    if trueMin > value:
                        trueMin = value
                    if trueMax < value:
                        trueMax = value

            if trueMin != max_value and trueMax != min_value:
                min_value = max(trueMin - 5, min_value)
                max_value = min(trueMax + 5, max_value)

        step = width / len(values)
        # pre compute yScale multiplier value
        yScale = height / (max_value - min_value)

        plotsX = []
        plotsY = []
        count = 0
        for value in values:
            if not math.isnan(value):
                # Don't let the set value exceed our min or max value, this is bad :)                
                if value < min_value:
                    value = min_value
                elif max_value < value:
                    value = max_value

                assert min_value <= value <= max_value, 'Plot point value shall be between min and max'

                plotsX.append(count * step)
                plotsY.append(height - (value - min_value) * yScale)

                count += 1

        # Draw plot graph
        draw = ImageDraw.Draw(graph_image)
        draw.line(list(zip(plotsX, plotsY)), fill=line_color, width=line_width)

        if graph_axis:
            # Draw axis
            draw.line([0, height - 1, width - 1, height - 1], fill=axis_color)
            draw.line([0, 0, 0, height - 1], fill=axis_color)

            # Draw Legend
            draw.line([0, 0, 1, 0], fill=axis_color)
            text = f"{int(max_value)}"
            ttfont = self.open_font(axis_font, axis_font_size)
            _, top, right, bottom = ttfont.getbbox(text)
            draw.text((2, 0 - top), text,
                      font=ttfont, fill=axis_color)

            text = f"{int(min_value)}"
            _, top, right, bottom = ttfont.getbbox(text)
            draw.text((width - 1 - right, height - 2 - bottom), text,
                      font=ttfont, fill=axis_color)

        self.DisplayPILImage(graph_image, x, y)

    def DrawRadialDecoration(self, draw: ImageDraw.ImageDraw, angle: float, radius: float, width: float, color: Tuple[int, int, int] = (0, 0, 0)):
        i_cos = math.cos(angle*math.pi/180)
        i_sin = math.sin(angle*math.pi/180)
        x_f = (i_cos * (radius - width/2)) + radius
        if math.modf(x_f) == 0.5:
            if i_cos > 0:
                x_f = math.floor(x_f)
            else:
                x_f = math.ceil(x_f)
        else:
             x_f = math.floor(x_f + 0.5) 
            
        y_f = (i_sin * (radius - width/2)) + radius 
        if math.modf(y_f) == 0.5:
            if i_sin > 0:
                y_f = math.floor(y_f)
            else:
                y_f = math.ceil(y_f)
        else:
            y_f = math.floor(y_f + 0.5)            
        draw.ellipse([x_f - width/2, y_f - width/2, x_f + width/2, y_f - 1 + width/2 - 1], outline=color, fill=color, width=1)   
      

    def DisplayRadialProgressBar(self, xc: int, yc: int, radius: int, bar_width: int,
                                 min_value: int = 0,
                                 max_value: int = 100,
                                 angle_start: float = 0,
                                 angle_end: float = 360,
                                 angle_sep: int = 5,
                                 angle_steps: int = 10,
                                 clockwise: bool = True,
                                 value: int = 50,
                                 text: Optional[str] = None,
                                 with_text: bool = True,
                                 font: str = "./res/fonts/roboto/Roboto-Black.ttf",
                                 font_size: int = 20,
                                 font_color: Color = (0, 0, 0),
                                 bar_color: Color = (0, 0, 0),
                                 background_color: Color = (255, 255, 255),
                                 background_image: Optional[str] = None,
                                 custom_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0),
                                 text_offset: Tuple[int, int] = (0,0),
                                 bar_background_color: Color = (0, 0, 0),
                                 draw_bar_background: bool = False,
                                 bar_decoration: str = ""):                                 
        # Generate a radial progress bar and display it
        # Provide the background image path to display progress bar with transparent background

        bar_color = parse_color(bar_color)
        background_color = parse_color(background_color)
        font_color = parse_color(font_color)
        bar_background_color = parse_color(bar_background_color)

        if angle_start % 361 == angle_end % 361:
            if clockwise:
                angle_start += 0.1
            else:
                angle_end += 0.1

        assert xc - radius >= 0 and xc + radius <= self.get_width(), 'Radial is out of screen (left/right)'
        assert yc - radius >= 0 and yc + radius <= self.get_height(), 'Radial is out of screen (up/down)'
        assert 0 < bar_width <= radius, f'Radial linewidth is {bar_width}, must be > 0 and <= radius'
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

        assert min_value <= value <= max_value, 'Radial value shall be between min and max'

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

            # draw bar background
            if draw_bar_background:
                if angle_end < angle_start:
                    angleE = angle_start + ecart
                    angleS = angle_start
                else:
                    angleS = angle_start
                    angleE = angle_start + ecart
                draw.arc([0, 0, diameter - 1, diameter - 1], angleS, angleE, fill=bar_background_color, width=bar_width) 
                
            # draw bar decoration
            if bar_decoration == "Ellipse":
                self.DrawRadialDecoration(draw = draw, angle = angle_end, radius = radius, width = bar_width, color = bar_background_color)
                self.DrawRadialDecoration(draw = draw, angle = angle_start, radius = radius, width = bar_width, color = bar_color)
                self.DrawRadialDecoration(draw = draw, angle = angle_start + pct * ecart, radius = radius, width = bar_width, color = bar_color)

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

            # draw bar background
            if draw_bar_background:
                if angle_end < angle_start:
                    angleE = angle_start
                    angleS = angle_start - ecart
                else:
                    angleS = angle_start - ecart
                    angleE = angle_start
                draw.arc([0, 0, diameter - 1, diameter - 1], angleS, angleE, fill=bar_background_color, width=bar_width) 


            # draw bar decoration
            if bar_decoration == "Ellipse":
                self.DrawRadialDecoration(draw = draw, angle = angle_end, radius = radius, width = bar_width, color = bar_background_color)
                self.DrawRadialDecoration(draw = draw, angle = angle_start, radius = radius, width = bar_width, color = bar_color)
                self.DrawRadialDecoration(draw = draw, angle = angle_start - pct * ecart, radius = radius, width = bar_width, color = bar_color)

            #      
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
            ttfont = self.open_font(font, font_size)
            left, top, right, bottom = ttfont.getbbox(text)
            w, h = right - left, bottom - top
            draw.text((radius - w / 2 + text_offset[0], radius - top - h / 2 + text_offset[1]), text,
                      font=ttfont, fill=font_color)

        if custom_bbox[0] != 0 or custom_bbox[1] != 0 or custom_bbox[2] != 0 or custom_bbox[3] != 0:
            bar_image = bar_image.crop(box=custom_bbox)

        self.DisplayPILImage(bar_image, xc - radius + custom_bbox[0], yc - radius + custom_bbox[1])
       # self.DisplayPILImage(bar_image, xc - radius, yc - radius)

    # Load image from the filesystem, or get from the cache if it has already been loaded previously
    def open_image(self, bitmap_path: str) -> Image.Image:
        if bitmap_path not in self.image_cache:
            logger.debug("Bitmap " + bitmap_path + " is now loaded in the cache")
            self.image_cache[bitmap_path] = Image.open(bitmap_path)
        return copy.copy(self.image_cache[bitmap_path])

    def open_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        if (name, size) not in self.font_cache:
            self.font_cache[(name, size)] = ImageFont.truetype(name, size)
        return self.font_cache[(name, size)]
