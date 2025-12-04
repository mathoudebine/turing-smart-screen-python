# Copyright (C) 2024-2024  WeAct Studio
# Imported from https://github.com/WeActStudio/WeActStudio.SystemMonitor

import struct

from serial.tools.list_ports import comports

from library.lcd.lcd_comm import *
from library.log import logger
from library.lcd import serialize
#import fastlz

class Command(IntEnum):
    CMD_WHO_AM_I = 0x81  # Establish communication before driving the screen
    CMD_SET_ORIENTATION = 0x02  # Sets the screen orientation
    CMD_SET_BRIGHTNESS = 0x03  # Sets the screen brightness
    CMD_FULL = 0x04  # Displays an image on the screen
    CMD_SET_BITMAP = 0x05  # Displays an image on the screen
    CMD_SET_BITMAP_WITH_FASTLZ = 0x15
    CMD_FREE = 0x07
    CMD_SYSTEM_VERSION = 0x42
    CMD_END = 0x0A  # Displays an image on the screen
    CMD_READ = 0x80


# This class is for WeAct Studio Display FS V1 0.96"
class LcdCommWeActB(LcdComm):
    def __init__(
        self,
        com_port: str = "AUTO",
        display_width: int = 80,
        display_height: int = 160,
        update_queue: queue.Queue = None,
    ):
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.brightness = 0
        self.support_fastlz = False
        self.openSerial()


    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port():
        com_ports = comports()

        for com_port in com_ports:
            if com_port.vid == 0x1a86 and com_port.pid == 0xfe0c:
                return com_port.device
            if isinstance(com_port.serial_number, str):
                if com_port.serial_number.startswith("AD"):
                    return com_port.device

        return None

    def Send_Bitmap_xy_Command(self, xs, ys, xe, ye, bypass_queue: bool = False):
        byteBuffer = bytearray(10)
        byteBuffer[0] = Command.CMD_SET_BITMAP
        byteBuffer[1] = xs & 0xFF
        byteBuffer[2] = xs >> 8 & 0xFF
        byteBuffer[3] = ys & 0xFF
        byteBuffer[4] = ys >> 8 & 0xFF
        byteBuffer[5] = xe & 0xFF
        byteBuffer[6] = xe >> 8 & 0xFF
        byteBuffer[7] = ye & 0xFF
        byteBuffer[8] = ye >> 8 & 0xFF
        byteBuffer[9] = Command.CMD_END

        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(byteBuffer)
        else:
            # Lock queue mutex then queue the request
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [byteBuffer]))

    def SendCommand(self, byteBuffer, bypass_queue: bool = False):
        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(byteBuffer)
        else:
            # Lock queue mutex then queue the request
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [byteBuffer]))

    def InitializeComm(self,use_compress:int = 0):
        byteBuffer = bytearray(2)
        self.serial_readall()
        byteBuffer[0] = Command.CMD_SYSTEM_VERSION | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END
        self.WriteData(byteBuffer)
        response = self.serial_read(19)
        self.serial_flush_input()
        if response and len(response) == 19:
            version_str = response[1:9].decode('ascii').strip()
            logger.info(f"Device version: {version_str}")
            # logger.info("Device supports fastlz compression.")
            # if use_compress:
            #     self.support_fastlz = True
            # else:
            #     self.support_fastlz = False
            #     logger.info("User disabled fastlz compression.")
        else:
            # self.support_fastlz = False
            logger.info("Get version failed") 
        pass

    def Reset(self):
        pass

    def Clear(self):
        self.Full((0,0,0))
    
    def Full(self,color: Tuple[int, int, int] = (0, 0, 0)):
        R = color[0] >> 3
        G = color[1] >> 2
        B = color[2] >> 3
        # Color information is 0bRRRRRGGGGGGBBBBB
        # Encode in Little-Endian
        rgb = (R << 11) | (G << 5) | B
        line = struct.pack("<H", rgb)

        xe = self.get_width()
        ye = self.get_height()
        
        byteBuffer = bytearray(12)
        byteBuffer[0] = Command.CMD_FULL
        byteBuffer[1] = 0
        byteBuffer[2] = 0
        byteBuffer[3] = 0
        byteBuffer[4] = 0
        byteBuffer[5] = (xe-1) & 0xff
        byteBuffer[6] = (xe >> 8) & 0xff
        byteBuffer[7] = (ye-1) & 0xff
        byteBuffer[8] = (ye >> 8) & 0xff
        byteBuffer[9] = line[0]
        byteBuffer[10] = line[1]
        byteBuffer[11] = Command.CMD_END
        self.SendCommand(byteBuffer)

    def ScreenOff(self):
        self.SetBrightness(0)
        # self.SetSensorReportTime(0)
        self.Free()

    def ScreenOn(self):
        self.SetBrightness(self.brightness)

    def SetBrightness(self, level: int = 0):
        assert 0 <= level <= 100, "Brightness level must be [0-100]"
        converted_level = int((level / 100) * 255)
        brightness_ms = 1000
        byteBuffer = bytearray(5)
        byteBuffer[0] = Command.CMD_SET_BRIGHTNESS
        byteBuffer[1] = converted_level & 0xFF
        byteBuffer[2] = brightness_ms & 0xFF
        byteBuffer[3] = brightness_ms >> 8 & 0xFF
        byteBuffer[4] = Command.CMD_END
        self.SendCommand(byteBuffer)
        self.brightness = level

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        self.orientation = orientation
        byteBuffer = bytearray(3)
        byteBuffer[0] = Command.CMD_SET_ORIENTATION
        byteBuffer[1] = self.orientation
        byteBuffer[2] = Command.CMD_END
        self.SendCommand(byteBuffer)

    def Free(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_FREE
        byteBuffer[1] = Command.CMD_END
        self.SendCommand(byteBuffer)

    def DisplayPILImage(
        self,
        image: Image.Image,
        x: int = 0,
        y: int = 0,
        image_width: int = 0,
        image_height: int = 0,
    ):
        # print(f'image.size: {image.size} x: {x} y: {y}')

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

        assert x >= 0, f"Display Image X {x} coordinate must be >= 0"
        assert y >= 0, f"Display Image Y {y} coordinate must be >= 0"
        assert x <= self.get_width(), f"Display Image X {x} coordinate must be <= display width {self.get_width()}"
        assert y <= self.get_height(), f"Display Image Y {y} coordinate must be <= display height {self.get_height()}"
        assert image_height > 0, "Image height must be > 0"
        assert image_width > 0, "Image width must be > 0"
        assert x + image_width <= self.get_width(), f'Display Bitmap width+x exceeds display width {self.get_width()}'
        assert y + image_height <= self.get_height(), f'Display Bitmap height+y exceeds display height {self.get_height()}'

        (x0, y0) = (x, y)
        (x1, y1) = (x + image_width - 1, y + image_height - 1)

        byteBuffer = bytearray(10)
        byteBuffer[0] = Command.CMD_SET_BITMAP
        byteBuffer[1] = x0 & 0xFF
        byteBuffer[2] = x0 >> 8 & 0xFF
        byteBuffer[3] = y0 & 0xFF
        byteBuffer[4] = y0 >> 8 & 0xFF
        byteBuffer[5] = x1 & 0xFF
        byteBuffer[6] = x1 >> 8 & 0xFF
        byteBuffer[7] = y1 & 0xFF
        byteBuffer[8] = y1 >> 8 & 0xFF
        byteBuffer[9] = Command.CMD_END

        line_to_send_size = self.get_width() * 4

        rgb565le = serialize.image_to_RGB565(image,'little')

        # if self.support_fastlz:
        #     chunk_size = line_to_send_size
        #     # Lock queue mutex then queue all the requests for the image data
        #     with self.update_queue_mutex:
        #         byteBuffer[0] = Command.CMD_SET_BITMAP_WITH_FASTLZ
        #         self.SendLine(byteBuffer)
        #         # declare the chunk size
        #         for i in range(0, len(rgb565le), chunk_size):
        #             chunk = rgb565le[i:i+chunk_size]
        #             compressed_chunk = fastlz.compress(chunk)
        #             chunk_with_header = struct.pack("<HH", len(chunk), len(compressed_chunk[4:])) + compressed_chunk[4:]
        #             self.SendLine(chunk_with_header)
        # else:
        # Lock queue mutex then queue all the requests for the image data
        with self.update_queue_mutex:
            self.SendLine(byteBuffer)
            for chunk in serialize.chunked(rgb565le,line_to_send_size):
                self.SendLine(chunk)
                