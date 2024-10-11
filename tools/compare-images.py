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

# compare-images.py: Run by GitHub actions on new PR, to compare theme renderings and generate a diff if it has changed

import sys

from PIL import Image, ImageChops

try:
    im1 = Image.open(sys.argv[1]).convert('RGB')
except:
    sys.exit(0)

try:
    im2 = Image.open(sys.argv[2]).convert('RGB')
except:
    sys.exit(0)

if list(im1.getdata()) == list(im2.getdata()):
    print("The 2 pictures are visually identical")
else:
    print("The 2 pictures are different!")
    diff = ImageChops.difference(im1, im2)
    diff.save(sys.argv[3])
