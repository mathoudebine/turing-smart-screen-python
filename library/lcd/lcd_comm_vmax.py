# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Driver for HL-VMAX / Solarmax USB LCD Displays (Artinchip VID 0x33C3, PID 0xF101)
# Supports 462x1920, 320x1480, 480x1920 resolutions.
#

import io
import re
import time
from typing import Optional, Tuple
from enum import IntEnum
import serial
from serial.tools.list_ports import comports
from PIL import Image

from library.lcd.lcd_comm import LcdComm, Orientation, queue
from library.log import logger

VID = 0x33C3
PID = 0xF101
HANDSHAKE = bytes([0xF0, 0xA5, 0x5A, 0x0F])
SN_LEN = 26
DEFAULT_WIDTH = 462
DEFAULT_HEIGHT = 1920


class LcdCommVmax(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = DEFAULT_WIDTH,
                 display_height: int = DEFAULT_HEIGHT, update_queue: Optional[queue.Queue] = None):
        logger.debug("HW revision: VMAX / Solarmax (Artinchip)")
        super().__init__(com_port, display_width, display_height, update_queue)
        self.serial_number = None
        self.brightness = 100
        # Canvas for full frame composition
        self._canvas = Image.new("RGB", (self.display_width, self.display_height), (0, 0, 0))
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port() -> Optional[str]:
        ports = comports()
        for p in ports:
            if p.vid == VID and p.pid == PID:
                return p.device
            if p.serial_number and "VMAX" in p.serial_number.upper():
                return p.device
        return None

    def openSerial(self):
        for attempt in range(1, 11):
            com_port = self.com_port
            if com_port == 'AUTO':
                com_port = self.auto_detect_com_port()
                if not com_port:
                    logger.warning(f"Cannot find HL-VMAX COM port automatically, retrying ({attempt}/10)")
                    time.sleep(1)
                    continue
                logger.debug(f"Auto detected COM port: {com_port}")
            else:
                logger.debug(f"Static COM port: {com_port}")

            try:
                self.lcd_serial = serial.Serial(com_port, 115200, timeout=1, write_timeout=1, rtscts=False, dsrdtr=False)
                self.lcd_serial.dtr = True
                self.lcd_serial.rts = True
                self.lcd_serial.reset_input_buffer()
                self.lcd_serial.reset_output_buffer()
                return
            except Exception as e:
                logger.warning(f"Cannot open COM port {com_port}: {e} - retrying ({attempt}/10)")
                time.sleep(1)

    def InitializeComm(self):
        logger.debug("Initializing HL-VMAX communication...")
        self.serial_flush_input()
        try:
            self.serial_write(HANDSHAKE)
            raw = self.serial_read(SN_LEN)
            if len(raw) == SN_LEN:
                self.serial_number = raw.decode("ascii", errors="replace").strip()
                logger.info(f"Connected to HL-VMAX screen, Serial Number: {self.serial_number}")
                self._parse_geometry(self.serial_number)
            else:
                logger.warning(f"Unexpected handshake response length: {len(raw)} bytes")
        except Exception as e:
            logger.error(f"Failed during HL-VMAX handshake: {e}")

    def _parse_geometry(self, sn: str):
        # Format example: VMAXD160462*1920S262001750 or VMAXA170320*1480S261001155
        m = re.search(r"(\d{3,4})\s*\*\s*(\d{2,5})", sn)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            if w >= 100 and h >= 100:
                logger.info(f"Detected hardware panel geometry: {w}x{h}")
                self.display_width = w
                self.display_height = h
                self._canvas = Image.new("RGB", (self.display_width, self.display_height), (0, 0, 0))

    def Reset(self):
        self.serial_flush_input()
        self.Clear()

    def Clear(self):
        self._canvas = Image.new("RGB", (self.display_width, self.display_height), (0, 0, 0))
        self._send_full_frame(self._canvas)

    def ScreenOff(self):
        self.SetBrightness(0)

    def ScreenOn(self):
        self.SetBrightness(self.brightness if self.brightness > 0 else 100)

    def SetBrightness(self, level: int):
        self.brightness = max(0, min(100, int(level)))
        cmd = bytes([0xAA, 0xBB, self.brightness, 0xCC, 0xDD])
        if self.update_queue:
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [cmd]))
        else:
            self.WriteData(cmd)

    def SetOrientation(self, orientation: Orientation):
        self.orientation = orientation

    def DisplayPILImage(
            self,
            image: Image.Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
    ):
        if image_width != 0 and image_height != 0 and (image.size[0] != image_width or image.size[1] != image_height):
            image = image.resize((image_width, image_height))

        # Check if full frame matching current orientation
        target_w = self.get_width()
        target_h = self.get_height()

        if x == 0 and y == 0 and image.size == (target_w, target_h):
            # Direct full frame
            frame = self._orient_image(image)
            self._send_full_frame(frame)
        else:
            # Partial update onto canvas
            if self.orientation in (Orientation.LANDSCAPE, Orientation.REVERSE_LANDSCAPE):
                # In landscape logical coordinates
                if not hasattr(self, "_logical_canvas") or self._logical_canvas.size != (target_w, target_h):
                    self._logical_canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
                self._logical_canvas.paste(image, (x, y))
                frame = self._orient_image(self._logical_canvas)
                self._send_full_frame(frame)
            else:
                # In portrait logical coordinates
                self._canvas.paste(image, (x, y))
                frame = self._orient_image(self._canvas)
                self._send_full_frame(frame)

    def _orient_image(self, img: Image.Image) -> Image.Image:
        """Transforms logical image to match physical portrait panel (width x height)."""
        if self.orientation == Orientation.PORTRAIT:
            if img.size != (self.display_width, self.display_height):
                img = img.resize((self.display_width, self.display_height))
            return img
        elif self.orientation == Orientation.REVERSE_PORTRAIT:
            if img.size != (self.display_width, self.display_height):
                img = img.resize((self.display_width, self.display_height))
            return img.rotate(180)
        elif self.orientation == Orientation.LANDSCAPE:
            # Logical is (display_height, display_width), e.g. (1920, 462)
            # Physical panel is (display_width, display_height), e.g. (462, 1920)
            if img.size != (self.display_height, self.display_width):
                img = img.resize((self.display_height, self.display_width))
            return img.rotate(90, expand=True)
        elif self.orientation == Orientation.REVERSE_LANDSCAPE:
            if img.size != (self.display_height, self.display_width):
                img = img.resize((self.display_height, self.display_width))
            return img.rotate(270, expand=True)
        return img

    def _send_full_frame(self, img: Image.Image):
        # Convert to RGB and encode as high quality JPEG
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        jpeg_bytes = buf.getvalue()

        if self.update_queue:
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [jpeg_bytes]))
        else:
            self.WriteData(jpeg_bytes)
