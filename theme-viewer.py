# theme-viewer
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

import locale
import os
import platform
import sys
import time

MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

from library.log import logger
from library.display import display
import library.config

def refresh_theme():
    library.config.load_theme()

    # Initialize the display
    display.initialize_display()

    # Create all static images
    display.display_static_images()

    # Create all static texts
    display.display_static_text()

    # Display all data on screen once
    import library.stats as stats
    stats.CPU.percentage()
    stats.CPU.frequency()
    stats.CPU.load()
    stats.CPU.temperature()
    stats.Gpu.stats()
    stats.Memory.stats()
    stats.Disk.stats()
    stats.Net.stats()
    stats.Date.stats()

if __name__ == "__main__":
    # Apply system locale to this program
    locale.setlocale(locale.LC_ALL, '')

    logger.debug("Starting Theme Viewer")

    # Display preview at least once
    refresh_theme()

    theme_file = library.config.THEME_DATA['PATH'] + "theme.yaml"
    last_edit_time = os.path.getmtime(theme_file)

    # Every time the theme file is modified: reload preview
    while True:
        if os.path.getmtime(theme_file) > last_edit_time:
            refresh_theme()
            last_edit_time = os.path.getmtime(theme_file)
        time.sleep(0.1)
