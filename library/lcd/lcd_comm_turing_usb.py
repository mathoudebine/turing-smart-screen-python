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
import os
import platform
import queue
import struct
import shutil
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

# Command IDs used by the vendor protocol (subset)
CMD_UPLOAD_JPEG = 101
CMD_UPLOAD_PNG = 102
CMD_GET_H264_CHUNK_SIZE = 17
CMD_PLAY_H264_CHUNK = 121
CMD_GET_STREAM_STATUS = 122
CMD_STOP_STREAM = 123

# Default max payload for frame uploads (device/transport limit)
MAX_IMAGE_PAYLOAD_DEFAULT = MAX_CHUNK_BYTES

def _resp_ok(resp: Optional[bytes]) -> bool:
    if not resp:
        return False
    b1 = resp[1] if len(resp) > 1 else None
    b8 = resp[8] if len(resp) > 8 else None
    return (b1 == 0xC8) or (b8 == 0xC8)

def send_jpeg(dev, jpeg_data: bytes):
    img_size = len(jpeg_data)
    cmd_packet = build_command_packet_header(CMD_UPLOAD_JPEG)
    cmd_packet[8] = (img_size >> 24) & 0xFF
    cmd_packet[9] = (img_size >> 16) & 0xFF
    cmd_packet[10] = (img_size >> 8) & 0xFF
    cmd_packet[11] = img_size & 0xFF
    full_payload = encrypt_command_packet(cmd_packet) + jpeg_data
    return write_to_device(dev, full_payload)

def _encode_jpeg_under_limit(
    image: Image.Image,
    *,
    max_bytes: int,
    quality: int = 95,
    subsampling: int = -1,
) -> bytes:
    if subsampling not in (-1, 0, 1, 2):
        raise ValueError("subsampling must be one of: -1, 0, 1, 2")
    img = image
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")

    subs = (2, 1, 0) if subsampling == -1 else (subsampling,)
    best = b""
    for sub in subs:
        q = int(quality)
        while q >= 1:
            buf = BytesIO()
            try:
                img.save(
                    buf,
                    format="JPEG",
                    quality=q,
                    optimize=False,
                    progressive=False,
                    subsampling=sub,
                )
            except TypeError:
                img.save(buf, format="JPEG", quality=q, optimize=False, progressive=False)
            data = buf.getvalue()
            if not best or len(data) < len(best):
                best = data
            if len(data) <= max_bytes:
                return data
            q = q - 5 if q > 10 else q - 1

    raise RuntimeError(f"Could not transcode JPEG under max_bytes: {len(best)} > {max_bytes}")

def send_pil_image_auto(
    dev,
    image: Image.Image,
    *,
    max_bytes: int = MAX_IMAGE_PAYLOAD_DEFAULT,
) -> None:
    # First try PNG (preferred)
    png = _encode_png(image)
    if len(png) <= max_bytes:
        send_image(dev, png)
        return
    # Fallback to JPEG when over limit (default behavior)
    jpg = _encode_jpeg_under_limit(image, max_bytes=max_bytes, quality=90, subsampling=-1)
    send_jpeg(dev, jpg)

# ---- MP4 parsing + Annex-B extraction (pure Python fallback) ----
from dataclasses import dataclass
from typing import Iterable, Tuple, Set

def _u32be(b: bytes, off: int = 0) -> int:
    return int.from_bytes(b[off:off+4], "big", signed=False)

def _u64be(b: bytes, off: int = 0) -> int:
    return int.from_bytes(b[off:off+8], "big", signed=False)

def _iter_mp4_boxes(data: bytes, start: int, end: int) -> Iterable[tuple[bytes, int, int]]:
    i = start
    while i + 8 <= end:
        size = _u32be(data, i)
        typ = data[i+4:i+8]
        hdr = 8
        if size == 1:
            if i + 16 > end:
                break
            size = _u64be(data, i+8)
            hdr = 16
        elif size == 0:
            size = end - i
        if size < hdr:
            break
        j = i + int(size)
        if j > end:
            break
        yield typ, i + hdr, j
        i = j

