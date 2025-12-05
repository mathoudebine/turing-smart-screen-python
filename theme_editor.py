#!/usr/bin/env python
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

# theme_editor.py: Allow to easily edit themes for System Monitor (main.py) in a preview window on the computer
# The preview window is refreshed as soon as the theme file is modified
from library.pythoncheck import check_python_version

check_python_version()
import locale
import logging
import os
import platform
import subprocess
import sys
import time

try:
    import tkinter
    from PIL import ImageTk, Image
    from tkinter import Tk, DoubleVar, Toplevel
    from tkinter.ttk import Button, Label, Scale
except:
    print(
        "[ERROR] Tkinter dependency not installed. Please follow troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed")
    try:
        sys.exit(0)
    except:
        os._exit(0)
import library.log

library.log.logger.setLevel(logging.NOTSET)  # Disable system monitor logging for the editor
# Create a logger for the editor
logger = logging.getLogger('turing-editor')
logger.setLevel(logging.DEBUG)
# Hardcode specific configuration for theme editor
from library.config import config

config.CONFIG_DATA["config"]["HW_SENSORS"] = "STATIC"  # For theme editor always use stub data
config.load_theme()
# For theme editor, always use simulated LCD
config.CONFIG_DATA["display"]["REVISION"] = "SIMU"
from library.display import display  # Only import display after hardcoded config is set


# Resize editor if display is too big (e.g. 8.8" displays are 1920x480), can be changed later by zoom buttons
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
    if config.THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", 0) > 0:
        stats.CPU.percentage()
    if config.THEME_DATA['STATS']['CPU']['FREQUENCY'].get("INTERVAL", 0) > 0:
        stats.CPU.frequency()
    if config.THEME_DATA['STATS']['CPU']['LOAD'].get("INTERVAL", 0) > 0:
        stats.CPU.load()
    if config.THEME_DATA['STATS']['CPU']['TEMPERATURE'].get("INTERVAL", 0) > 0:
        stats.CPU.temperature()
    if config.THEME_DATA['STATS']['CPU']['FAN_SPEED'].get("INTERVAL", 0) > 0:
        stats.CPU.fan_speed()
    if config.THEME_DATA['STATS']['GPU'].get("INTERVAL", 0) > 0:
        stats.Gpu.stats()
    if config.THEME_DATA['STATS']['MEMORY'].get("INTERVAL", 0) > 0:
        stats.Memory.stats()
    if config.THEME_DATA['STATS']['DISK'].get("INTERVAL", 0) > 0:
        stats.Disk.stats()
    if config.THEME_DATA['STATS']['NET'].get("INTERVAL", 0) > 0:
        stats.Net.stats()
    if config.THEME_DATA['STATS']['DATE'].get("INTERVAL", 0) > 0:
        stats.Date.stats()
    if config.THEME_DATA['STATS']['UPTIME'].get("INTERVAL", 0) > 0:
        stats.SystemUptime.stats()
    if config.THEME_DATA['STATS']['CUSTOM'].get("INTERVAL", 0) > 0:
        stats.Custom.stats()
    if config.THEME_DATA['STATS']['WEATHER'].get("INTERVAL", 0) > 0:
        stats.Weather.stats()
    if config.THEME_DATA['STATS']['PING'].get("INTERVAL", 0) > 0:
        stats.Ping.stats()


