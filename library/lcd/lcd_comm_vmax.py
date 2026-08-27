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
import threading
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
        self._canvas_lock = threading.Lock()
        self._canvas = Image.new("RGB", (self.display_width, self.display_height), (0, 0, 0))
        self._frame_pending = False
        self._serial_lock = threading.Lock()

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
        with self._serial_lock:
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
                    self.lcd_serial = serial.Serial(
                        com_port,
                        115200,
                        timeout=1.0,
                        write_timeout=1.0,
                        rtscts=False,
                        dsrdtr=False
                    )
                    time.sleep(0.05)
                    try:
                        self.lcd_serial.reset_input_buffer()
                        self.lcd_serial.reset_output_buffer()
                    except Exception:
                        pass
                    return
                except Exception as e:
                    logger.warning(f"Cannot open COM port {com_port}: {e} - retrying ({attempt}/10)")
                    time.sleep(1)

    def InitializeComm(self):
        with self._serial_lock:
            logger.debug("Initializing HL-VMAX communication...")
            try:
                if self.lcd_serial and self.lcd_serial.is_open:
                    try:
                        self.lcd_serial.reset_input_buffer()
                    except Exception:
                        pass
                    self.lcd_serial.write(HANDSHAKE)
                    raw = self.lcd_serial.read(SN_LEN)
                    if len(raw) == SN_LEN:
                        self.serial_number = raw.decode("ascii", errors="replace").strip()
                        logger.info(f"Connected to HL-VMAX screen, Serial Number: {self.serial_number}")
                        self._parse_geometry(self.serial_number)
                    else:
                        logger.debug(f"Handshake response length: {len(raw)} bytes")
            except Exception as e:
                logger.warning(f"HL-VMAX handshake info: {e}")

    def _parse_geometry(self, sn: str):
        # Format example: VMAXD160462*1920S262001750 or VMAXA170320*1480S261001155
        m = re.search(r"(\d{3,4})\s*\*\s*(\d{2,5})", sn)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            if w >= 100 and h >= 100:
                logger.info(f"Detected hardware panel geometry: {w}x{h}")
                self.display_width = w
                self.display_height = h
                with self._canvas_lock:
                    target_w = self.get_width()
                    target_h = self.get_height()
                    self._canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))

    def Reset(self):
        with self._serial_lock:
            if self.lcd_serial and self.lcd_serial.is_open:
                try:
                    self.lcd_serial.reset_input_buffer()
                except Exception:
                    pass
        self.Clear()

    def Clear(self):
        with self._canvas_lock:
            target_w = self.get_width()
            target_h = self.get_height()
            self._canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        self._enqueue_render()

    def ScreenOff(self):
        self.SetBrightness(0)

    def ScreenOn(self):
        self.SetBrightness(self.brightness if self.brightness > 0 else 100)

    def SetBrightness(self, level: int):
        self.brightness = max(0, min(100, int(level)))
        cmd = bytes([0xAA, 0xBB, self.brightness, 0xCC, 0xDD])
        if self.update_queue:
            with self.update_queue_mutex:
                self.update_queue.put((self._send_brightness_direct, [cmd]))
        else:
            self._send_brightness_direct(cmd)

    def _send_brightness_direct(self, cmd: bytes):
        with self._serial_lock:
            try:
                if self.lcd_serial and self.lcd_serial.is_open:
                    self.lcd_serial.write(cmd)
            except Exception as e:
                logger.warning(f"Failed to send brightness command: {e}")

    def SetOrientation(self, orientation: Orientation):
        self.orientation = orientation
        with self._canvas_lock:
            target_w = self.get_width()
            target_h = self.get_height()
            self._canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))

    def DisplayPILImage(
            self,
            image: Image.Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
    ):
        if image_width != 0 and image_height != 0 and (image.size[0] != image_width or image.size[1] != image_height):
            image = image.resize((image_width, image_height))

        target_w = self.get_width()
        target_h = self.get_height()

        with self._canvas_lock:
            if self._canvas.size != (target_w, target_h):
                self._canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))

            if x == 0 and y == 0 and image.size == (target_w, target_h):
                self._canvas.paste(image, (0, 0))
            else:
                self._canvas.paste(image, (x, y))

        self._enqueue_render()

    def _enqueue_render(self):
        if self.update_queue:
            with self.update_queue_mutex:
                if not self._frame_pending:
                    self._frame_pending = True
                    self.update_queue.put((self._render_and_send_frame, []))
        else:
            self._render_and_send_frame()

    def _render_and_send_frame(self):
        with self.update_queue_mutex:
            self._frame_pending = False

        with self._canvas_lock:
            frame_to_send = self._orient_image(self._canvas.copy())

        if frame_to_send.mode != "RGB":
            frame_to_send = frame_to_send.convert("RGB")

        buf = io.BytesIO()
        frame_to_send.save(buf, format="JPEG", quality=88)
        jpeg_bytes = buf.getvalue()

        with self._serial_lock:
            try:
                if self.lcd_serial and self.lcd_serial.is_open:
                    self.lcd_serial.write(jpeg_bytes)
                    self.lcd_serial.flush()
            except Exception as e:
                logger.warning(f"Failed to send frame to HL-VMAX: {e}")

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
            if img.size != (self.display_height, self.display_width):
                img = img.resize((self.display_height, self.display_width))
            return img.rotate(270, expand=True)
        elif self.orientation == Orientation.REVERSE_LANDSCAPE:
            if img.size != (self.display_height, self.display_width):
                img = img.resize((self.display_height, self.display_width))
            return img.rotate(90, expand=True)
        return img