def _mp4_find_box(data: bytes, start: int, end: int, typ: bytes) -> Optional[tuple[int, int]]:
    for t, ps, pe in _iter_mp4_boxes(data, start, end):
        if t == typ:
            return ps, pe
    return None

@dataclass
class _Mp4H264Track:
    nal_len_size: int
    sps_list: list[bytes]
    pps_list: list[bytes]
    sample_sizes: list[int]
    chunk_offsets: list[int]
    stsc: list[tuple[int, int, int]]  # (first_chunk, samples_per_chunk, sample_desc_idx)
    sync_samples: Optional[Set[int]]

def _mp4_parse_avcc(avcc: bytes) -> tuple[int, list[bytes], list[bytes]]:
    if len(avcc) < 7:
        raise ValueError("avcC too small")
    nal_len_size = (avcc[4] & 0x03) + 1
    num_sps = avcc[5] & 0x1F
    off = 6
    sps_list: list[bytes] = []
    for _ in range(num_sps):
        if off + 2 > len(avcc):
            raise ValueError("avcC truncated (SPS length)")
        n = int.from_bytes(avcc[off:off+2], "big")
        off += 2
        if off + n > len(avcc):
            raise ValueError("avcC truncated (SPS data)")
        sps_list.append(avcc[off:off+n])
        off += n
    if off + 1 > len(avcc):
        raise ValueError("avcC truncated (PPS count)")
    num_pps = avcc[off]
    off += 1
    pps_list: list[bytes] = []
    for _ in range(num_pps):
        if off + 2 > len(avcc):
            raise ValueError("avcC truncated (PPS length)")
        n = int.from_bytes(avcc[off:off+2], "big")
        off += 2
        if off + n > len(avcc):
            raise ValueError("avcC truncated (PPS data)")
        pps_list.append(avcc[off:off+n])
        off += n
    return nal_len_size, sps_list, pps_list

def _mp4_load_moov(path: str) -> bytes:
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.seek(0, os.SEEK_SET)
        while f.tell() + 8 <= file_size:
            off0 = f.tell()
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            size = _u32be(hdr, 0)
            typ = hdr[4:8]
            hdr_size = 8
            if size == 1:
                ext = f.read(8)
                if len(ext) < 8:
                    break
                size = _u64be(ext, 0)
                hdr_size = 16
            elif size == 0:
                size = file_size - off0
            if size < hdr_size:
                break
            payload_size = int(size) - hdr_size
            if typ == b"moov":
                return f.read(payload_size)
            f.seek(payload_size, os.SEEK_CUR)
    raise ValueError("MP4: moov box not found")

