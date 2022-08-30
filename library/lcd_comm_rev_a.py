import struct
import time

from serial.tools.list_ports import comports

from library.lcd_comm import *
from library.log import logger


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
        self.openSerial()

    def __del__(self):
        try:
            self.lcd_serial.close()
        except:
            pass

    @staticmethod
    def auto_detect_com_port():
        com_ports = serial.tools.list_ports.comports()
        auto_com_port = None

        for com_port in com_ports:
            if com_port.serial_number == "USB35INCHIPSV2":
                auto_com_port = com_port.device

        return auto_com_port

    def SendCommand(self, cmd: Command, x: int, y: int, ex: int, ey: int, bypass_queue: bool = False):
        byteBuffer = bytearray(6)
        byteBuffer[0] = (x >> 2)
        byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
        byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
        byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
        byteBuffer[4] = (ey & 255)
        byteBuffer[5] = cmd

        if bypass_queue:
            self.WriteData(byteBuffer)
        else:
            # Lock queue mutex then queue the request
            with config.update_queue_mutex:
                config.update_queue.put((self.WriteData, [byteBuffer]))

    def WriteData(self, byteBuffer: bytearray):
        try:
            self.lcd_serial.write(bytes(byteBuffer))
        except serial.serialutil.SerialTimeoutException:
            # We timed-out trying to write to our device, slow things down.
            logger.warning("(Write data) Too fast! Slow down!")

    def SendLine(self, line: bytes):
        config.update_queue.put((self.WriteLine, [line]))

    def WriteLine(self, line: bytes):
        try:
            self.lcd_serial.write(line)
        except serial.serialutil.SerialTimeoutException:
            # We timed-out trying to write to our device, slow things down.
            logger.warning("(Write line) Too fast! Slow down!")

    def InitializeComm(self):
        # HW revision A does not need init commands
        pass

    def Reset(self):
        logger.info("Display reset...")
        # Reset command bypasses queue because it is run when queue threads are not yet started
        self.SendCommand(Command.RESET, 0, 0, 0, 0, bypass_queue=True)
        # Wait for display reset then reconnect
        time.sleep(1)
        self.openSerial()

    def Clear(self):
        self.SetOrientation(Orientation.PORTRAIT)  # Bug: orientation needs to be PORTRAIT before clearing
        self.SendCommand(Command.CLEAR, 0, 0, 0, 0)
        self.SetOrientation()  # Restore default orientation

    def ScreenOff(self):
        self.SendCommand(Command.SCREEN_OFF, 0, 0, 0, 0)

    def ScreenOn(self):
        self.SendCommand(Command.SCREEN_ON, 0, 0, 0, 0)

    def SetBrightness(self, level: int = CONFIG_DATA["display"]["BRIGHTNESS"]):
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        # Display scales from 0 to 255, with 0 being the brightest and 255 being the darkest.
        # Convert our brightness % to an absolute value.
        level_absolute = int(255 - ((level / 100) * 255))

        # Level : 0 (brightest) - 255 (darkest)
        self.SendCommand(Command.SET_BRIGHTNESS, level_absolute, 0, 0, 0)

    def SetBackplateLedColor(self, led_color: tuple[int, int, int] = THEME_DATA['display']["DISPLAY_RGB_LED"]):
        logger.info("HW revision A does not support backplate LED color setting")
        pass

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

        (x0, y0) = (x, y)
        (x1, y1) = (x + image_width - 1, y + image_height - 1)

        self.SendCommand(Command.DISPLAY_BITMAP, x0, y0, x1, y1)

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
