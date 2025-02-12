#!/usr/bin/env python
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
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
# generate-version-info.py: generate PyInstaller .exe version file from version number in argument
# Inspired from PyInstaller/utils/cliutils/grab_version.py and PyInstaller/utils/win32/versioninfo.py

import codecs
import sys
from pathlib import Path

from PyInstaller.utils.win32 import versioninfo

# Load generic file and parse version info
VERSION_INFO_FILE = str(Path(__file__).parent.resolve()) + "/pyinstaller-version-info.txt"
info = versioninfo.load_version_info_from_text_file(VERSION_INFO_FILE)

if not info:
    raise SystemExit("Error: VersionInfo resource not found in exe")

# Get version number from argument
version = sys.argv[1].split('.')
major = int(version[0])
minor = int(version[1])
revision = int(version[2])
build = 0  # For this project we only use 3-digit versions

if len(sys.argv) == 3 and sys.argv[2] == "debug":
    print (f"Generating debug version {major}.{minor}.{revision}-debug")
    debug_version = True
else:
    print (f"Generating version {major}.{minor}.{revision}")
    debug_version = False

# Update FixedFileInfo version
info.ffi.fileVersionMS = (major << 16) + minor
info.ffi.fileVersionLS = (revision << 16) + build
info.ffi.productVersionMS = (major << 16) + minor
info.ffi.productVersionLS = (revision << 16) + build

# Update StringFileInfo version
for elem in info.kids[0].kids[0].kids:
    if elem.name == 'ProductVersion' or elem.name == 'FileVersion':
        elem.val = f"{major}.{minor}.{revision}"
        if debug_version:
            elem.val += "-debug"

# Update version file with new info, to be used by PyInstaller
with codecs.open(VERSION_INFO_FILE, 'w', 'utf-8') as fp:
    fp.write(str(info))

print(f"Version info written to: {VERSION_INFO_FILE}")