def _mp4_pick_h264_video_track(moov: bytes) -> _Mp4H264Track:
    moov_start = 0
    moov_end = len(moov)
    for t_trak, trak_ps, trak_pe in _iter_mp4_boxes(moov, moov_start, moov_end):
        if t_trak != b"trak":
            continue
        mdia = _mp4_find_box(moov, trak_ps, trak_pe, b"mdia")
        if mdia is None:
            continue
        mdia_ps, mdia_pe = mdia
        hdlr = _mp4_find_box(moov, mdia_ps, mdia_pe, b"hdlr")
        if hdlr is None:
            continue
        hdlr_ps, hdlr_pe = hdlr
        hdlr_payload = moov[hdlr_ps:hdlr_pe]
        if len(hdlr_payload) < 12 or hdlr_payload[8:12] != b"vide":
            continue

        minf = _mp4_find_box(moov, mdia_ps, mdia_pe, b"minf")
        if minf is None:
            continue
        stbl = _mp4_find_box(moov, minf[0], minf[1], b"stbl")
        if stbl is None:
            continue
        stbl_ps, stbl_pe = stbl

        stsd = _mp4_find_box(moov, stbl_ps, stbl_pe, b"stsd")
        stsz = _mp4_find_box(moov, stbl_ps, stbl_pe, b"stsz")
        stsc = _mp4_find_box(moov, stbl_ps, stbl_pe, b"stsc")
        stco = _mp4_find_box(moov, stbl_ps, stbl_pe, b"stco")
        co64 = _mp4_find_box(moov, stbl_ps, stbl_pe, b"co64")
        stss = _mp4_find_box(moov, stbl_ps, stbl_pe, b"stss")
        if stsd is None or stsz is None or stsc is None or (stco is None and co64 is None):
            continue

        stsd_payload = moov[stsd[0]:stsd[1]]
        if len(stsd_payload) < 8:
            continue
        entry_count = _u32be(stsd_payload, 4)
        off = 8
        found = False
        nal_len_size = 4
        sps_list: list[bytes] = []
        pps_list: list[bytes] = []
        for _ in range(entry_count):
            if off + 8 > len(stsd_payload):
                break
            ent_size = _u32be(stsd_payload, off)
            fmt = stsd_payload[off+4:off+8]
            ent_end = off + int(ent_size)
            if ent_size < 8 or ent_end > len(stsd_payload):
                break
            if fmt in (b"avc1", b"avc3"):
                child_start = off + 8 + 78
                if child_start < ent_end:
                    for t2, ps2, pe2 in _iter_mp4_boxes(stsd_payload, child_start, ent_end):
                        if t2 == b"avcC":
                            nal_len_size, sps_list, pps_list = _mp4_parse_avcc(stsd_payload[ps2:pe2])
                            found = True
                            break
            elif fmt in (b"hvc1", b"hev1"):
                raise ValueError("MP4 contains HEVC/H.265; device expects H.264")
            if found:
                break
            off = ent_end
        if not found:
            continue

        stsz_payload = moov[stsz[0]:stsz[1]]
        if len(stsz_payload) < 12:
            continue
        fixed_size = _u32be(stsz_payload, 4)
        sample_count = _u32be(stsz_payload, 8)
        sample_sizes: list[int] = []
        if fixed_size:
            sample_sizes = [int(fixed_size)] * int(sample_count)
        else:
            need = 12 + int(sample_count) * 4
            if len(stsz_payload) < need:
                continue
            off2 = 12
            for _ in range(int(sample_count)):
                sample_sizes.append(int(_u32be(stsz_payload, off2)))
                off2 += 4

        if stco is not None:
            stco_payload = moov[stco[0]:stco[1]]
            if len(stco_payload) < 8:
                continue
            n = _u32be(stco_payload, 4)
            need = 8 + int(n) * 4
            if len(stco_payload) < need:
                continue
            chunk_offsets = [int(_u32be(stco_payload, 8 + 4*i)) for i in range(int(n))]
        else:
            co64_payload = moov[co64[0]:co64[1]]  # type: ignore[index]
            if len(co64_payload) < 8:
                continue
            n = _u32be(co64_payload, 4)
            need = 8 + int(n) * 8
            if len(co64_payload) < need:
                continue
            chunk_offsets = [int(_u64be(co64_payload, 8 + 8*i)) for i in range(int(n))]

        stsc_payload = moov[stsc[0]:stsc[1]]
        if len(stsc_payload) < 8:
            continue
        n = _u32be(stsc_payload, 4)
        need = 8 + int(n) * 12
        if len(stsc_payload) < need:
            continue
        stsc_entries: list[tuple[int, int, int]] = []
        off3 = 8
        for _ in range(int(n)):
            first_chunk = int(_u32be(stsc_payload, off3))
            samples_per_chunk = int(_u32be(stsc_payload, off3+4))
            desc_idx = int(_u32be(stsc_payload, off3+8))
            stsc_entries.append((first_chunk, samples_per_chunk, desc_idx))
            off3 += 12
        stsc_entries.sort(key=lambda x: x[0])

        sync_samples: Optional[Set[int]] = None
        if stss is not None:
            stss_payload = moov[stss[0]:stss[1]]
            if len(stss_payload) >= 8:
                n2 = _u32be(stss_payload, 4)
                need = 8 + int(n2) * 4
                if len(stss_payload) >= need:
                    sync_samples = set(int(_u32be(stss_payload, 8 + 4*i)) for i in range(int(n2)))

        return _Mp4H264Track(
            nal_len_size=int(nal_len_size),
            sps_list=sps_list,
            pps_list=pps_list,
            sample_sizes=sample_sizes,
            chunk_offsets=chunk_offsets,
            stsc=stsc_entries,
            sync_samples=sync_samples,
        )

    raise ValueError("MP4: no H.264 video track found")

