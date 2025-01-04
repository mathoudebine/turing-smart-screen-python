from typing import Iterator, Literal

import numpy as np
from PIL import Image


def chunked(data: bytes, chunk_size: int) -> Iterator[bytes]:
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


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
