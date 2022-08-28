from abc import ABC, abstractmethod
from enum import IntEnum

from library import config

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
        print("Orientation '", THEME_DATA["display"]["DISPLAY_ORIENTATION"], "' unknown, using portrait")
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
    def SetOrientation(self, orientation: Orientation):
        pass

    @abstractmethod
    def DisplayBitmap(self, bitmap_path: str, x: int, y: int, width: int, height: int):
        pass

    @abstractmethod
    def DisplayText(
            self,
            text: str,
            x: int,
            y: int,
            font: str,
            font_size: int,
            font_color: tuple[int, int, int],
            background_color: tuple[int, int, int],
            background_image: str
    ):
        pass

    @abstractmethod
    def DisplayProgressBar(self, x: int, y: int, width: int, height: int, min_value: int,
                           max_value: int,
                           value: int,
                           bar_color: tuple[int, int, int],
                           bar_outline: bool,
                           background_color: tuple[int, int, int],
                           background_image: str):
        pass
