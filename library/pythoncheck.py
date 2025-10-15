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

# This file is used to check if Python version used is compatible
import os
import sys

# Oldest / newest version supported
MIN_PYTHON = (3, 9)
MAX_PYTHON = (3, 13)


def check_python_version():
    current_version = sys.version_info[:2]

    if current_version < MIN_PYTHON or current_version > MAX_PYTHON:
        print(f"[ERROR] Python {current_version[0]}.{current_version[1]} is not supported by this program. "
              f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}-{MAX_PYTHON[0]}.{MAX_PYTHON[1]} required.")
        try:
            sys.exit(0)
        except:
            os._exit(0)
