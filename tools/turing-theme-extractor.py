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

# turing-theme-extractor.py: Extract resources from a Turing Smart Screen theme (.data files) made for Windows app
# This program will search and extract PNGs from the theme data and extract theme in the current directory
# The PNG can then be re-used to create a theme for System Monitor python program (see Wiki for theme creation)
import mmap
import os
import sys

PNG_SIGNATURE = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
PNG_IEND = b'\x49\x45\x4E\x44\xAE\x42\x60\x82'

MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

if len(sys.argv) != 2:
    print("Usage :")
    print("        turing-theme-extractor.py path/to/theme-file.data")
    print("Examples : ")
    print("        turing-theme-extractor.py \"Dragon Ball.data\"")
    print("        turing-theme-extractor.py \"Pikachu theme.data\"")
    print("        turing-theme-extractor.py NZXT_BLUR.data")
    try:
        sys.exit(0)
    except:
        os._exit(0)

found_png = 0

with open(sys.argv[1], "r+b") as theme_file:
    mm = mmap.mmap(theme_file.fileno(), 0)

    # Find PNG signature in binary data
    start_pos=0
    header_found = mm.find(PNG_SIGNATURE, 0)

    while header_found != -1:
        print("\nFound PNG header at 0x%06x" % header_found)

        # Find PNG IEND chunk (= end of file)
        iend_found = mm.find(PNG_IEND, header_found)
        print("Found PNG end-of-file at 0x%06x" % iend_found)

        # Extract PNG data to a file
        theme_file.seek(header_found)
        png_file = open('theme_res_' + str(header_found) + '.png', 'wb')
        png_file.write(theme_file.read(iend_found - header_found + len(PNG_IEND)))
        png_file.close()

        print("PNG extracted to theme_res_%s.png" % str(header_found))
        found_png = found_png + 1

        # Find next PNG signature (if any)
        header_found = mm.find(PNG_SIGNATURE, iend_found)

    print("\n%d PNG files extracted from theme to current directory" % found_png)

