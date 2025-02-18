#!/usr/bin/env python
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
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

# This file generate PNG previews for available fonts

import os
import sys

MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

from PIL import Image, ImageDraw, ImageFont
import math
from pathlib import Path

FONTS_DIR = str(Path(__file__).parent.resolve()) + "/"


def generate_preview(font_dir: str, font_filename: str, text: str, font_size: int = 40,
                     font_color: tuple[int, int, int] = (0, 0, 0),
                     background_color: tuple[int, int, int] = (255, 255, 255)):
    font = os.path.join(font_dir, font_filename)

    ttfont = ImageFont.truetype(font, font_size)
    text_image = Image.new(
        'RGB',
        (1000, 1000),
        background_color
    )
    d = ImageDraw.Draw(text_image)
    left, top, right, bottom = d.textbbox((0, 0), text, font=ttfont)

    # textbbox may return float values, which is not good for the bitmap operations below.
    # Let's extend the bounding box to the next whole pixel in all directions
    left, top = math.floor(left), math.floor(top)
    right, bottom = math.ceil(right), math.ceil(bottom)

    d.text((0, 0), text, font=ttfont, fill=font_color)

    text_image = text_image.crop(box=(left, top, right, bottom))

    text_image.save(os.path.join(font_dir, font_filename[:-4] + "_preview.png"), "PNG")


TEXT = ("50%  9876M  Core i5-4321\n"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
        "abcdefghijklmnopqrstuvwxyz\n"
        "0123456789 %;,:?!/-_()[]{}<>=+*#$")

fonts = []
for dir in os.listdir(FONTS_DIR):
    font_dir = os.path.join(FONTS_DIR, dir)
    if os.path.isdir(font_dir):
        for font in os.listdir(font_dir):
            font_file = os.path.join(font_dir, font)
            if os.path.isfile(font_file) and (font_file.endswith(".ttf") or font_file.endswith(".otf")):
                print(f"Found font {dir}/{font}")
                generate_preview(font_dir, font, "40%", font_size=60)
