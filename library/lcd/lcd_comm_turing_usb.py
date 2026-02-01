# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
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

import math
import platform
import queue
import struct
import subprocess
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

import usb.core
import usb.util
from Crypto.Cipher import DES
from PIL import Image

from library.log import logger
from library.lcd.lcd_comm import Orientation, LcdComm

VENDOR_ID = 0x1cbe
PRODUCT_ID = [0x0088, 0x0092]   # 8.8", 9.2"


MAX_CHUNK_BYTES = 1024*1024  # Data sent to screen cannot exceed 1024MB or there will be a timeout


def build_command_packet_header(a0: int) -> bytearray:
    packet = bytearray(500)
    packet[0] = a0
    packet[2] = 0x1A
    packet[3] = 0x6D
    timestamp = int((time.time() - time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))) * 1000)
    packet[4:8] = struct.pack('<I', timestamp)
    return packet


def encrypt_with_des(key: bytes, data: bytes) -> bytes:
    cipher = DES.new(key, DES.MODE_CBC, key)
    padded_len = (len(data) + 7) // 8 * 8
    padded_data = data.ljust(padded_len, b'\x00')
    return cipher.encrypt(padded_data)


def encrypt_command_packet(data: bytearray) -> bytearray:
    des_key = b'slv3tuzx'
    encrypted = encrypt_with_des(des_key, data)
    final_packet = bytearray(512)
    final_packet[:len(encrypted)] = encrypted
    final_packet[510] = 161
    final_packet[511] = 26
    return final_packet


def find_usb_device():
    for pid in PRODUCT_ID:
        dev = usb.core.find(idVendor=VENDOR_ID, idProduct=pid)
    if dev is None:
        raise ValueError(f'USB device not found')
    

    try:
        dev.set_configuration()
    except usb.core.USBError as e:
        print("Warning: set_configuration() failed:", e)

    if platform.system() == "Linux":
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
        except usb.core.USBError as e:
            print("Warning: detach_kernel_driver failed:", e)

    return dev


def read_flush(ep_in, max_attempts=5):
    """
    Flush the USB IN endpoint by reading available data until timeout or max attempts reached.
    """
    for _ in range(max_attempts):
        try:
            ep_in.read(512, timeout=100)
        except usb.core.USBError as e:
            if e.errno == 110 or e.args[0] == 'Operation timed out':
                break
            else:
                # print("Flush read error:", e)
                break


def write_to_device(dev, data, timeout=2000):
    cfg = dev.get_active_configuration()
    intf = usb.util.find_descriptor(cfg, bInterfaceNumber=0)
    if intf is None:
        raise RuntimeError("USB interface 0 not found")
    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(
        e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(
        e.bEndpointAddress) == usb.util.ENDPOINT_IN)
    assert ep_out is not None and ep_in is not None, "Could not find USB endpoints"

    try:
        ep_out.write(data, timeout)
    except usb.core.USBError as e:
        print("USB write error:", e)
        return None

    try:
        response = ep_in.read(512, timeout)
        read_flush(ep_in)
        return bytes(response)
    except usb.core.USBError as e:
        print("USB read error:", e)
        return None


def delay_sync(dev):
    send_sync_command(dev)
    time.sleep(0.2)


def send_sync_command(dev):
    print("Sending Sync Command (ID 10)...")
    cmd_packet = build_command_packet_header(10)
    return write_to_device(dev, encrypt_command_packet(cmd_packet))


def send_restart_device_command(dev):
    print("Sending Restart Command (ID 11)...")
    return write_to_device(dev, encrypt_command_packet(build_command_packet_header(11)))


def send_brightness_command(dev, brightness: int):
    print(f"Sending Brightness Command (ID 14)...")
    print(f"  Brightness = {brightness}")
    cmd_packet = build_command_packet_header(14)
    cmd_packet[8] = brightness
    return write_to_device(dev, encrypt_command_packet(cmd_packet))