def _mp4_iter_sample_locations(track: _Mp4H264Track) -> Iterable[tuple[int, int, int]]:
    sizes = track.sample_sizes
    sample_idx0 = 0
    entries = track.stsc
    entry_idx = 0
    if not sizes:
        return
    for chunk_idx1, chunk_off in enumerate(track.chunk_offsets, start=1):
        while (entry_idx + 1) < len(entries) and chunk_idx1 >= entries[entry_idx + 1][0]:
            entry_idx += 1
        samples_per_chunk = entries[entry_idx][1]
        off = int(chunk_off)
        for _ in range(samples_per_chunk):
            if sample_idx0 >= len(sizes):
                return
            sz = int(sizes[sample_idx0])
            yield sample_idx0 + 1, off, sz
            off += sz
            sample_idx0 += 1

def _mp4_extract_h264_annexb(in_path: str, out_path: str, *, repeat_headers: bool = True) -> None:
    moov = _mp4_load_moov(in_path)
    track = _mp4_pick_h264_video_track(moov)
    start_code = b"\x00\x00\x00\x01"
    spspps = b"".join(start_code + s for s in track.sps_list) + b"".join(start_code + p for p in track.pps_list)
    if not spspps:
        raise ValueError("MP4: missing SPS/PPS in avcC")

    with open(in_path, "rb") as fin, open(out_path, "wb") as fout:
        fout.write(spspps)
        nls = int(track.nal_len_size)
        if nls not in (1,2,3,4):
            raise ValueError(f"MP4: unsupported NAL length size: {nls}")
        sync = track.sync_samples
        for sample_no, off, sz in _mp4_iter_sample_locations(track):
            if repeat_headers and sync is not None and sample_no in sync:
                fout.write(spspps)
            fin.seek(off, os.SEEK_SET)
            data = fin.read(sz)
            if len(data) != sz:
                raise ValueError("MP4: truncated sample read")
            pos = 0
            end = len(data)
            while pos + nls <= end:
                nal_len = int.from_bytes(data[pos:pos+nls], "big")
                pos += nls
                if nal_len <= 0:
                    continue
                if pos + nal_len > end:
                    raise ValueError("MP4: invalid NAL length in sample")
                fout.write(start_code)
                fout.write(data[pos:pos+nal_len])
                pos += nal_len



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
    if response and len(response) > 8 and response[8] > rst:
        delay(dev, rst)


def extract_h264_from_mp4(mp4_path: str):
    input_path = Path(mp4_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = input_path.with_suffix(".h264")
    if output_path.exists():
        print(f"{output_path.name} already exists. Skipping extraction.")
        return output_path

    # Prefer ffmpeg when available (fast + robust). Fall back to pure-Python MP4->Annex-B extraction.
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-c:v",
            "copy",
            "-bsf:v",
            "h264_mp4toannexb",
            "-an",
            "-f",
            "h264",
            str(output_path),
        ]
        print(f"Extracting H.264 from {input_path.name} with ffmpeg...")
        subprocess.run(cmd, check=True)
        print(f"Done. Saved as {output_path.name}")
        return output_path

    print(f"ffmpeg not found; extracting H.264 from {input_path.name} with built-in MP4 parser...")
    _mp4_extract_h264_annexb(str(input_path), str(output_path), repeat_headers=True)
    print(f"Done. Saved as {output_path.name}")
    return output_path



