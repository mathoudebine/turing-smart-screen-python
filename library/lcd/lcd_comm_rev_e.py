# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2023-2023  Alex W. Baulé (alexwbaule)
# Copyright (C) 2023-2023  Arthur Ferrai (arthurferrai)
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

import queue
import time
from enum import Enum
from math import ceil

import serial
from PIL import Image
from serial.tools.list_ports import comports

from library.lcd.lcd_comm import Orientation, LcdComm
from library.log import logger


class Count:
    Start = 0

class Command(Enum):
    # COMMANDS
    HELLO = bytearray((0x01, 0xef, 0x69, 0x00, 0x00, 0x00,
                      0x01, 0x00, 0x00, 0x00, 0xc5, 0xd3))

    RESTART = bytearray((0x84, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    TURNOFF = bytearray((0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    TURNON = bytearray((0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x00))

    SET_BRIGHTNESS = bytearray(
        (0x7b, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00))

    # STOP COMMANDS
    STOP_VIDEO = bytearray((0x79, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    STOP_MEDIA = bytearray((0x96, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))

    # IMAGE QUERY STATUS
    QUERY_STATUS = bytearray((0xcf, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))

    # STATIC IMAGE
    START_DISPLAY_BITMAP = bytearray((0x2c,))
    PRE_UPDATE_BITMAP = bytearray((0x86, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    UPDATE_BITMAP = bytearray((0xcc, 0xef, 0x69,))
    UPDATE_BITMAP_NO_CHANGES = bytearray(
        (0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0xEF, 0x69,))
    STOP_UPDATE_BITMAP = bytearray((0x87, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))

    RESTARTSCREEN = bytearray((0x84, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    DISPLAY_BITMAP = bytearray((0xc8, 0xef, 0x69))

    OPTIONS = bytearray((0x7d, 0xef, 0x69, 0x00, 0x00,
                        0x00, 0x05, 0x00, 0x00, 0x00, 0xff))
    STARTMODE_DEFAULT = bytearray((0x00,))
    STARTMODE_IMAGE = bytearray((0x01,))
    STARTMODE_VIDEO = bytearray((0x02,))
    FLIP_180 = bytearray((0x01,))
    NO_FLIP = bytearray((0x00,))

    UPLOAD_FILE = bytearray((0x6F, 0xef, 0x69,))  # 6FEF6900000017000000
    DELETE_FILE = bytearray((0x66, 0xef, 0x69,))
    LIST_FILES = bytearray((0x65, 0xEF, 0x69,))
    QUERY_FILE_SIZE = bytearray((0x6e, 0xef, 0x69,))
    QUERY_STORAGE_INFORMATION = bytearray((0x64, 0xef, 0x69,
                                           0x00, 0x00, 0x00, 0x01,))  # 64EF6900000001

    PLAY_IMAGE = bytearray((0x8C, 0xEF, 0x69,))
    PLAY_VIDEO = bytearray((0x78, 0xEF, 0x69,))

    SEND_PAYLOAD = bytearray((0xFF,))

    def __init__(self, command):
        self.command = command


class Padding(Enum):
    NULL = bytearray([0x00])
    START_DISPLAY_BITMAP = bytearray([0x2c])

    def __init__(self, command):
        self.command = command


class SleepInterval(Enum):
    OFF = bytearray((0x00,))
    ONE = bytearray((0x01,))
    TWO = bytearray((0x02,))
    THREE = bytearray((0x03,))
    FOUR = bytearray((0x04,))
    FIVE = bytearray((0x05,))
    SIX = bytearray((0x06,))
    SEVEN = bytearray((0x07,))
    EIGHT = bytearray((0x08,))
    NINE = bytearray((0x09,))
    TEN = bytearray((0x0a,))

    def __init__(self, command):
        self.command = command


class SubRevision(Enum):
    UNKNOWN = None
    EIGHTINCH = "chs_88inch"

    def __init__(self, command):
        self.command = command


# This class is for Turing Smart Screen 5" screens
class LcdCommRevE(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 1920, display_height: int = 480,
                 update_queue: queue.Queue = None):
        logger.debug("HW revision: E")
        LcdComm.__init__(self, com_port, display_width,
                         display_height, update_queue)
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port():
        com_ports = comports()

        # Try to find awake device through serial number or vid/pid
        for com_port in com_ports:
            if com_port.serial_number == 'CT88INCH':
                return com_port.device
            if com_port.vid == 0x0525 and com_port.pid == 0xa4a7:
                return com_port.device

        # Try to find sleeping device and wake it up
        for com_port in com_ports:
            if com_port.serial_number == 'CT88INCH':
                LcdCommRevE._connect_to_reset_device_name(com_port)
                return LcdCommRevE.auto_detect_com_port()

        return None

    @staticmethod
    def _connect_to_reset_device_name(com_port):
        # this device enumerates differently when off, we need to connect once to reset it to correct COM device
        try:
            logger.debug(f"Waiting for device {com_port} to be turned ON...")
            serial.Serial(com_port.device, 115200, timeout=1, rtscts=1)
        except serial.serialutil.SerialException:
            pass
        time.sleep(10)

    def _send_command(self, cmd: Command, payload: bytearray = None, padding: Padding = None,
                      bypass_queue: bool = False, readsize: int = None) -> bytes | None:
        message = bytearray()

        if cmd != Command.SEND_PAYLOAD:
            message = bytearray(cmd.value)

        # logger.debug("Command: {}".format(cmd.name))

        if not padding:
            padding = Padding.NULL

        if payload:
            message.extend(payload)

        msg_size = len(message)

        if not (msg_size / 250).is_integer():
            pad_size = (250 * ceil(msg_size / 250) - msg_size)
            message += bytearray(padding.value * pad_size)

        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(message)
            if readsize:
                return self.ReadData(readsize)
        else:
            # Lock queue mutex then queue the request
            self.update_queue.put((self.WriteData, [message]))
            if readsize:
                self.update_queue.put((self.ReadData, [readsize]))

    def _hello(self):
        # This command reads LCD answer on serial link, so it bypasses the queue
        self.sub_revision = SubRevision.UNKNOWN
        self._send_command(Command.HELLO, bypass_queue=True)
        response = str(self.lcd_serial.read(23).decode())
        self.lcd_serial.flushInput()
        if response.startswith(SubRevision.EIGHTINCH.value):
            self.sub_revision = SubRevision.EIGHTINCH
        else:
            logger.warning(
                "Display returned unknown sub-revision on Hello answer (%s)" % str(response))

    def InitializeComm(self):
        pass

    def Reset(self):
        logger.info("Display reset (COM port may change)...")
        
        self._init_packet_interaction()
        self._send_command(Command.RESTART, bypass_queue=True)
        self._send_command(Command.RESTART, bypass_queue=True)
        self.closeSerial()
        # Wait for display reset then reconnect
        time.sleep(15)
        self.openSerial()

    def Clear(self):
        # This hardware does not implement a Clear command: display a blank image on the whole screen
        # Force an orientation in case the screen is currently configured with one different from the theme
        backup_orientation = self.orientation
        self.SetOrientation(orientation=Orientation.PORTRAIT)

        blank = Image.new(
            "RGB", (self.get_width(), self.get_height()), (255, 255, 255))
        self.DisplayPILImage(blank)

        # Restore orientation
        self.SetOrientation(orientation=backup_orientation)

    def ScreenOff(self):
        logger.info("Calling ScreenOff")
        self._send_command(Command.HELLO, bypass_queue=True)
        self._send_command(Command.STOP_VIDEO)
        response = self._send_command(Command.STOP_MEDIA, readsize=1024)

        assert response == b'media_stop', 'Failed to stop media'

        self._send_command(Command.TURNOFF)

    def ScreenOn(self, is_isolated_call: bool = True):
        logger.info("Calling ScreenOn")

        if is_isolated_call:
            self._init_packet_interaction()

        self._send_command(Command.STOP_VIDEO)
        self._send_command(Command.STOP_MEDIA, readsize=1024)
        # self._send_command(Command.SET_BRIGHTNESS, payload=bytearray([255]))

    def SetBrightness(self, level: int = 25, is_isolated_call: bool = True):
        # logger.info("Call SetBrightness")
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        # Brightness scales from 0 to 255, with 255 being the brightest and 0 being the darkest.
        # Convert our brightness % to an absolute value.
        converted_level = int((level / 100) * 255)

        if is_isolated_call:
            self._init_packet_interaction()

        self._send_command(Command.SET_BRIGHTNESS, payload=bytearray(
            (converted_level,)), bypass_queue=True)

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT, is_isolated_call: bool = True):
        self.orientation = orientation
        # logger.info(f"Call SetOrientation to: {self.orientation.name}")

        if is_isolated_call:
            self._init_packet_interaction()

        if self.orientation == Orientation.REVERSE_LANDSCAPE or self.orientation == Orientation.REVERSE_PORTRAIT:
            b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + \
                Command.FLIP_180.value + SleepInterval.OFF.value
            self._send_command(Command.OPTIONS, payload=b)
        else:
            b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + \
                Command.NO_FLIP.value + SleepInterval.OFF.value
            self._send_command(Command.OPTIONS, payload=b)

    def ListDirectory(self, path: str) -> tuple[list[str], list[str]]:
        self._init_packet_interaction()

        payload = len(path).to_bytes(4, byteorder='big') + \
            Padding.NULL.value * 3 + bytearray(path, 'utf-8')

        response = self._send_command(
            Command.LIST_FILES,
            payload=payload,
            readsize=10240,
            bypass_queue=True)

        responseList = response.decode().rstrip('\x00')
        print(responseList)

        assert responseList.startswith("result"), 'Failed to list files'

        if responseList.startswith('result:'):
            parts = responseList.split(':')
            return parts[2].split('/')[:-1], parts[3].split('/')[:-1]

        return [], []

    def UploadFile(self, src_path: str, target_path: str):        
        payload = len(target_path).to_bytes(4, byteorder='big') + \
            Padding.NULL.value * 3 + bytearray(target_path, 'utf-8')
            
        response = self._send_command(
            Command.UPLOAD_FILE, 
            payload=payload,
            readsize=1024, 
            bypass_queue=True)

        assert response.startswith(b'create_success'), 'Failed to create file'

        with open(src_path, 'rb') as file:
            byte = file.read(1024)
            sent = 0
            while byte != b"":
                if len(byte) == 1024:
                    self._send_command(Command.SEND_PAYLOAD,
                                       payload=byte, bypass_queue=True)
                    sent += 1024
                else:
                    response = self._send_command(
                        Command.SEND_PAYLOAD, payload=byte, readsize=1024, bypass_queue=True)
                    assert response.startswith(
                        b'file_rev_done'), 'Failed to upload file'
                print("Sent %d bytes" % sent)
                byte = file.read(1024)

    def DeleteFile(self, target_path: str):
        self._init_packet_interaction()
        
        payload = len(target_path).to_bytes(4, byteorder='big') + \
            Padding.NULL.value * 3 + bytearray(target_path, 'utf-8')
        
        self._send_command(
            Command.DELETE_FILE,
            payload=payload,
            bypass_queue=True)

    def GetFileSize(self, target_path: str, is_isolated_call: bool = True):
        if is_isolated_call:
            self._init_packet_interaction()
            
        payload = len(target_path).to_bytes(4, byteorder='big') + \
            Padding.NULL.value * 3 + bytearray(target_path, 'utf-8')

        response = self._send_command(
            Command.QUERY_FILE_SIZE, 
            payload=payload, 
            readsize=1024, 
            bypass_queue=True)
        
        size = int(response.decode().rstrip('\x00'))

        assert size > 0, 'File does not exist'
        return size

    def PlayImageFromStorage(self, target_path: str, is_isolated_call: bool = True):
        if is_isolated_call:
            self._init_packet_interaction()
            
        payload = len(target_path).to_bytes(4, byteorder='big') + \
            Padding.NULL.value * 3 + bytearray(target_path, 'utf-8')

        response = self._send_command(Command.PLAY_IMAGE, payload=payload,
                                      readsize=1024, bypass_queue=True)

        assert response.startswith(b'play_img_ok'), 'Failed to play image'

    def PlayVideoFromStorage(self, target_path: str, is_isolated_call: bool = True):
        if is_isolated_call:
            self._init_packet_interaction()
        
        payload = len(target_path).to_bytes(4, byteorder='big') + \
            Padding.NULL.value * 3 + bytearray(target_path, 'utf-8')
        
        response = self._send_command(
            Command.PLAY_VIDEO, 
            payload=payload,
            readsize=1024, 
            bypass_queue=True)

        assert response.startswith(
            b'play_video_success'), 'Failed to play video'

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
        if image.size[1] > self.get_height():
            image_height = self.get_height()
        if image.size[0] > self.get_width():
            image_width = self.get_width()

        assert x <= self.get_width(), 'Image X coordinate must be <= display width'
        assert y <= self.get_height(), 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'

        if x == 0 and y == 0 and (image_width == self.get_width()) and (image_height == self.get_height()):
            with self.update_queue_mutex:
                self._stop_media()
                self.SetOrientation(self.orientation, is_isolated_call=False)

                self._send_command(Command.PRE_UPDATE_BITMAP)
                self._send_command(Command.START_DISPLAY_BITMAP,
                                   padding=Padding.START_DISPLAY_BITMAP)

                self.SetBrightness(60, is_isolated_call=False)

                self._send_command(
                    Command.DISPLAY_BITMAP,
                    payload=bytearray(int(self.display_width * self.display_width)
                                      .to_bytes(4)),
                    bypass_queue=True
                )

                response = self._send_command(
                    Command.SEND_PAYLOAD,
                    payload=bytearray(
                        self._generate_full_image(image, self.orientation)),
                    readsize=1024,
                    bypass_queue=True
                )

                assert response.startswith(
                    b'full_png_sucess'), 'Failed to display bitmap'

                self._send_command(Command.QUERY_STATUS, readsize=1024)
        else:
            with self.update_queue_mutex:
                update_image, img_len = self._generate_update_image(
                    image, x, y, self.orientation)

                payload_len = img_len.to_bytes(4, byteorder='big')
                command_payload = payload_len + \
                    Count.Start.to_bytes(7, byteorder='big')

                self._send_command(Command.UPDATE_BITMAP,
                                   payload=command_payload)
                self._send_command(Command.SEND_PAYLOAD, payload=update_image)
                self._send_command(Command.QUERY_STATUS, readsize=1024)
            Count.Start += 1

    @staticmethod
    def _generate_full_image(image: Image, orientation: Orientation = Orientation.PORTRAIT):
        if orientation == Orientation.REVERSE_PORTRAIT:
            image = image.rotate(90, expand=True)
        elif orientation == Orientation.REVERSE_LANDSCAPE:
            image = image.rotate(180, expand=True)
        elif orientation == Orientation.PORTRAIT:
            image = image.rotate(270, expand=True)

        image_data = image.convert("RGBA").load()
        pixel_data = []
        for y in range(image.height):
            for x in range(image.width):
                pixel = image_data[x, y]
                pixel_data += [pixel[2], pixel[1], pixel[0], pixel[3]]

        hex_data = bytes(pixel_data)
        return b'\x00'.join(hex_data[i:i + 249] for i in range(0, len(hex_data), 249))

    def _generate_update_image(self, image, x, y, orientation: Orientation = Orientation.PORTRAIT):
        x0, y0 = x, y

        if orientation == Orientation.PORTRAIT:
            y0 = self.get_height() - y - image.height
        elif orientation == Orientation.REVERSE_PORTRAIT:
            image = image.rotate(180, expand=True)
            x0 = self.get_width() - x - image.width
        elif orientation == Orientation.LANDSCAPE:
            image = image.rotate(90, expand=True)
            x0, y0 = y, x
        elif orientation == Orientation.REVERSE_LANDSCAPE:
            image = image.rotate(270, expand=True)
            x0 = self.get_height() - y - image.width
            y0 = self.get_width() - x - image.height

        img_raw_data = bytes([])
        image_data = image.convert("RGBA").load()

        for w in range(image.width):
            # Target start
            img_raw_data += (((x0 + w) * self.display_height) + y0).to_bytes(3, byteorder='big')

            # Number of pixels to be written
            img_raw_data += image.height.to_bytes(2, byteorder='big')

            for h in range(image.height):
                current_pixel = image_data[w, image.height - h - 1]
                img_raw_data += bytes([current_pixel[2], current_pixel[1],
                                      current_pixel[0], current_pixel[3]])

        img_raw_data += bytes([0xef, 0x69])

        return b'\x00'.join(img_raw_data[i:i + 249] for i in range(0, len(img_raw_data), 249)), len(img_raw_data)

    def _stop_media(self, is_isolated_call: bool = True):
        if is_isolated_call:
            self._init_packet_interaction()

        self._send_command(Command.STOP_MEDIA, bypass_queue=True)
        response = self._send_command(
            Command.STOP_VIDEO, readsize=1024, bypass_queue=True)

        assert response.startswith(b'media_stop'), 'Failed to stop media'

    def _init_packet_interaction(self):
        response = self._send_command(
            Command.HELLO, readsize=1024, bypass_queue=True)
        assert response.startswith(
            b'chs_88inch'), 'Failed to initialize packet interaction'

    def _no_update(self):
        payload_len = (8).to_bytes(4, byteorder='big')
        command_payload = payload_len + \
            Count.Start.to_bytes(7, byteorder='big')

        self._send_command(Command.UPDATE_BITMAP, payload=command_payload)
        self._send_command(Command.UPDATE_BITMAP_NO_CHANGES)
        self._send_command(Command.QUERY_STATUS, readsize=1024)

        Count.Start += 1