def send_frame_rate_command(dev, frame_rate: int):
    print(f"Sending Frame Rate Command (ID 15)...")
    print(f"  Frame Rate = {frame_rate}")
    cmd_packet = build_command_packet_header(15)
    cmd_packet[8] = frame_rate
    return write_to_device(dev, encrypt_command_packet(cmd_packet))


def format_bytes(val):
    if val > 1024 * 1024:
        return f"{val / (1024 * 1024):.2f} GB"
    else:
        return f"{val / 1024:.2f} MB"


def send_refresh_storage_command(dev):
    print("Sending Refresh Storage Command (ID 100)...")
    response = write_to_device(dev, encrypt_command_packet(build_command_packet_header(100)))

    total = format_bytes(int.from_bytes(response[8:12], byteorder='little'))
    used = format_bytes(int.from_bytes(response[12:16], byteorder='little'))
    valid = format_bytes(int.from_bytes(response[16:20], byteorder='little'))

    print(f"  Card Total = {total}")
    print(f"  Card Used = {used}")
    print(f"  Card Valid = {valid}")


def send_save_settings_command(dev, brightness=0, startup=0, reserved=0, rotation=0, sleep=0, offline=0):
    print("Sending Save Settings Command (ID 125)...")
    print(f"  Brightness:     {brightness}")
    print(f"  Startup Mode:   {startup}")
    print(f"  Reserved:       {reserved}")
    print(f"  Rotation:       {rotation}")
    print(f"  Sleep Timeout:  {sleep}")
    print(f"  Offline Mode:   {offline}")
    cmd_packet = build_command_packet_header(125)
    cmd_packet[8] = brightness
    cmd_packet[9] = startup
    cmd_packet[10] = reserved
    cmd_packet[11] = rotation
    cmd_packet[12] = sleep
    cmd_packet[13] = offline
    return write_to_device(dev, encrypt_command_packet(cmd_packet))


def send_image(dev, png_data: bytes):
    img_size = len(png_data)

    cmd_packet = build_command_packet_header(102)
    cmd_packet[8] = (img_size >> 24) & 0xFF
    cmd_packet[9] = (img_size >> 16) & 0xFF
    cmd_packet[10] = (img_size >> 8) & 0xFF
    cmd_packet[11] = img_size & 0xFF

    full_payload = encrypt_command_packet(cmd_packet) + png_data
    return write_to_device(dev, full_payload)


def clear_image(dev):
    img_data = bytearray(
        [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52, 0x00, 0x00,
            0x01, 0xe0, 0x00, 0x00, 0x07, 0x80, 0x08, 0x06, 0x00, 0x00, 0x00, 0x16, 0xf0, 0x84, 0xf5, 0x00, 0x00, 0x00,
            0x01, 0x73, 0x52, 0x47, 0x42, 0x00, 0xae, 0xce, 0x1c, 0xe9, 0x00, 0x00, 0x00, 0x04, 0x67, 0x41, 0x4d, 0x41,
            0x00, 0x00, 0xb1, 0x8f, 0x0b, 0xfc, 0x61, 0x05, 0x00, 0x00, 0x00, 0x09, 0x70, 0x48, 0x59, 0x73, 0x00, 0x00,
            0x0e, 0xc3, 0x00, 0x00, 0x0e, 0xc3, 0x01, 0xc7, 0x6f, 0xa8, 0x64, 0x00, 0x00, 0x0e, 0x0c, 0x49, 0x44, 0x41,
            0x54, 0x78, 0x5e, 0xed, 0xc1, 0x01, 0x0d, 0x00, 0x00, 0x00, 0xc2, 0xa0, 0xf7, 0x4f, 0x6d, 0x0f, 0x07, 0x14,
            0x00, 0x00, 0x00, 0x00, ] + [0x00] * 3568 + [0x00, 0xf0, 0x66, 0x4a, 0xc8, 0x00, 0x01, 0x11, 0x9d, 0x82,
            0x0a, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82])
    img_size = len(img_data)
    print(f"  Chunk Size: {img_size} bytes")

    cmd_packet = build_command_packet_header(102)
    cmd_packet[8] = (img_size >> 24) & 0xFF
    cmd_packet[9] = (img_size >> 16) & 0xFF
    cmd_packet[10] = (img_size >> 8) & 0xFF
    cmd_packet[11] = img_size & 0xFF

    full_payload = encrypt_command_packet(cmd_packet) + img_data
    return write_to_device(dev, full_payload)


