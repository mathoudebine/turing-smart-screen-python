from typing import Iterator, Literal

import numpy as np
from PIL import Image


def chunked(data: bytes, chunk_size: int) -> Iterator[bytes]:
    for i in range(0, len(data), chunk_size):
        yield data[i: i + chunk_size]


def image_to_RGB565(image: Image.Image, endianness: Literal["big", "little"]) -> bytes:
    if image.mode not in ["RGB", "RGBA"]:
        # we need the first 3 channels to be R, G and B
        image = image.convert("RGB")

    rgb = np.asarray(image)

    # flatten the first 2 dimensions (width and height) into a single stream
    # of RGB pixels
    rgb = rgb.reshape((image.size[1] * image.size[0], -1))

    # extract R, G, B channels and promote them to 16 bits
    r = rgb[:, 0].astype(np.uint16)
    g = rgb[:, 1].astype(np.uint16)
    b = rgb[:, 2].astype(np.uint16)

    # construct RGB565
    r = r >> 3
    g = g >> 2
    b = b >> 3
    rgb565 = (r << 11) | (g << 5) | b

    # serialize to the correct endianness
    if endianness == "big":
        typ = ">u2"
    else:
        typ = "<u2"
    return rgb565.astype(typ).tobytes()


def image_to_BGR(image: Image.Image) -> (bytes, int):
    if image.mode not in ["RGB", "RGBA"]:
        # we need the first 3 channels to be R, G and B
        image = image.convert("RGB")
    rgb = np.asarray(image)
    # same as rgb[:, :, [2, 1, 0]] but faster
    bgr = np.take(rgb, (2, 1, 0), axis=-1)
    return bgr.tobytes(), 3


def image_to_BGRA(image: Image.Image) -> (bytes, int):
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    rgba = np.asarray(image)
    # same as rgba[:, :, [2, 1, 0, 3]] but faster
    bgra = np.take(rgba, (2, 1, 0, 3), axis=-1)
    return bgra.tobytes(), 4


# FIXME: to optimize like other functions above
def image_to_compressed_BGRA(image: Image.Image) -> (bytes, int):
    compressed_bgra = bytearray()
    image_data = image.convert("RGBA").load()
    for h in range(image.height):
        for w in range(image.width):
            # r = pixel[0], g = pixel[1], b = pixel[2], a = pixel[3]
            pixel = image_data[w, h]
            a = pixel[3] >> 4
            compressed_bgra.append(pixel[2] & 0xFC | a >> 2)
            compressed_bgra.append(pixel[1] & 0xFC | a & 2)
            compressed_bgra.append(pixel[0])
    return bytes(compressed_bgra), 3
