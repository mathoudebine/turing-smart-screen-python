# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Rev. A over raw USB bulk transfers (PyUSB/libusb) instead of the serial device.
#
# On macOS, sending through the CDC serial device (/dev/cu.usbmodem...) corrupts images on Turing / UsbMonitor
# 3.5" units (1a86:5722): the panel firmware works per USB transfer/packet, and the macOS serial path re-packs the
# byte stream. Writing directly to the bulk OUT endpoint, as the vendor Windows app does, draws correctly.
# Approach from issue #7 (findings by marcelors27 and amarok30).
#
# Observed on a 1a86:5722 unit: the firmware handles pixel data per 64-byte USB packet. A short packet is drawn
# padded with stale bytes, and the zero-length packet macOS sends after a write that is a multiple of 64 bytes is
# drawn as a duplicate. So every command goes in its own transfer, and bitmaps are widened to the 32-px grid
# (from a framebuffer copy of the screen) so pixel data is always whole 64-byte packets and exactly w*h*2 bytes.
#
# On macOS, detaching the kernel CDC driver needs root, but claiming the data interface works without it.
# Requires libusb (e.g. `brew install libusb`) and pyusb (already in requirements.txt).

import time
from typing import Optional

import usb.core
import usb.util

from library.lcd.lcd_comm import *
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Command
from library.lcd.serialize import image_to_RGB565
from library.log import logger

VID, PID = 0x1A86, 0x5722
INTERFACE = 1  # CDC data interface
OUT_EP = 0x03
IN_EP = 0x82
CHUNK = 4096  # multiple of 64


class LcdCommRevAUsb(LcdCommRevA):
    PACKET_PIXELS = 32  # 64-byte USB packet = 32 RGB565 pixels

    def __init__(self, display_width: int = 320, display_height: int = 480,
                 update_queue: Optional[queue.Queue] = None):
        self.usb_dev = None
        self._framebuffer = None  # copy of the screen contents, used to widen updates to the 32-px grid
        LcdCommRevA.__init__(self, "AUTO", display_width, display_height, update_queue)

    def __del__(self):
        self.closeSerial()

    # --- transport: USB bulk instead of pyserial ---

    def openSerial(self):
        dev = usb.core.find(idVendor=VID, idProduct=PID)
        if dev is None:
            raise IOError("Rev. A display not found on USB (1a86:5722)")
        try:
            if dev.is_kernel_driver_active(INTERFACE):
                dev.detach_kernel_driver(INTERFACE)
        except (usb.core.USBError, NotImplementedError):
            pass  # macOS needs root to detach, but claiming still works with the serial driver attached
        usb.util.claim_interface(dev, INTERFACE)
        self.usb_dev = dev
        logger.info(f"Display connected via USB bulk endpoint 0x{OUT_EP:02x}")

    def closeSerial(self):
        if self.usb_dev is not None:
            try:
                usb.util.release_interface(self.usb_dev, INTERFACE)
                try:
                    self.usb_dev.attach_kernel_driver(INTERFACE)
                except (usb.core.USBError, NotImplementedError):
                    pass
                usb.util.dispose_resources(self.usb_dev)
            except usb.core.USBError:
                pass
            self.usb_dev = None

    def serial_write(self, data: bytes):
        assert self.usb_dev is not None
        self.usb_dev.write(OUT_EP, data, timeout=10000)  # one call = one USB transfer

    def serial_read(self, size: int) -> bytes:
        assert self.usb_dev is not None
        try:
            return bytes(self.usb_dev.read(IN_EP, size, timeout=500))
        except usb.core.USBTimeoutError:
            return b""

    def serial_flush_input(self):
        try:
            while True:
                self.usb_dev.read(IN_EP, 64, timeout=50)
        except usb.core.USBError:
            pass

    def WriteLine(self, line: bytes):
        try:
            self.serial_write(line)
        except usb.core.USBError as e:
            logger.error(f"USB write failed ({e}): reopening the device and retrying once")
            self.closeSerial()
            time.sleep(1)
            self.openSerial()
            self.serial_write(line)

    # --- commands ---

    def Reset(self):
        # Not sent over USB bulk: once the panel's pixel counter is out of sync it swallows commands (RESET included)
        # as pixel data, so a reset cannot recover it. Unplugging / replugging the display does.
        logger.info("USB bulk transport: skipping display reset (unplug/replug the display to recover it)")

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        self.orientation = orientation
        width, height = self.get_width(), self.get_height()
        buf = bytearray(11)  # 6-byte command + orientation + width/height (big-endian)
        buf[5] = Command.SET_ORIENTATION
        buf[6] = orientation + 100
        buf[7], buf[8] = width >> 8, width & 255
        buf[9], buf[10] = height >> 8, height & 255
        self.WriteData(buf)
        self._framebuffer = Image.new("RGB", (width, height), (0, 0, 0))

    def DisplayPILImage(self, image: Image.Image, x: int = 0, y: int = 0, image_width: int = 0,
                        image_height: int = 0):
        width, height = self.get_width(), self.get_height()
        if not image_height:
            image_height = image.size[1]
        if not image_width:
            image_width = image.size[0]
        if x + image_width > width:
            image_width = width - x
        if y + image_height > height:
            image_height = height - y
        if image_width != image.size[0] or image_height != image.size[1]:
            image = image.crop((0, 0, image_width, image_height))
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'

        if self._framebuffer is None or self._framebuffer.size != (width, height):
            self._framebuffer = Image.new("RGB", (width, height), (0, 0, 0))
        self._framebuffer.paste(image.convert("RGB"), (x, y))

        # Widen to whole 32-px blocks so the pixel data is whole 64-byte packets
        p = self.PACKET_PIXELS
        ax0 = (x // p) * p
        ax1 = min(-(-(x + image_width) // p) * p, width)
        y1 = y + image_height
        data = image_to_RGB565(self._framebuffer.crop((ax0, y, ax1, y1)), "little")

        header = bytearray(6)
        header[0] = ax0 >> 2
        header[1] = ((ax0 & 3) << 6) + (y >> 4)
        header[2] = ((y & 15) << 4) + ((ax1 - 1) >> 6)
        header[3] = (((ax1 - 1) & 63) << 2) + ((y1 - 1) >> 8)
        header[4] = (y1 - 1) & 255
        header[5] = Command.DISPLAY_BITMAP

        # Header and pixel data are queued together so nothing else is sent while the bitmap is in progress
        if self.update_queue:
            with self.update_queue_mutex:
                self.update_queue.put((self._send_bitmap, [bytes(header), data]))
        else:
            self._send_bitmap(bytes(header), data)

    def _send_bitmap(self, header: bytes, data: bytes):
        self.WriteLine(header)
        time.sleep(0.010)  # the vendor app pauses 10 ms between the header and the pixel data
        for i in range(0, len(data), CHUNK):
            self.WriteLine(data[i:i + CHUNK])