def delay(dev, rst):
    time.sleep(0.05)
    print("Sending Delay Command (ID 122)...")
    cmd_packet = build_command_packet_header(122)
    response = write_to_device(dev, encrypt_command_packet(cmd_packet))
    if response and response[8] > rst:
        delay(dev, rst)


def extract_h264_from_mp4(mp4_path: str):
    input_path = Path(mp4_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = input_path.with_suffix(".h264")

    if output_path.exists():
        print(f"{output_path.name} already exists. Skipping extraction.")
        return output_path

    cmd = ["ffmpeg", "-y",  # overwrite without asking
        "-i", str(input_path),  # input file
        "-c:v", "copy",  # copy video stream
        "-bsf:v", "h264_mp4toannexb",  # convert to Annex-B
        "-an",  # remove audio
        "-f", "h264",  # set output format
        str(output_path)  # output file
    ]

    print(f"Extracting H.264 from {input_path.name}...")
    subprocess.run(cmd, check=True)
    print(f"Done. Saved as {output_path.name}")
    return output_path


def send_video(dev, video_path, loop=False):
    output_path = extract_h264_from_mp4(video_path)
    write_to_device(dev, encrypt_command_packet(build_command_packet_header(111)))
    write_to_device(dev, encrypt_command_packet(build_command_packet_header(112)))
    write_to_device(dev, encrypt_command_packet(build_command_packet_header(13)))
    send_brightness_command(dev, 32)  # 14
    write_to_device(dev, encrypt_command_packet(build_command_packet_header(41)))
    clear_image(dev)  # 102, 3703
    send_frame_rate_command(dev, 25)  # 15
    # send_image(dev, './102_25011_payload.png') #102, 25011
    print("Sending Send Video Command (ID 121)...")
    try:
        while (True):
            with open(output_path, 'rb') as f:
                while True:
                    data = f.read(202752)
                    chunksize = len(data)
                    if not data:
                        break
                    print(f"  Chunk Size: {chunksize} bytes")

                    cmd_packet = build_command_packet_header(121)
                    cmd_packet[8] = (chunksize >> 24) & 0xFF
                    cmd_packet[9] = (chunksize >> 16) & 0xFF
                    cmd_packet[10] = (chunksize >> 8) & 0xFF
                    cmd_packet[11] = chunksize & 0xFF

                    full_payload = encrypt_command_packet(cmd_packet) + data
                    response = write_to_device(dev, full_payload)
                    time.sleep(0.03)
                    if response is None or len(response) < 9 or response[8] <= 3:
                        delay(dev, 2)
                print("Video sent successfully.")
            if not loop:
                break
    except KeyboardInterrupt:
        print("\nLoop interrupted by user. Sending reset...")
    finally:
        write_to_device(dev, encrypt_command_packet(build_command_packet_header(123)))


def _encode_png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


def compress_image(image: Image.Image, ratio: float) -> Image.Image:
    width, height = image.size
    image = image.resize((int(width * ratio*0.5), int(height * ratio*0.5)),
                                   resample=Image.Resampling.LANCZOS)
    image = image.resize((width, height))
    return image



def upload_file(dev, file_path: str) -> bool:
    local_path = Path(file_path)
    if not local_path.exists():
        logger.error("Error: File does not exist: %s", file_path)
        return False

    ext = local_path.suffix.lower()
    if ext == ".png":
        device_path = f"/tmp/sdcard/mmcblk0p1/img/{local_path.name}"
        logger.info("Uploading PNG: %s → %s", file_path, device_path)
    elif ext == ".mp4":
        h264_path = extract_h264_from_mp4(file_path)
        device_path = f"/tmp/sdcard/mmcblk0p1/video/{h264_path.name}"
        local_path = h264_path  # Update local path to .h264
        logger.info("Uploading MP4 as H264: %s → %s", local_path, device_path)
    else:
        logger.error("Error: Unsupported file type. Only .png and .mp4 are allowed.")
        return False

    if not _open_file_command(dev, device_path):
        logger.error("Failed to open remote file for writing.")
        return False

    if not _write_file_command(dev, str(local_path)):
        logger.error("Failed to write file data.")
        return False

    logger.info("Upload completed successfully.")
    return True


def _open_file_command(dev, path: str):
    logger.info("Opening remote file: %s", path)

    path_bytes = path.encode("ascii")
    length = len(path_bytes)

    packet = build_command_packet_header(38)

    packet[8] = (length >> 24) & 0xFF
    packet[9] = (length >> 16) & 0xFF
    packet[10] = (length >> 8) & 0xFF
    packet[11] = length & 0xFF
    packet[12:16] = b"\x00\x00\x00\x00"
    packet[16 : 16 + length] = path_bytes

    return write_to_device(dev, encrypt_command_packet(packet))


def _delete_command(dev, file_path: str):
    logger.info("Deleting remote file: %s", file_path)

    path_bytes = file_path.encode("ascii")
    length = len(path_bytes)

    packet = build_command_packet_header(40)
    packet[8] = (length >> 24) & 0xFF
    packet[9] = (length >> 16) & 0xFF
    packet[10] = (length >> 8) & 0xFF
    packet[11] = length & 0xFF
    packet[12:16] = b"\x00\x00\x00\x00"
    packet[16 : 16 + length] = path_bytes

    return write_to_device(dev, encrypt_command_packet(packet))


def _play_command(dev, file_path: str):
    logger.info("Requesting playback for: %s", file_path)

    path_bytes = file_path.encode("ascii")
    length = len(path_bytes)

    packet = build_command_packet_header(98)

    packet[8] = (length >> 24) & 0xFF
    packet[9] = (length >> 16) & 0xFF
    packet[10] = (length >> 8) & 0xFF
    packet[11] = length & 0xFF
    packet[12:16] = b"\x00\x00\x00\x00"
    packet[16 : 16 + length] = path_bytes

    return write_to_device(dev, encrypt_command_packet(packet))


def _play2_command(dev, file_path: str):
    logger.info("Requesting alternate playback for: %s", file_path)

    path_bytes = file_path.encode("ascii")
    length = len(path_bytes)

    packet = build_command_packet_header(110)

    packet[8] = (length >> 24) & 0xFF
    packet[9] = (length >> 16) & 0xFF
    packet[10] = (length >> 8) & 0xFF
    packet[11] = length & 0xFF
    packet[12:16] = b"\x00\x00\x00\x00"
    packet[16 : 16 + length] = path_bytes

    return write_to_device(dev, encrypt_command_packet(packet))


def _play3_command(dev, file_path: str):
    logger.info("Requesting image playback for: %s", file_path)

    path_bytes = file_path.encode("ascii")
    length = len(path_bytes)

    packet = build_command_packet_header(113)

    packet[8] = (length >> 24) & 0xFF
    packet[9] = (length >> 16) & 0xFF
    packet[10] = (length >> 8) & 0xFF
    packet[11] = length & 0xFF
    packet[12:16] = b"\x00\x00\x00\x00"
    packet[16 : 16 + length] = path_bytes

    return write_to_device(dev, encrypt_command_packet(packet))


def _write_file_command(dev, file_path: str) -> bool:
    logger.info("Writing remote file from: %s", file_path)

    try:
        with open(file_path, "rb") as fh:
            chunk_index = 0
            while True:
                data_chunk = fh.read(202752)
                if not data_chunk:
                    break

                chunk_size = len(data_chunk)
                chunk_index += 1
                logger.debug("Chunk %d size: %d bytes", chunk_index, chunk_size)

                cmd_packet = build_command_packet_header(39)
                cmd_packet[8] = (chunk_size >> 24) & 0xFF
                cmd_packet[9] = (chunk_size >> 16) & 0xFF
                cmd_packet[10] = (chunk_size >> 8) & 0xFF
                cmd_packet[11] = chunk_size & 0xFF

                response = write_to_device(dev, encrypt_command_packet(cmd_packet) + data_chunk)
                if response is None:
                    logger.error("Write command failed at chunk %d", chunk_index)
                    return False

        logger.info("File write completed successfully (%d chunks).", chunk_index)
        return True
    except FileNotFoundError:
        logger.error("File not found: %s", file_path)
        return False
    except Exception as exc:
        logger.error("Error writing file: %s", exc)
        return False

# This class is for Turing Smart Screen newer models (5.2" / 8" / 8.8" HW rev 1.x / 9.2")
# These models are not detected as serial ports but as (Win)USB devices
class LcdCommTuringUSB(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 480, display_height: int = 1920,
                 update_queue: Optional[queue.Queue] = None):
        super().__init__(com_port, display_width, display_height, update_queue)
        self.dev = find_usb_device()
        # Store the current screen state as an image that will be continuously updated and sent
        self.current_state = Image.new("RGBA", (self.get_width(), self.get_height()), (0, 0, 0, 0))

    def InitializeComm(self):
        send_sync_command(self.dev)

    def Reset(self):
        # Do not enable the reset command for now on Turing USB models
        # send_restart_device_command(self.dev)
        pass

    def Clear(self):
        clear_image(self.dev)

    def ScreenOff(self):
        # Turing USB models do not implement a "screen off" command (that we know of): use SetBrightness(0) instead
        self.Clear()
        self.SetBrightness(0)

    def ScreenOn(self):
        # Turing USB models do not implement a "screen off" command (that we know of): using SetBrightness() instead
        self.SetBrightness()

    def SetBrightness(self, level: int = 25):
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'
        converted = int(level / 100 * 102)
        send_brightness_command(self.dev, converted)

    def SetOrientation(self, orientation: Orientation):
        self.orientation = orientation
        # Recreate new state with correct width/height now that screen orientation has changed
        self.current_state = Image.new("RGBA", (self.get_width(), self.get_height()), (0, 0, 0, 0))

    def DisplayPILImage(self, image: Image.Image, x: int = 0, y: int = 0, image_width: int = 0, image_height: int = 0):
        if not image_height:
            image_height = image.size[1]
        if not image_width:
            image_width = image.size[0]

        if image.size[1] > self.get_height():
            image_height = self.get_height()
        if image.size[0] > self.get_width():
            image_width = self.get_width()

        if image_width != image.size[0] or image_height != image.size[1]:
            image = image.crop((0, 0, image_width, image_height))

        # Paste new image over existing screen state
        self.current_state.paste(image, (x, y))

        # Rotate image before sending to screen: all images sent to the screen are in portrait mode
        if self.orientation == Orientation.LANDSCAPE:
            base_image = self.current_state.transpose(Image.Transpose.ROTATE_270)
        elif self.orientation == Orientation.REVERSE_LANDSCAPE:
            base_image = self.current_state.transpose(Image.Transpose.ROTATE_90)
        elif self.orientation == Orientation.PORTRAIT:
            base_image = self.current_state.transpose(Image.Transpose.ROTATE_180)
        else:  # Orientation.REVERSE_PORTRAIT is initial screen orientation
            base_image = self.current_state

        # total_size = len(_encode_png(base_image))
        # print("total size =", total_size/1024)
        #
        # if total_size > 1024*1024:
        #
        #     # If bitmap is > 1024MB operation will timeout: compress it
        #     size_overflow = total_size - 1024*1024
        #     ratio = 1- (size_overflow / total_size)
        #     print("ratio = ", ratio)
        #
        #     base_image = compress_image(base_image, ratio)
        #
        #     new_size = len(_encode_png(base_image))
        #     print("new_size =", new_size/1024)


        # Send PNG data
        encoded = _encode_png(base_image)
        send_image(self.dev, encoded)