def send_video(dev, video_path, loop=False):
    output_path = extract_h264_from_mp4(video_path)

    write_to_device(dev, encrypt_command_packet(build_command_packet_header(111)))
    write_to_device(dev, encrypt_command_packet(build_command_packet_header(112)))
    write_to_device(dev, encrypt_command_packet(build_command_packet_header(13)))
    send_brightness_command(dev, 32)  # 14
    write_to_device(dev, encrypt_command_packet(build_command_packet_header(41)))
    clear_image(dev)  # 102
    send_frame_rate_command(dev, 25)  # 15

    # Negotiate chunk size if supported
    resp = write_to_device(dev, encrypt_command_packet(build_command_packet_header(CMD_GET_H264_CHUNK_SIZE)))
    chunk_size = 202752
    try:
        if resp and len(resp) >= 12:
            negotiated = int.from_bytes(resp[8:12], byteorder="big", signed=False)
            if 0 < negotiated <= 1024 * 1024:
                chunk_size = negotiated
    except Exception:
        pass

    print("Sending Send Video Command (ID 121)...")
    try:
        while True:
            with open(output_path, "rb") as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break

                    chunksize = len(data)
                    is_last = f.tell() == os.path.getsize(output_path)

                    cmd_packet = build_command_packet_header(CMD_PLAY_H264_CHUNK)
                    cmd_packet[8] = (chunksize >> 24) & 0xFF
                    cmd_packet[9] = (chunksize >> 16) & 0xFF
                    cmd_packet[10] = (chunksize >> 8) & 0xFF
                    cmd_packet[11] = chunksize & 0xFF
                    if is_last:
                        cmd_packet[12] = 1

                    full_payload = encrypt_command_packet(cmd_packet) + data
                    response = write_to_device(dev, full_payload)

                    # Flow control (queue depth is usually reported in response[8] to cmd 122)
                    if response is None:
                        delay(dev, 2)
                    else:
                        # Poll stream status when queue is high
                        st = write_to_device(dev, encrypt_command_packet(build_command_packet_header(CMD_GET_STREAM_STATUS)))
                        if st and len(st) > 8 and st[8] > 3:
                            delay(dev, 2)

            print("Video sent successfully.")
            if not loop:
                break
    except KeyboardInterrupt:
        print("\nLoop interrupted by user. Sending reset...")
    finally:
        write_to_device(dev, encrypt_command_packet(build_command_packet_header(CMD_STOP_STREAM)))


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
        total_size = Path(file_path).stat().st_size
        sent = 0
        chunk_index = 0

        preferred_cap = min(1024 * 1024, MAX_CHUNK_BYTES)

        with open(file_path, "rb") as fh:
            while True:
                data_chunk = fh.read(preferred_cap)
                if not data_chunk:
                    break

                chunk_index += 1
                chunk_len = len(data_chunk)
                sent += chunk_len
                is_last = sent >= total_size

                # [8..11]=chunk_capacity, [12..15]=chunk_len, [16]=last_flag, payload=chunk
                cmd_packet = build_command_packet_header(39)
                cap = preferred_cap
                cmd_packet[8] = (cap >> 24) & 0xFF
                cmd_packet[9] = (cap >> 16) & 0xFF
                cmd_packet[10] = (cap >> 8) & 0xFF
                cmd_packet[11] = cap & 0xFF
                cmd_packet[12] = (chunk_len >> 24) & 0xFF
                cmd_packet[13] = (chunk_len >> 16) & 0xFF
                cmd_packet[14] = (chunk_len >> 8) & 0xFF
                cmd_packet[15] = chunk_len & 0xFF
                if is_last:
                    cmd_packet[16] = 1

                response = write_to_device(dev, encrypt_command_packet(cmd_packet) + data_chunk)

                # Fallback: legacy layout uses [8..11]=chunk_len only
                if response is None or (not _resp_ok(response)):
                    legacy_packet = build_command_packet_header(39)
                    legacy_packet[8] = (chunk_len >> 24) & 0xFF
                    legacy_packet[9] = (chunk_len >> 16) & 0xFF
                    legacy_packet[10] = (chunk_len >> 8) & 0xFF
                    legacy_packet[11] = chunk_len & 0xFF
                    response = write_to_device(dev, encrypt_command_packet(legacy_packet) + data_chunk)

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


        # Send image data (auto JPEG fallback when payload exceeds device limit)
        send_pil_image_auto(self.dev, base_image, max_bytes=MAX_IMAGE_PAYLOAD_DEFAULT)
