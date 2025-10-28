from io import BytesIO
from PIL import Image
import usb.core
import usb.util
import struct
import time
import argparse
from Crypto.Cipher import DES
from PIL import Image
import time
import subprocess
from pathlib import Path
import platform
from library.lcd.lcd_comm import Orientation, LcdComm
from library.lcd.serialize import image_to_BGRA, image_to_BGR, chunked
from library.log import logger
from typing import Optional, Tuple
import queue

VENDOR_ID = 0x1cbe
PRODUCT_ID = 0x0088

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
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        raise ValueError('USB device not found')

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
                #print("Flush read error:", e)
                break

def write_to_device(dev, data, timeout=2000):
    cfg = dev.get_active_configuration()
    intf = usb.util.find_descriptor(cfg, bInterfaceNumber=0)
    if intf is None:
        raise RuntimeError("USB interface 0 not found")
    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
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
    img_data = bytearray([
        0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x01, 0xe0, 0x00, 0x00, 0x07, 0x80, 0x08, 0x06, 0x00, 0x00, 0x00, 0x16, 0xf0, 0x84,
        0xf5, 0x00, 0x00, 0x00, 0x01, 0x73, 0x52, 0x47, 0x42, 0x00, 0xae, 0xce, 0x1c, 0xe9, 0x00, 0x00,
        0x00, 0x04, 0x67, 0x41, 0x4d, 0x41, 0x00, 0x00, 0xb1, 0x8f, 0x0b, 0xfc, 0x61, 0x05, 0x00, 0x00,
        0x00, 0x09, 0x70, 0x48, 0x59, 0x73, 0x00, 0x00, 0x0e, 0xc3, 0x00, 0x00, 0x0e, 0xc3, 0x01, 0xc7,
        0x6f, 0xa8, 0x64, 0x00, 0x00, 0x0e, 0x0c, 0x49, 0x44, 0x41, 0x54, 0x78, 0x5e, 0xed, 0xc1, 0x01,
        0x0d, 0x00, 0x00, 0x00, 0xc2, 0xa0, 0xf7, 0x4f, 0x6d, 0x0f, 0x07, 0x14, 0x00, 0x00, 0x00, 0x00,
    ] + [0x00] * 3568 + [
        0x00, 0xf0, 0x66, 0x4a, 0xc8, 0x00, 0x01, 0x11, 0x9d, 0x82, 0x0a, 0x00, 0x00, 0x00, 0x00, 0x49,
        0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82
    ])
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

    cmd = [
        "ffmpeg",
        "-y",  # overwrite without asking
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
    send_brightness_command(dev, 32) #14
    write_to_device(dev, encrypt_command_packet(build_command_packet_header(41)))
    clear_image(dev) #102, 3703
    send_frame_rate_command(dev, 25) #15
    # send_image(dev, './102_25011_payload.png') #102, 25011
    print("Sending Send Video Command (ID 121)...")
    try:
        while(True):
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

class LcdCommRevCUSB(LcdComm):
    def __init__(self, com_port: str = "USB", display_width: int = 480, display_height: int = 1920,
                 update_queue: Optional[queue.Queue] = None):
        super().__init__(com_port, display_width, display_height, update_queue)
        self.dev = find_usb_device()
        self.image_parts = {}
    
    def auto_detect_com_port(self):
        pass

    def InitializeComm(self):
        send_sync_command(self.dev)

    def Reset(self):
        # send_restart_device_command(self.dev)
        pass

    def Clear(self):
        clear_image(self.dev)

    def ScreenOff(self):
        pass

    def ScreenOn(self):
        pass

    def SetBrightness(self, level: int):
        assert 0 <= level <= 100, 'Brightness must be 0~100'
        converted = int(level / 100 * 102)
        send_brightness_command(self.dev, converted)

    def SetOrientation(self, orientation: Orientation):
        self.orientation = orientation

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

        self.image_parts[(x, y)] = image
        base_image = Image.new("RGBA", (self.get_width(), self.get_height()), (0, 0, 0, 0))

        for (x, y), part in self.image_parts.items():
            base_image.paste(part, (x, y))

        if self.orientation == Orientation.LANDSCAPE:
            base_image = base_image.transpose(Image.Transpose.ROTATE_270)
        elif self.orientation == Orientation.REVERSE_LANDSCAPE:
            base_image = base_image.transpose(Image.Transpose.ROTATE_90)
        elif self.orientation == Orientation.PORTRAIT:
            base_image = base_image.transpose(Image.Transpose.ROTATE_180)
        elif self.orientation == Orientation.REVERSE_PORTRAIT:
            pass

        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        png_data = buffer.getvalue()

        send_image(self.dev, png_data)
