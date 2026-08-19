# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
# Copyright (C) 2023 Alex W. Baulé (alexwbaule)
# Copyright (C) 2023 Arthur Ferrai (arthurferrai)
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
import string
import time
from enum import Enum
from math import ceil
from typing import Optional, Tuple

import numpy as np
import serial
from PIL import Image
from serial.tools.list_ports import comports

from library.lcd.lcd_comm import Orientation, LcdComm
from library.lcd.serialize import image_to_BGRA, image_to_BGR, chunked
from library.log import logger


class Count:
    Start = 0


# READ HELLO ALWAYS IS 23.
# ALL READS IS 1024

# ORDER:
# SEND HELLO
# READ HELLO (23)
# SEND STOP_VIDEO
# SEND STOP_MEDIA
# READ STATUS (1024)
# SEND SET_BRIGHTNESS
# SEND SET_OPTIONS WITH ORIENTATION ?
# SEND PRE_UPDATE_BITMAP
# SEND START_DISPLAY_BITMAP
# SEND DISPLAY_BITMAP
# READ STATUS (1024)
# SEND QUERY_STATUS
# READ STATUS (1024)
# WHILE:
#   SEND UPDATE_BITMAP
#   SEND QUERY_STATUS
#   READ STATUS(1024)

class Command(Enum):
    # COMMANDS
    HELLO = bytearray((0x01, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0xc5, 0xd3))
    OPTIONS = bytearray((0x7d, 0xef, 0x69, 0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x2d))
    RESTART = bytearray((0x84, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    TURNOFF = bytearray((0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    TURNON = bytearray((0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x00))

    SET_BRIGHTNESS = bytearray((0x7b, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00))

    # STOP COMMANDS
    STOP_VIDEO = bytearray((0x79, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    STOP_MEDIA = bytearray((0x96, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    # 11.3" / chs_113inch vendor sequence (ShinySnake G600 / TURZX)
    PRE_FULL_FRAME = bytearray((0x81, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    STOP_SESSION = bytearray((0x87, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    OPTIONS_113INCH = bytearray((0x7d, 0xef, 0x69, 0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0xaa))

    # IMAGE QUERY STATUS
    QUERY_STATUS = bytearray((0xcf, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))

    # STATIC IMAGE
    START_DISPLAY_BITMAP = bytearray((0x2c,))
    PRE_UPDATE_BITMAP = bytearray((0x86, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01))
    UPDATE_BITMAP = bytearray((0xcc, 0xef, 0x69, 0x00))
    DISPLAY_BITMAP_2INCH = bytearray((0xc8, 0xef, 0x69, 0x00)) + bytearray((0x0E, 0x10))
    DISPLAY_BITMAP_5INCH = bytearray((0xc8, 0xef, 0x69, 0x00)) + bytearray((0x17, 0x70))
    DISPLAY_BITMAP_8INCH = bytearray((0xc8, 0xef, 0x69, 0x00)) + bytearray((0x38, 0x40))
    DISPLAY_BITMAP_113INCH = bytearray((0xc8, 0xef, 0x69, 0x00)) + bytearray((0x33, 0x90))

    STARTMODE_DEFAULT = bytearray((0x00,))
    STARTMODE_IMAGE = bytearray((0x01,))
    STARTMODE_VIDEO = bytearray((0x02,))
    FLIP_180 = bytearray((0x01,))
    NO_FLIP = bytearray((0x00,))
    SEND_PAYLOAD = bytearray((0xFF,))


class Padding(Enum):
    NULL = bytearray([0x00])
    START_DISPLAY_BITMAP = bytearray([0x2c])


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


class SubRevision(Enum):
    UNKNOWN = 0
    REV_2INCH = 1  # For 2.1" and 2.8" models
    REV_5INCH = 2
    REV_8INCH = 3
    REV_113INCH = 4


class Rev113Geometry:
    # Every other Rev C size's C8 wire canvas matches its glass 1:1, so
    # display_width/display_height (from LcdComm) are enough on their own.
    # 11.3" is the only size where that's not true. Its C8 canvas is a
    # reshape of the glass, not the same shape. So it's the only one that
    # needs a second set of dimensions at all.
    C8_WIDTH = 1760
    C8_HEIGHT = 480
    GLASS_WIDTH = 440
    GLASS_HEIGHT = 1920
    REV_113_WIDTH = GLASS_WIDTH
    REV_113_HEIGHT = GLASS_HEIGHT


WAKE_RETRIES = 15


# This class is for Turing Smart Screen 2.1" / 2.8" / 5" / 8.8" / 11.3" screens
class LcdCommRevC(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 480, display_height: int = 800,
                 update_queue: Optional[queue.Queue] = None):
        logger.debug("HW revision: C")
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self._last_status_ts_113inch = 0.0
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    def openSerial(self):
        LcdComm.openSerial(self)
        # Full 11.3" frames are ~3.4 MB; the default write timeout is too short.
        # Set here rather than in __init__ so it survives the reconnect that
        # WriteLine/ReadData perform on SerialException.
        if self.lcd_serial is not None and self._subrevision_from_size() == SubRevision.REV_113INCH:
            self.lcd_serial.write_timeout = 20

    @staticmethod
    def auto_detect_com_port() -> Optional[str]:
        # If sleeping device is detected through serial number or vid/pid, try to wake it up
        for com_port in comports():
            if com_port.serial_number == 'USB7INCH' or com_port.serial_number == 'CT21INCH':
                LcdCommRevC._wake_up_device(com_port)
            elif com_port.vid == 0x1a86 and com_port.pid == 0xca21:
                LcdCommRevC._wake_up_device(com_port)

        return LcdCommRevC._get_awake_com_port(comports())

    @staticmethod
    def _get_awake_com_port(com_ports) -> Optional[str]:
        # Try to find awake device through serial number or vid/pid
        for com_port in com_ports:
            if com_port.serial_number == '20080411':
                return com_port.device
            if com_port.vid == 0x0525 and com_port.pid == 0xa4a7:
                return com_port.device
            if com_port.vid == 0x1d6b and (com_port.pid == 0x0121 or com_port.pid == 0x0106):
                return com_port.device

        return None

    @staticmethod
    def _wake_up_device(com_port):
        # Connect to the device to wake it up
        logger.debug(f"Waiting for device {com_port} to be turned ON...")

        for i in range(WAKE_RETRIES):
            try:
                # Try to connect every second, since it takes sometimes multiple connect to wake up the device
                serial.Serial(com_port.device, 115200, timeout=1, rtscts=True)
            except serial.SerialException:
                pass

            if LcdCommRevC._get_awake_com_port(comports()) is not None:
                time.sleep(1)
                logger.debug(f"Detected screen turned ON")
                return

            time.sleep(1)

        logger.error(f"Could not turn screen on after {WAKE_RETRIES} seconds, aborting.")

    def _send_command(self, cmd: Command, payload: Optional[bytearray] = None, padding: Optional[Padding] = None,
                      bypass_queue: bool = False, readsize: Optional[int] = None):
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
                self.ReadData(readsize)
        else:
            # Lock queue mutex then queue the request
            self.update_queue.put((self.WriteData, [message]))
            if readsize:
                self.update_queue.put((self.ReadData, [readsize]))

    def _subrevision_from_size(self) -> SubRevision:
        if self.display_width == 480 and self.display_height == 480:
            return SubRevision.REV_2INCH
        if self.display_width == 480 and self.display_height == 800:
            return SubRevision.REV_5INCH
        if self.display_width == 480 and self.display_height == 1920:
            return SubRevision.REV_8INCH
        if self.display_width == Rev113Geometry.REV_113_WIDTH and self.display_height == Rev113Geometry.REV_113_HEIGHT:
            return SubRevision.REV_113INCH
        return SubRevision.UNKNOWN

    @staticmethod
    def _decode_hello(raw: bytes) -> str:
        # IDs are ASCII and model-dependent length. The 8.8" ID is 23 chars
        # (chs_88inch.dev1_rom1.90); the 11.3" ID is 24
        # (chs_113inch.dev1_rom1.90). A hardcoded 23-byte read truncates the
        # latter to rom1.9 and the ROM parse falls back to 87 (BGR instead of BGRA).
        return ''.join(c for c in raw.decode(errors="ignore") if c in set(string.printable)).split('\x00')[0].strip()

    def _read_hello(self) -> str:
        self._send_command(Command.HELLO, bypass_queue=True)
        return self._decode_hello(self.serial_read(64))

    def _hello(self):
        # This command reads LCD answer on serial link, so it bypasses the queue
        self.sub_revision = SubRevision.UNKNOWN
        self.serial_flush_input()
        response = self._read_hello()
        self.serial_flush_input()
        logger.debug("Display ID returned: %s" % response)
        while not response.startswith("chs_"):
            logger.warning("Display returned invalid or unsupported ID, try again in 1 second")
            time.sleep(1)
            response = self._read_hello()
            self.serial_flush_input()
            logger.debug("Display ID returned: %s" % response)

        # 11.3" identifies itself; do not classify it as the 8.8" (also 480x1920).
        if response.startswith("chs_113inch"):
            self.sub_revision = SubRevision.REV_113INCH
            self.display_width = Rev113Geometry.REV_113_WIDTH
            self.display_height = Rev113Geometry.REV_113_HEIGHT
        else:
            # Note: ID returned by display are not reliable for some models e.g. 2.1" displays return "chs_5inch"
            # Rely on width/height for sub-revision detection
            self.sub_revision = self._subrevision_from_size()
            if self.sub_revision == SubRevision.UNKNOWN:
                logger.error(f"Unsupported resolution {self.display_width}x{self.display_height} for revision C")

        # Detect ROM version
        try:
            self.rom_version = int(response.split(".")[2])
            if self.rom_version < 80 or self.rom_version > 100:
                logger.warning("ROM version %d may be invalid, use default ROM version 87" % self.rom_version)
                self.rom_version = 87
        except Exception:
            logger.warning("Display returned invalid or unsupported ID, use default ROM version 87")
            self.rom_version = 87

        logger.debug("HW sub-revision detected: %s, ROM version: %d" % ((str(self.sub_revision)), self.rom_version))

    def InitializeComm(self):
        self._hello()

    def Reset(self):
        if self.display_width == Rev113Geometry.REV_113_WIDTH and self.display_height == Rev113Geometry.REV_113_HEIGHT:
            self.serial_flush_input()
            ident = self._read_hello()
            self.serial_flush_input()
            if ident.startswith("chs_113inch"):
                logger.info("11.3\" panel: skipping firmware RESTART")
                return
            # Declared size matched but the panel didn't identify as 11.3" -- fall through to normal RESTART.

        logger.info("Display reset (COM port may change)...")
        # Reset command bypasses queue because it is run when queue threads are not yet started
        self._send_command(Command.RESTART, bypass_queue=True)
        self.closeSerial()
        # Wait for disconnection (max. 15 seconds)
        for i in range(15):
            if LcdCommRevC._get_awake_com_port(comports()) is not None:
                time.sleep(1)
        # Wait for reconnection (max. 15 seconds)
        for i in range(15):
            if LcdCommRevC._get_awake_com_port(comports()) is None:
                time.sleep(1)
        # Reconnect to device
        self.openSerial()

    def Clear(self):
        # This hardware does not implement a Clear command: display a blank image on the whole screen
        # Force an orientation in case the screen is currently configured with one different from the theme
        backup_orientation = self.orientation
        self.SetOrientation(orientation=Orientation.PORTRAIT)

        blank = Image.new("RGB", (self.get_width(), self.get_height()), (255, 255, 255))
        self.DisplayPILImage(blank)

        # Restore orientation
        self.SetOrientation(orientation=backup_orientation)

    def ScreenOff(self):
        # logger.info("Calling ScreenOff")
        self._send_command(Command.STOP_VIDEO)
        self._send_command(Command.STOP_MEDIA, readsize=1024)
        self._send_command(Command.TURNOFF)

    def ScreenOn(self):
        # logger.info("Calling ScreenOn")
        self._send_command(Command.STOP_VIDEO)
        self._send_command(Command.STOP_MEDIA, readsize=1024)
        if getattr(self, "sub_revision", None) == SubRevision.REV_113INCH:
            # Vendor sends 0x81 after STOP_MEDIA before the first frame.
            self._send_command(Command.PRE_FULL_FRAME)
        # self._send_command(Command.SET_BRIGHTNESS, payload=bytearray([255]))

    def SetBrightness(self, level: int = 25):
        # logger.info("Call SetBrightness")
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        # Brightness scales from 0 to 255, with 255 being the brightest and 0 being the darkest.
        # Convert our brightness % to an absolute value.
        converted_level = int((level / 100) * 255)

        self._send_command(Command.SET_BRIGHTNESS, payload=bytearray((converted_level,)), bypass_queue=True)

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        self.orientation = orientation
        # logger.info(f"Call SetOrientation to: {self.orientation.name}")

        # if self.orientation == Orientation.REVERSE_LANDSCAPE or self.orientation == Orientation.REVERSE_PORTRAIT:
        #   b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + Command.FLIP_180.value + SleepInterval.OFF.value
        #   self._send_command(Command.OPTIONS, payload=b)
        # else:
        if getattr(self, "sub_revision", None) == SubRevision.REV_113INCH:
            # Vendor payload is 0xAA rather than STARTMODE_DEFAULT (0x2D).
            self._send_command(Command.OPTIONS_113INCH)
            return
        b = Command.STARTMODE_DEFAULT.value + Padding.NULL.value + Command.NO_FLIP.value + SleepInterval.OFF.value
        self._send_command(Command.OPTIONS, payload=b)

    def DisplayPILImage(
            self,
            image: Image.Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
    ):
        # For full-screen images on the 11.3" display route through a custm full-frame sender
        # Needed since on the 11.3" the c8 canvas size != the physical glass size
        if (
            getattr(self, "sub_revision", None) == SubRevision.REV_113INCH
            and x == 0 and y == 0
            and image.size in (
                (Rev113Geometry.GLASS_WIDTH, Rev113Geometry.GLASS_HEIGHT),  # 440×1920 declared theme size == native glass
                (Rev113Geometry.C8_WIDTH, Rev113Geometry.C8_HEIGHT),  # 1760×480 native C8 wire canvas
                (480, Rev113Geometry.GLASS_HEIGHT),  # 480×1920 borrowed 8.8" theme, scale don't crop
            )
        ):
            with self.update_queue_mutex:
                self._display_full_113inch(image)
            return

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

        if image_width != image.size[0] or image_height != image.size[1]:
            image = image.crop((0, 0, image_width, image_height))

        assert x <= self.get_width(), 'Image X coordinate must be <= display width'
        assert y <= self.get_height(), 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'

        if x == 0 and y == 0 and (image_width == self.get_width()) and (image_height == self.get_height()):
            with self.update_queue_mutex:
                if self.sub_revision == SubRevision.REV_113INCH:
                    self._display_full_113inch(image)
                else:
                    self._send_command(Command.PRE_UPDATE_BITMAP)
                    self._send_command(Command.START_DISPLAY_BITMAP, padding=Padding.START_DISPLAY_BITMAP)

                    if self.sub_revision == SubRevision.REV_5INCH:
                        display_bmp_cmd = Command.DISPLAY_BITMAP_5INCH
                    elif self.sub_revision == SubRevision.REV_2INCH:
                        display_bmp_cmd = Command.DISPLAY_BITMAP_2INCH
                    elif self.sub_revision == SubRevision.REV_8INCH:
                        display_bmp_cmd = Command.DISPLAY_BITMAP_8INCH
                    else:
                        display_bmp_cmd = Command.DISPLAY_BITMAP_8INCH

                    self._send_command(display_bmp_cmd,
                                       payload=bytearray(
                                           int(self.display_width * self.display_width / 64).to_bytes(2, "big")))
                    self._send_command(Command.SEND_PAYLOAD,
                                       payload=bytearray(self._generate_full_image(image)),
                                       readsize=1024)
                    self._send_command(Command.QUERY_STATUS, readsize=1024)
        else:
            with self.update_queue_mutex:
                img, pyd = self._generate_update_image(image, x, y, Count.Start, Command.UPDATE_BITMAP)
                if self.sub_revision == SubRevision.REV_113INCH:
                    # Poll status at most ~1 Hz; faster 0xcf jams this ROM.
                    self._maybe_query_status_113inch()
                    self._send_command(Command.SEND_PAYLOAD, payload=pyd)
                    self._send_command(Command.SEND_PAYLOAD, payload=img)
                else:
                    self._send_command(Command.SEND_PAYLOAD, payload=pyd)
                    self._send_command(Command.SEND_PAYLOAD, payload=img)
                    self._send_command(Command.QUERY_STATUS, readsize=1024)
            Count.Start += 1

    def _display_full_113inch(self, image: Image.Image):
        """Full-frame 0xc8 path for chs_113inch.

        PRE_UPDATE + 0x2C block + 0xc8 00 33 90, BGRA with a 0x00 every 249
        bytes, no 0xEF69 terminator, padded to 250. Sent twice. ACK is the
        ASCII string 'full_png_sucess'. No extra W*W/64 size word.

        Every send here uses bypass_queue=True. _write_113inch_c8_body/
        _wait_113inch_full_png_success always write/read the serial port directly
        (there's no way to chunk a body write or an ACK wait through
        update_queue), so if the header commands above were left to go
        through the queue instead, main.py's real update_queue could
        dequeue and send the body on a *different* thread before the
        queued header command actually went out -- a real ordering race
        that only shows up when a queue is configured (i.e. real main.py
        use, not a standalone script that constructs the driver without
        one). That's what caused the intermittent "missing full_png_sucess"
        seen running a real theme end-to-end 2026-08-17: the background
        frame silently raced its own header and got dropped.
        """
        self._send_command(Command.PRE_UPDATE_BITMAP, bypass_queue=True)
        self._send_command(Command.START_DISPLAY_BITMAP, padding=Padding.START_DISPLAY_BITMAP, bypass_queue=True)
        payload = bytearray(self._generate_full_image(image))
        # Send twice and wait for 'full_png_sucess' after each. Without the
        # ACK wait the second copy piles onto the first and mixed pixels tear.
        for _ in range(2):
            self._send_command(Command.DISPLAY_BITMAP_113INCH, bypass_queue=True)
            # Write the body in 25 KiB chunks; a single 3.4 MB write returns
            # as soon as the tty buffer fills.
            self._write_113inch_c8_body(payload)
            ack = self._wait_113inch_full_png_success()
            if "full_png_sucess" not in ack:
                logger.warning("11.3\" C8: missing full_png_sucess (%r)", ack[:80])
        # Vendor restarts the 0xcc sequence counter after a new full frame.
        Count.Start = 0
        self._last_status_ts_113inch = 0.0

    def _write_113inch_c8_body(self, payload: bytearray) -> None:
        """Pad to 250 and write in 25_000-byte chunks (vendor URB size)."""
        msg = bytes(payload)
        if len(msg) % 250:
            msg += bytes(250 - (len(msg) % 250))
        if self.lcd_serial is not None:
            self.lcd_serial.reset_input_buffer()
        for i in range(0, len(msg), 25000):
            self.WriteData(bytearray(msg[i : i + 25000]))
            if self.lcd_serial is not None:
                self.lcd_serial.flush()

    def _wait_113inch_full_png_success(self, timeout: float = 8.0) -> str:
        deadline = time.time() + timeout
        buf = b""
        while time.time() < deadline:
            chunk = self.serial_read(1024)
            if chunk:
                buf += chunk
                text = self._decode_hello(buf)
                if "full_png_sucess" in text:
                    return text
        return self._decode_hello(buf)

    def _maybe_query_status_113inch(self):
        """Vendor polls 0xcf at ~1 Hz, never faster, and always before a 0xcc."""
        now = time.time()
        if now - self._last_status_ts_113inch < 1.0:
            return
        self._send_command(Command.QUERY_STATUS, readsize=1024)
        self._last_status_ts_113inch = now

    def _pack_113inch_c8(self, image: Image.Image) -> Image.Image:
        """Pack a 440×1920 glass image into the vendor 1760×480 C8 canvas.

        Canvas pixel (cy, cx) is glass pixel (4*cy + cx//440, cx%440): each
        canvas row packs 4 consecutive glass rows side by side. That is
        exactly a (1920, 440, 3) -> (480, 1760, 3) numpy reshape, no
        interpolation. A native 1760×480 image is sent unchanged; anything
        else is resized to the true 440×1920 glass resolution first.
        """
        if image.size == (Rev113Geometry.C8_WIDTH, Rev113Geometry.C8_HEIGHT):
            return image
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        if image.size != (Rev113Geometry.GLASS_WIDTH, Rev113Geometry.GLASS_HEIGHT):
            image = image.resize((Rev113Geometry.GLASS_WIDTH, Rev113Geometry.GLASS_HEIGHT), Image.Resampling.LANCZOS)
        glass = np.asarray(image.convert("RGB"))  # (1920, 440, 3)
        canvas = glass.reshape(Rev113Geometry.C8_HEIGHT, Rev113Geometry.C8_WIDTH, 3)  # (480, 1760, 3)
        return Image.fromarray(canvas, "RGB")

    def _map_113inch_view_to_glass(
            self, x: int, y: int, width: int, height: int
    ) -> Tuple[int, int, int, int]:
        """Declared 440×1760 widget rect → true 440×1920 glass rect.

        x/width are unscaled (declared width == glass width). y/height scale
        by 1920/1760 to fill the taller glass.
        """
        view_h = self.display_height or Rev113Geometry.REV_113_HEIGHT
        glass_h = Rev113Geometry.GLASS_HEIGHT
        dx = x
        dy = int(round(y * glass_h / view_h))
        dw = width
        dh = max(1, int(round(height * glass_h / view_h)))
        if dy >= glass_h:
            dy = glass_h - 1
        if dy + dh > glass_h:
            dh = glass_h - dy
        return dx, dy, dw, dh

    def _generate_full_image(self, image: Image.Image) -> bytes:
        if self.sub_revision == SubRevision.REV_113INCH:
            image = self._pack_113inch_c8(image)
        elif self.sub_revision == SubRevision.REV_8INCH:
            # Switch landscape/portrait mode for 8"
            if self.orientation == Orientation.LANDSCAPE:
                image = image.rotate(270, expand=True)
            elif self.orientation == Orientation.REVERSE_LANDSCAPE:
                image = image.rotate(90, expand=True)
            elif self.orientation == Orientation.PORTRAIT:
                image = image.rotate(180, expand=True)
            elif self.orientation == Orientation.REVERSE_PORTRAIT:
                pass
        else:
            if self.orientation == Orientation.PORTRAIT:
                image = image.rotate(90, expand=True)
            elif self.orientation == Orientation.REVERSE_PORTRAIT:
                image = image.rotate(270, expand=True)
            elif self.orientation == Orientation.REVERSE_LANDSCAPE:
                image = image.rotate(180)

        bgra_data, pixel_size = image_to_BGRA(image)

        return b'\x00'.join(chunked(bgra_data, 249))

    def _generate_update_image(
            self, image: Image.Image, x: int, y: int, count: int, cmd: Optional[Command] = None
    ) -> Tuple[bytearray, bytearray]:
        if self.sub_revision == SubRevision.REV_113INCH:
            return self._generate_update_image_113inch(image, x, y, count, cmd)

        x0, y0 = x, y
        if self.sub_revision == SubRevision.REV_8INCH:
            # Switch landscape/portrait mode for 8"
            if self.orientation == Orientation.LANDSCAPE:
                image = image.rotate(270, expand=True)
                y0 = self.get_height() - y - image.width
            elif self.orientation == Orientation.REVERSE_LANDSCAPE:
                image = image.rotate(90, expand=True)
                x0 = self.get_width() - x - image.height
            elif self.orientation == Orientation.PORTRAIT:
                image = image.rotate(180, expand=True)
                x0 = self.get_height() - y - image.height
                y0 = self.get_height() - x - image.width
            elif self.orientation == Orientation.REVERSE_PORTRAIT:
                x0 = y
                y0 = x
        else:
            if self.orientation == Orientation.PORTRAIT:
                image = image.rotate(90, expand=True)
                x0 = self.get_width() - x - image.height
            elif self.orientation == Orientation.REVERSE_PORTRAIT:
                image = image.rotate(270, expand=True)
                y0 = self.get_height() - y - image.width
            elif self.orientation == Orientation.REVERSE_LANDSCAPE:
                image = image.rotate(180)
                y0 = self.get_width() - x - image.width
                x0 = self.get_height() - y - image.height
            elif self.orientation == Orientation.LANDSCAPE:
                x0 = y
                y0 = x

        img_raw_data = bytearray()

        # Some screens require different RGBA encoding
        if self.sub_revision != SubRevision.REV_2INCH and self.rom_version > 88:
            # BGRA mode on 4 bytes : [B, G, R, A]
            img_data, pixel_size = image_to_BGRA(image)
        else:
            # BGRA mode on 3 bytes: [6-bit B + 2-bit A, 6-bit G + 2-bit A, 8-bit R]
            # img_data, pixel_size = image_to_compressed_BGRA(image)
            # For now use simple BGR that is more optimized, because this program does not support transparent background
            img_data, pixel_size = image_to_BGR(image)

        for h, line in enumerate(chunked(img_data, image.width * pixel_size)):
            if self.sub_revision == SubRevision.REV_8INCH:
                # Switch landscape/portrait mode for 8" / 11.3"
                img_raw_data += int(((x0 + h) * self.display_width) + y0).to_bytes(3, "big")
            else:
                img_raw_data += int(((x0 + h) * self.display_height) + y0).to_bytes(3, "big")
            img_raw_data += int(image.width).to_bytes(2, "big")
            img_raw_data += line

        if self.sub_revision == SubRevision.REV_113INCH and self._update_payload_needs_dummy(img_raw_data):
            # Dummy visible-pixel field; shifts 0xEF69 off a packet boundary (PR #348).
            img_raw_data += bytes((0x80, 0x00, 0x00, 0x00, 0x00))

        image_size = int(len(img_raw_data) + 2).to_bytes(3, "big")  # The +2 is for the "ef69" that will be added later.

        # logger.debug("Render Count: {}".format(count))
        payload = bytearray()

        if cmd:
            payload.extend(cmd.value)
        payload.extend(image_size)
        payload.extend(Padding.NULL.value * 3)
        payload.extend(count.to_bytes(4, 'big'))

        if len(img_raw_data) > 250:
            img_raw_data = bytearray(b'\x00').join(chunked(bytes(img_raw_data), 249))
        img_raw_data += b'\xef\x69'

        return img_raw_data, payload

    def _generate_update_image_113inch(
            self, image: Image.Image, x: int, y: int, count: int, cmd: Optional[Command] = None
    ) -> Tuple[bytearray, bytearray]:
        """Encode a partial update into the 1760×480 C8 canvas.

        Callers use the declared 440×1760 portrait; x/y are scaled into the
        true 440×1920 glass first (_map_113inch_view_to_glass). Each glass
        row then decomposes into a canvas row + sub-slot (glass_row =
        4*canvas_row + sub, see class docstring): start = canvas_row*1760 +
        sub*440 + x + col. Records are n=16 BGRA spans; image_size includes
        the trailing ef69.
        """
        x, y, dst_w, dst_h = self._map_113inch_view_to_glass(x, y, image.width, image.height)
        if image.size != (dst_w, dst_h):
            image = image.resize((dst_w, dst_h), Image.Resampling.LANCZOS)
        img_data, _ = image_to_BGRA(image)
        stride = image.width * 4
        span = 16
        img_raw_data = bytearray()
        for h, line in enumerate(chunked(img_data, stride)):
            glass_row = y + h
            canvas_row, sub = divmod(glass_row, 4)
            row_x0 = sub * Rev113Geometry.GLASS_WIDTH + x
            col = 0
            while col < image.width:
                n = min(span, image.width - col)
                start = canvas_row * Rev113Geometry.C8_WIDTH + row_x0 + col
                img_raw_data += int(start).to_bytes(3, "big")
                img_raw_data += int(n).to_bytes(2, "big")
                img_raw_data += line[col * 4 : (col + n) * 4]
                col += n
        img_raw_data += b"\xef\x69"
        image_size = int(len(img_raw_data)).to_bytes(3, "big")
        payload = bytearray()
        if cmd:
            payload.extend(cmd.value)
        payload.extend(image_size)
        payload.extend(Padding.NULL.value * 3)
        payload.extend(count.to_bytes(4, "big"))
        if len(img_raw_data) > 250:
            img_raw_data = bytearray(b"\x00").join(chunked(bytes(img_raw_data), 249))
        return img_raw_data, payload

    @staticmethod
    def _update_payload_needs_dummy(img_raw_data: bytearray) -> bool:
        """True if ef69 would sit at the start or end of the final 250-byte packet."""
        body = bytes(img_raw_data)
        if len(body) > 250:
            body = b'\x00'.join(chunked(body, 249))
        candidate = body + b'\xef\x69'
        n = len(candidate) if len(candidate) % 250 == 0 else 250 * ceil(len(candidate) / 250)
        last = (candidate + bytes(n - len(candidate)))[-250:]
        return (
            (last[:2] == b'\xef\x69' and set(last[2:]) <= {0})
            or last[-2:] == b'\xef\x69'
            or (last[0] == 0x69 and last[1:5] == b'\x00\x00\x00\x00')
        )
