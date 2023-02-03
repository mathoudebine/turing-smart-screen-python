# turing-smart-screen-python - a Python system monitor and library for 3.5" USB-C displays like Turing Smart Screen or XuanFang
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

# theme-editor.py: Allow to easily edit themes for System Monitor (main.py) in a preview window on the computer
# The preview window is refreshed as soon as the theme file is modified

import locale
import logging
import os
import platform
import subprocess
import sys
import time
import tkinter

MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

if len(sys.argv) != 2:
    print("Usage :")
    print("        theme-editor.py theme-name")
    print("Examples : ")
    print("        theme-editor.py 3.5inchTheme2")
    print("        theme-editor.py Landscape6Grid")
    print("        theme-editor.py Cyberpunk")
    try:
        sys.exit(0)
    except:
        os._exit(0)

from PIL import ImageTk

import library.log
library.log.logger.setLevel(logging.NOTSET)  # Disable system monitor logging for the editor

# Create a logger for the editor
logger = logging.getLogger('turing-editor')
logger.setLevel(logging.DEBUG)

# Hardcode specific configuration for theme editor
from library import config
config.CONFIG_DATA["display"]["REVISION"] = "SIMU"  # For theme editor, always use simulated LCD
config.CONFIG_DATA["config"]["HW_SENSORS"] = "STATIC"  # For theme editor always use stub data
config.CONFIG_DATA["config"]["THEME"] = sys.argv[1]  # Theme is given as argument

from library.display import display  # Only import display after hardcoded config is set


def refresh_theme():
    config.load_theme()

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
    def on_closing():
        logger.debug("Exit Theme Editor...")
        try:
            sys.exit(0)
        except:
            os._exit(0)


    # Apply system locale to this program
    locale.setlocale(locale.LC_ALL, '')

    # Load theme file and generate first preview
    refresh_theme()

    logger.debug("Starting Theme Editor...")

    # Get theme file to edit
    theme_file = config.THEME_DATA['PATH'] + "theme.yaml"
    last_edit_time = os.path.getmtime(theme_file)
    logger.debug("Using theme file " + theme_file)

    # Open theme in default editor. You can also open the file manually in another program
    logger.debug("Opening theme file in your default editor. If it does not work, open it manually in the "
                 "editor of your choice")
    if platform.system() == 'Darwin':  # macOS
        subprocess.call(('open', "./" + theme_file))
    elif platform.system() == 'Windows':  # Windows
        os.startfile(".\\" + theme_file)
    else:  # linux variants
        subprocess.call(('xdg-open', "./" + theme_file))

    # Create preview window
    logger.debug("Opening theme preview window with static data")
    viewer = tkinter.Tk()
    viewer.title("Turing SysMon Theme Editor")
    viewer.iconphoto(True, tkinter.PhotoImage(file="res/icons/monitor-icon-17865/64.png"))
    viewer.geometry(str(display.lcd.get_width() + 24) + "x" + str(display.lcd.get_height() + 44))
    viewer.protocol("WM_DELETE_WINDOW", on_closing)
    viewer.call('wm', 'attributes', '.', '-topmost', '1')  # Preview window always on top

    # Display RGB backplate LEDs color as background color
    led_color = config.THEME_DATA['display'].get("DISPLAY_RGB_LED", (255, 255, 255))
    if isinstance(led_color, str):
        led_color = tuple(map(int, led_color.split(', ')))
    viewer.configure(bg='#%02x%02x%02x' % led_color)

    # Display preview in the window
    display_image = ImageTk.PhotoImage(display.lcd.screen_image)
    viewer_picture = tkinter.Label(viewer, image=display_image)
    viewer_picture.place(x=10, y=10)

    label = tkinter.Label(viewer, text="This preview will reload when theme file is updated")
    label.place(x=0, y=display.lcd.get_height() + 24, width=display.lcd.get_width() + 24)

    viewer.update()

    logger.debug("You can now edit the theme file in the editor. When you save your changes, the preview window will "
                 "update automatically")
    # Every time the theme file is modified: reload preview
    while True:
        if os.path.getmtime(theme_file) > last_edit_time:
            logger.debug("The theme file has been updated, the preview window will refresh")
            refresh_theme()
            last_edit_time = os.path.getmtime(theme_file)

            # Display new picture
            display_image = ImageTk.PhotoImage(display.lcd.screen_image)
            viewer_picture.config(image=display_image)

            # Refresh RGB backplate LEDs color
            led_color = config.THEME_DATA['display'].get("DISPLAY_RGB_LED", (255, 255, 255))
            if isinstance(led_color, str):
                led_color = tuple(map(int, led_color.split(', ')))
            viewer.configure(bg='#%02x%02x%02x' % led_color)

        # Regularly update the viewer window even if content unchanged
        viewer.update()

        time.sleep(0.1)