class Viewer(Tk if __name__ == '__main__' else Toplevel):
    def __init__(self, theme: str = None):
        super().__init__()
        if theme:
            config.CONFIG_DATA["config"]["THEME"] = theme  # Theme is given as argument
        self.last_edit_time = 0
        self.theme_file = None
        self.error_in_theme = False
        self.inited = False
        self.RESIZE_FACTOR = 2 if (display.lcd.get_width() > 1000 or display.lcd.get_height() > 1000) else 1
        self.init_env()
        self.ERROR_IN_THEME = Image.open("res/docs/error-in-theme.png")
        self.RGB_LED_MARGIN = 12
        self.x0 = 0
        self.y0 = 0
        self.y1 = 0
        self.x1 = 0
        self.title("Turing SysMon Theme Editor")
        self.iconphoto(True, tkinter.PhotoImage(file=config.MAIN_DIRECTORY / "res/icons/monitor-icon-17865/64.png"))
        self.display_width, self.display_height = int(display.lcd.get_width() / self.RESIZE_FACTOR), int(
            display.lcd.get_height() / self.RESIZE_FACTOR)
        self.geometry(
            str(self.display_width + 2 * self.RGB_LED_MARGIN) + "x" + str(
                self.display_height + 2 * self.RGB_LED_MARGIN + 80))
        if hasattr(self, 'call'):
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.call('wm', 'attributes', '.', '-topmost', '1')  # Preview window always on top
        self.config(cursor="cross")
        led_color = config.THEME_DATA['display'].get("DISPLAY_RGB_LED", (255, 255, 255))
        if isinstance(led_color, str):
            led_color = tuple(map(int, led_color.split(', ')))
        self.configure(bg='#%02x%02x%02x' % led_color)

        self.circular_mask = Image.open(config.MAIN_DIRECTORY / "res/backgrounds/circular-mask.png")

        # Display preview in the window
        if not self.error_in_theme:
            screen_image = display.lcd.screen_image
            if config.THEME_DATA["display"].get("DISPLAY_SIZE", '3.5"') == '2.1"':
                # This is a circular screen: apply a circle mask over the preview
                screen_image.paste(self.circular_mask, mask=self.circular_mask)
            self.display_image = ImageTk.PhotoImage(
                screen_image.resize(
                    (int(screen_image.width / self.RESIZE_FACTOR), int(screen_image.height / self.RESIZE_FACTOR))))
        else:
            size = self.display_width if self.display_width < self.display_height else self.display_height
            self.display_image = ImageTk.PhotoImage(self.ERROR_IN_THEME.resize((size, size)))
        self.viewer_picture = Label(self, image=self.display_image, borderwidth=0)
        self.viewer_picture.place(x=self.RGB_LED_MARGIN, y=self.RGB_LED_MARGIN)

        # Allow to click on preview to show coordinates and draw zones
        self.viewer_picture.bind("<ButtonPress-1>", self.on_button1_press)
        self.viewer_picture.bind("<B1-Motion>", self.on_button1_press_and_drag)
        self.viewer_picture.bind("<ButtonRelease-1>", self.on_button1_release)

        # Allow to resize editor using mouse wheel or buttons
        self.bind_all("<MouseWheel>", self.on_mousewheel)
        self.zoom_level = DoubleVar(value=self.RESIZE_FACTOR)
        self.zoom_scale = Scale(self, from_=0.2, to=2, variable=self.zoom_level, orient="horizontal",
                                command=self.on_zoom_level_change)
        self.zoom_scale.place(x=self.RGB_LED_MARGIN, y=self.display_height + 2 * self.RGB_LED_MARGIN, height=30,
                              width=int(self.display_width / 2))
        self.zoom_label = Label(self, text=f"Zoom Level:{self.RESIZE_FACTOR}")
        self.zoom_label.place(x=self.RGB_LED_MARGIN, y=self.display_height + 2 * self.RGB_LED_MARGIN, height=30,
                              width=int(self.display_width / 2))

        self.zoom_scale.place(x=int(self.display_width / 2) + self.RGB_LED_MARGIN,
                              y=self.display_height + 2 * self.RGB_LED_MARGIN,
                              height=30, width=int(self.display_width / 2))

        self.label_coord = Label(self, text="Click or draw a zone to show coordinates")
        self.label_coord.place(x=0, y=self.display_height + 2 * self.RGB_LED_MARGIN + 40,
                               width=self.display_width + 2 * self.RGB_LED_MARGIN)

        self.label_info = Label(self, text="This preview will reload when theme file is updated")
        self.label_info.place(x=0, y=self.display_height + 2 * self.RGB_LED_MARGIN + 60,
                              width=self.display_width + 2 * self.RGB_LED_MARGIN)

        self.label_zone = tkinter.Label(self, bg='#%02x%02x%02x' % tuple(map(lambda x: 255 - x, led_color)))
        self.label_zone.bind("<ButtonRelease-1>", self.on_zone_click)
        self.update()

    def init_env(self):
        if self.inited:
            return
        # Apply system locale to this program
        locale.setlocale(locale.LC_ALL, '')

        logger.debug("Starting Theme Editor...")

        # Get theme file to edit
        self.theme_file = config.THEME_DATA['PATH'] + "theme.yaml"
        self.last_edit_time = os.path.getmtime(self.theme_file)
        logger.debug("Using theme file " + self.theme_file)

        # Open theme in default editor. You can also open the file manually in another program
        logger.debug("Opening theme file in your default editor. If it does not work, open it manually in the "
                     "editor of your choice")
        if platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', config.MAIN_DIRECTORY / self.theme_file))
        elif platform.system() == 'Windows':  # Windows
            os.startfile(config.MAIN_DIRECTORY / self.theme_file)
        else:  # linux variants
            subprocess.call(('xdg-open', config.MAIN_DIRECTORY / self.theme_file))

        # Load theme file and generate first preview
        try:
            refresh_theme()
            self.error_in_theme = False
        except Exception as e:
            logger.error(f"Error in theme: {e}")
            self.error_in_theme = True
        self.inited = True

    def refresh_window(self):
        self.display_width, self.display_height = int(display.lcd.get_width() / self.RESIZE_FACTOR), int(
            display.lcd.get_height() / self.RESIZE_FACTOR)
        self.geometry(
            str(self.display_width + 2 * self.RGB_LED_MARGIN) + "x" + str(
                self.display_height + 2 * self.RGB_LED_MARGIN + 80))
        self.zoom_scale.place(x=self.RGB_LED_MARGIN + int(self.display_width / 2),
                              y=self.display_height + 2 * self.RGB_LED_MARGIN, height=30,
                              width=int(self.display_width / 2))
        self.zoom_label.place(x=self.RGB_LED_MARGIN, y=self.display_height + 2 * self.RGB_LED_MARGIN, height=30,
                              width=int(self.display_width / 2))
        self.label_info.place(x=0, y=self.display_height + 2 * self.RGB_LED_MARGIN + 60,
                              width=self.display_width + 2 * self.RGB_LED_MARGIN)
        self.label_coord.place(x=0, y=self.display_height + 2 * self.RGB_LED_MARGIN + 40,
                               width=self.display_width + 2 * self.RGB_LED_MARGIN)

    def refresh(self, force_fresh: bool = False):
        if os.path.exists(self.theme_file) and os.path.getmtime(
                self.theme_file) > self.last_edit_time or force_fresh:
            logger.debug("The theme file has been updated, the preview window will refresh")
            try:
                refresh_theme()
                self.error_in_theme = False
            except Exception as e:
                logger.error(f"Error in theme: {e}")
                self.error_in_theme = True
            self.last_edit_time = os.path.getmtime(self.theme_file)

            # Update the preview.png that is in the theme folder
            display.lcd.screen_image.save(config.THEME_DATA['PATH'] + "preview.png", "PNG")

            # Display new picture
            if not self.error_in_theme:
                self.screen_image = display.lcd.screen_image
                if config.THEME_DATA["display"].get("DISPLAY_SIZE", '3.5"') == '2.1"':
                    # This is a circular screen: apply a circle mask over the preview
                    self.screen_image.paste(self.circular_mask, mask=self.circular_mask)
                self.display_image = ImageTk.PhotoImage(
                    self.screen_image.resize(
                        (int(self.screen_image.width / self.RESIZE_FACTOR),
                         int(self.screen_image.height / self.RESIZE_FACTOR))))
            else:
                size = self.display_width if self.display_width < self.display_height else self.display_height
                self.display_image = ImageTk.PhotoImage(self.ERROR_IN_THEME.resize((size, size)))
            self.viewer_picture.config(image=self.display_image)

            # Refresh RGB backplate LEDs color
            led_color = config.THEME_DATA['display'].get("DISPLAY_RGB_LED", (255, 255, 255))
            if isinstance(led_color, str):
                led_color = tuple(map(int, led_color.split(', ')))
            self.configure(bg='#%02x%02x%02x' % led_color)
            self.label_zone.configure(bg='#%02x%02x%02x' % tuple(map(lambda x: 255 - x, led_color)))

    def draw_zone(self):
        x = min(self.x0, self.x1)
        y = min(self.y0, self.y1)
        width = max(self.x0, self.x1) - min(self.x0, self.x1)
        height = max(self.y0, self.y1) - min(self.y0, self.y1)
        if width > 0 and height > 0:
            self.label_zone.place(x=x + self.RGB_LED_MARGIN, y=y + self.RGB_LED_MARGIN, width=width, height=height)
        else:
            self.label_zone.place_forget()

    def on_button1_press(self, event):
        self.x0, self.y0 = event.x, event.y
        self.label_zone.place_forget()

    def on_button1_press_and_drag(self, event):
        display_width, display_height = int(display.lcd.get_width() / self.RESIZE_FACTOR), int(
            display.lcd.get_height() / self.RESIZE_FACTOR)
        self.x1, self.y1 = event.x, event.y

        # Do not draw zone outside of theme preview
        if self.x1 < 0:
            self.x1 = 0
        elif self.x1 >= display_width:
            self.x1 = display_width - 1
        if self.y1 < 0:
            self.y1 = 0
        elif self.y1 >= display_height:
            self.y1 = display_height - 1

        self.label_coord.config(
            text='Drawing zone from [{:0.0f},{:0.0f}] to [{:0.0f},{:0.0f}]'.format(self.x0 * self.RESIZE_FACTOR,
                                                                                   self.y0 * self.RESIZE_FACTOR,
                                                                                   self.x1 * self.RESIZE_FACTOR,
                                                                                   self.y1 * self.RESIZE_FACTOR))
        self.draw_zone()

    def on_button1_release(self, event):
        display_width, display_height = int(display.lcd.get_width() / self.RESIZE_FACTOR), int(
            display.lcd.get_height() / self.RESIZE_FACTOR)
        self.x1, self.y1 = event.x, event.y
        if self.x1 != self.x0 or self.y1 != self.y0:
            # Do not draw zone outside of theme preview
            if self.x1 < 0:
                self.x1 = 0
            elif self.x1 >= display_width:
                self.x1 = display_width - 1
            if self.y1 < 0:
                self.y1 = 0
            elif self.y1 >= display_height:
                self.y1 = display_height - 1

            # Display drawn zone and coordinates
            self.draw_zone()

            # Display relative zone coordinates, to set in theme
            x = min(self.x0, self.x1)
            y = min(self.y0, self.y1)
            width = max(self.x0, self.x1) - min(self.x0, self.x1)
            height = max(self.y0, self.y1) - min(self.y0, self.y1)

            self.label_coord.config(
                text='Zone: X={:0.0f}, Y={:0.0f}, width={:0.0f} height={:0.0f}'.format(x * self.RESIZE_FACTOR,
                                                                                       y * self.RESIZE_FACTOR,
                                                                                       width * self.RESIZE_FACTOR,
                                                                                       height * self.RESIZE_FACTOR))
        else:
            # Display click coordinates
            self.label_coord.config(
                text='X={:0.0f}, Y={:0.0f} (click and drag to draw a zone)'.format(self.x0 * self.RESIZE_FACTOR,
                                                                                   self.y0 * self.RESIZE_FACTOR))

    def on_zone_click(self, event):
        self.label_zone.place_forget()

    def on_closing(self):
        logger.debug("Exit Theme Editor...")
        try:
            sys.exit(0)
        except:
            os._exit(0)

    def on_zoom_level_change(self, value):
        level = self.zoom_level.get()
        if not level % 0.2:
            self.zoom_level.set(level - (level % 0.2))
        self.zoom_label.config(text=f"Zoom Level:{self.zoom_level.get():.1f}")
        self.RESIZE_FACTOR = round(self.zoom_level.get(), 1)

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.RESIZE_FACTOR += 0.2
        else:
            self.RESIZE_FACTOR -= 0.2
        self.zoom_scale.set(self.RESIZE_FACTOR)


def main(theme: str = None):
    # Create preview window
    logger.debug("Opening theme preview window with static data")
    viewer = Viewer(theme)
    current_resize_factor = viewer.RESIZE_FACTOR
    logger.debug(
        "You can now edit the theme file in the editor. When you save your changes, the preview window will "
        "update automatically")

    while True:
        if current_resize_factor != viewer.RESIZE_FACTOR:
            logger.info(
                f"Zoom level changed from {current_resize_factor:.1f} to {viewer.RESIZE_FACTOR:.1f}, reloading theme editor")
            viewer.refresh(True)
            viewer.refresh_window()
            current_resize_factor = viewer.RESIZE_FACTOR
        # Every time the theme file is modified: reload preview
        viewer.refresh()
        # Regularly update the viewer window even if content unchanged, or it will appear as "not responding"
        viewer.update()
        time.sleep(0.1)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage :")
        print("        theme_editor.py theme-name")
        print("Examples : ")
        print("        theme_editor.py 3.5inchTheme2")
        print("        theme_editor.py Landscape6Grid")
        print("        theme_editor.py Cyberpunk")
        try:
            sys.exit(1)
        except:
            os._exit(1)
    main(sys.argv[1])
