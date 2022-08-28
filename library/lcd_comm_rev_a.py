import struct

import serial
from PIL import Image, ImageDraw, ImageFont
from serial.tools.list_ports import comports

from library.lcd_comm import *


class Command(IntEnum):
    RESET = 101  # Resets the display
    CLEAR = 102  # Clears the display to a white screen
    TO_BLACK = 103  # Makes the screen go black. NOT TESTED
    SCREEN_OFF = 108  # Turns the screen off
    SCREEN_ON = 109  # Turns the screen on
    SET_BRIGHTNESS = 110  # Sets the screen brightness
    SET_ORIENTATION = 121  # Sets the screen orientation
    DISPLAY_BITMAP = 197  # Displays an image on the screen


class LcdCommRevA(LcdComm):
    def __init__(self):
        self.lcd_serial = None
        if CONFIG_DATA['config']['COM_PORT'] == 'AUTO':
            lcd_com_port = self.auto_detect_com_port()
            self.lcd_serial = serial.Serial(lcd_com_port, 115200, timeout=1, rtscts=1)
            print(f"Auto detected comm port: {lcd_com_port}")
        else:
            lcd_com_port = CONFIG_DATA["config"]["COM_PORT"]
            print(f"Static comm port: {lcd_com_port}")
            self.lcd_serial = serial.Serial(lcd_com_port, 115200, timeout=1, rtscts=1)

    @staticmethod
    def auto_detect_com_port():
        com_ports = serial.tools.list_ports.comports()
        auto_com_port = None

        for com_port in com_ports:
            if com_port.serial_number == "USB35INCHIPSV2":
                auto_com_port = com_port.device

        return auto_com_port

    def SendReg(self, cmd: Command, x: int, y: int, ex: int, ey: int):
        byteBuffer = bytearray(6)
        byteBuffer[0] = (x >> 2)
        byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
        byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
        byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
        byteBuffer[4] = (ey & 255)
        byteBuffer[5] = cmd

        # Lock queue mutex then queue the request
        with config.update_queue_mutex:
            config.update_queue.put((self.WriteData, [byteBuffer]))

    def WriteData(self, byteBuffer):
        try:
            self.lcd_serial.write(bytes(byteBuffer))
        except serial.serialutil.SerialTimeoutException:
            # We timed-out trying to write to our device, slow things down.
            print("(Write data) Too fast! Slow down!")

    def SendLine(self, line):
        config.update_queue.put((self.WriteLine, [line]))

    def WriteLine(self, line):
        try:
            self.lcd_serial.write(line)
        except serial.serialutil.SerialTimeoutException:
            # We timed-out trying to write to our device, slow things down.
            print("(Write line) Too fast! Slow down!")

    def Reset(self):
        self.SendReg(Command.RESET, 0, 0, 0, 0)

    def Clear(self):
        self.SendReg(Command.CLEAR, 0, 0, 0, 0)

    def ScreenOff(self):
        self.SendReg(Command.SCREEN_OFF, 0, 0, 0, 0)

    def ScreenOn(self):
        self.SendReg(Command.SCREEN_ON, 0, 0, 0, 0)

    def SetBrightness(self, level: int = CONFIG_DATA["display"]["BRIGHTNESS"]):
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        # Display scales from 0 to 255, with 0 being the brightest and 255 being the darkest.
        # Convert our brightness % to an absolute value.
        level_absolute = int(255 - ((level / 100) * 255))

        # Level : 0 (brightest) - 255 (darkest)
        self.SendReg(Command.SET_BRIGHTNESS, level_absolute, 0, 0, 0)

    def SetOrientation(self, orientation: Orientation = get_theme_orientation()):
        width = get_width()
        height = get_height()
        x = 0
        y = 0
        ex = 0
        ey = 0
        byteBuffer = bytearray(11)
        byteBuffer[0] = (x >> 2)
        byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
        byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
        byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
        byteBuffer[4] = (ey & 255)
        byteBuffer[5] = Command.SET_ORIENTATION
        byteBuffer[6] = (orientation + 100)
        byteBuffer[7] = (width >> 8)
        byteBuffer[8] = (width & 255)
        byteBuffer[9] = (height >> 8)
        byteBuffer[10] = (height & 255)
        self.lcd_serial.write(bytes(byteBuffer))

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
        if image.size[1] > get_height():
            image_height = get_height()
        if image.size[0] > get_width():
            image_width = get_width()

        assert x <= get_width(), 'Image X coordinate must be <= display width'
        assert y <= get_height(), 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image width must be > 0'
        assert image_width > 0, 'Image height must be > 0'

        self.SendReg(Command.DISPLAY_BITMAP, x, y, x + image_width - 1, y + image_height - 1)

        pix = image.load()
        line = bytes()

        # Lock queue mutex then queue all the requests for the image data
        with config.update_queue_mutex:
            for h in range(image_height):
                for w in range(image_width):
                    R = pix[w, h][0] >> 3
                    G = pix[w, h][1] >> 2
                    B = pix[w, h][2] >> 3

                    rgb = (R << 11) | (G << 5) | B
                    line += struct.pack('H', rgb)

                    # Send image data by multiple of DISPLAY_WIDTH bytes
                    if len(line) >= get_width() * 8:
                        self.SendLine(line)
                        line = bytes()

            # Write last line if needed
            if len(line) > 0:
                self.SendLine(line)

    def DisplayBitmap(self, bitmap_path: str, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        image = Image.open(bitmap_path)
        self.DisplayPILImage(image, x, y, width, height)

    def DisplayText(
            self,
            text: str,
            x=0,
            y=0,
            font="roboto/Roboto-Regular.ttf",
            font_size=20,
            font_color=(0, 0, 0),
            background_color=(255, 255, 255),
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

    def DisplayProgressBar(self, x: int, y: int, width: int, height: int, min_value=0, max_value=100,
                           value=50,
                           bar_color=(0, 0, 0),
                           bar_outline=True,
                           background_color=(255, 255, 255),
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


lcd_rev_a = LcdCommRevA()
