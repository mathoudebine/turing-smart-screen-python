from abc import ABC, abstractmethod
from enum import IntEnum

import serial
from PIL import Image, ImageDraw, ImageFont

from library import config
from library.log import logger

CONFIG_DATA = config.CONFIG_DATA
THEME_DATA = config.THEME_DATA


class Orientation(IntEnum):
    PORTRAIT = 0
    LANDSCAPE = 2
    REVERSE_PORTRAIT = 1
    REVERSE_LANDSCAPE = 3


def get_theme_orientation() -> Orientation:
    if THEME_DATA["display"]["DISPLAY_ORIENTATION"] == 'portrait':
        return Orientation.PORTRAIT
    elif THEME_DATA["display"]["DISPLAY_ORIENTATION"] == 'landscape':
        return Orientation.LANDSCAPE
    elif THEME_DATA["display"]["DISPLAY_ORIENTATION"] == 'reverse_portrait':
        return Orientation.REVERSE_PORTRAIT
    elif THEME_DATA["display"]["DISPLAY_ORIENTATION"] == 'reverse_landscape':
        return Orientation.REVERSE_LANDSCAPE
    else:
        logger.warning("Orientation '", THEME_DATA["display"]["DISPLAY_ORIENTATION"], "' unknown, using portrait")
        return Orientation.PORTRAIT


def get_width() -> int:
    if get_theme_orientation() == Orientation.PORTRAIT or get_theme_orientation() == Orientation.REVERSE_PORTRAIT:
        return CONFIG_DATA["display"]["DISPLAY_WIDTH"]
    else:
        return CONFIG_DATA["display"]["DISPLAY_HEIGHT"]


def get_height() -> int:
    if get_theme_orientation() == Orientation.PORTRAIT or get_theme_orientation() == Orientation.REVERSE_PORTRAIT:
        return CONFIG_DATA["display"]["DISPLAY_HEIGHT"]
    else:
        return CONFIG_DATA["display"]["DISPLAY_WIDTH"]


class LcdComm(ABC):
    def openSerial(self):
        if CONFIG_DATA['config']['COM_PORT'] == 'AUTO':
            lcd_com_port = self.auto_detect_com_port()
            self.lcd_serial = serial.Serial(lcd_com_port, 115200, timeout=1, rtscts=1)
            logger.debug(f"Auto detected comm port: {lcd_com_port}")
        else:
            lcd_com_port = CONFIG_DATA["config"]["COM_PORT"]
            logger.debug(f"Static comm port: {lcd_com_port}")
            self.lcd_serial = serial.Serial(lcd_com_port, 115200, timeout=1, rtscts=1)

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
    def SetBackplateLedColor(self, led_color: tuple[int, int, int]):
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
            font_color: tuple[int, int, int] = (0, 0, 0),
            background_color: tuple[int, int, int] = (255, 255, 255),
            background_image: str = None
    ):
        # Convert text to bitmap using PIL and display it
        # Provide the background image path to display text with transparent background

        if isinstance(font_color, str):
            font_color = tuple(map(int, font_color.split(', ')))

        if isinstance(background_color, str):
            background_color = tuple(map(int, background_color.split(', ')))

        assert x <= get_width(), 'Text X coordinate must be <= display width'
        assert y <= get_height(), 'Text Y coordinate must be <= display height'
        assert len(text) > 0, 'Text must not be empty'
        assert font_size > 0, "Font size must be > 0"

        if background_image is None:
            # A text bitmap is created with max width/height by default : text with solid background
            text_image = Image.new(
                'RGB',
                (get_width(), get_height()),
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
            min(x + text_width, get_width()),
            min(y + text_height, get_height())
        ))

        self.DisplayPILImage(text_image, x, y)

    def DisplayProgressBar(self, x: int, y: int, width: int, height: int, min_value: int = 0, max_value: int = 100,
                           value: int = 50,
                           bar_color: tuple[int, int, int] = (0, 0, 0),
                           bar_outline: bool = True,
                           background_color: tuple[int, int, int] = (255, 255, 255),
                           background_image: str = None):
        # Generate a progress bar and display it
        # Provide the background image path to display progress bar with transparent background

        if isinstance(bar_color, str):
            bar_color = tuple(map(int, bar_color.split(', ')))

        if isinstance(background_color, str):
            background_color = tuple(map(int, background_color.split(', ')))

        assert x <= get_width(), 'Progress bar X coordinate must be <= display width'
        assert y <= get_height(), 'Progress bar Y coordinate must be <= display height'
        assert x + width <= get_width(), 'Progress bar width exceeds display width'
        assert y + height <= get_height(), 'Progress bar height exceeds display height'

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
