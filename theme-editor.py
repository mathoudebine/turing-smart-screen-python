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

# theme-editor.py: Allow to easily edit themes for System Monitor (main.py) in a preview window on the computer
# The preview window is refreshed as soon as the theme file is modified

import locale
import logging
import os
import platform
import subprocess
import sys
import time

MIN_PYTHON = (3, 8)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import tkinter
    from PIL import ImageTk, Image
except:
    print(
        "[ERROR] Tkinter dependency not installed. Please follow troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed")
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

import library.log

library.log.logger.setLevel(logging.NOTSET)  # Disable system monitor logging for the editor

# Create a logger for the editor
logger = logging.getLogger('turing-editor')
logger.setLevel(logging.DEBUG)

# Hardcode specific configuration for theme editor
from library import config

config.CONFIG_DATA["config"]["HW_SENSORS"] = "STATIC"  # For theme editor always use stub data
config.CONFIG_DATA["config"]["THEME"] = sys.argv[1]  # Theme is given as argument

config.load_theme()

# For theme editor, always use simulated LCD
config.CONFIG_DATA["display"]["REVISION"] = "SIMU"

from library.display import display  # Only import display after hardcoded config is set

RGB_LED_MARGIN = 12

# Resize editor if display is too big (e.g. 8.8" displays are 1920x480), can be changed later by zoom buttons
RESIZE_FACTOR = 2 if (display.lcd.get_width() > 1000 or display.lcd.get_height() > 1000) else 1

ERROR_IN_THEME = Image.open("res/docs/error-in-theme.png")


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


if __name__ == "__main__":
    def on_closing():
        logger.debug("Exit Theme Editor...")
        try:
            sys.exit(0)
        except:
            os._exit(0)


    x0 = 0
    y0 = 0


    def draw_zone(x0, y0, x1, y1):
        x = min(x0, x1)
        y = min(y0, y1)
        width = max(x0, x1) - min(x0, x1)
        height = max(y0, y1) - min(y0, y1)
        if width > 0 and height > 0:
            label_zone.place(x=x + RGB_LED_MARGIN, y=y + RGB_LED_MARGIN, width=width, height=height)
        else:
            label_zone.place_forget()


    def on_button1_press(event):
        global x0, y0
        x0, y0 = event.x, event.y
        label_zone.place_forget()


    def on_button1_press_and_drag(event):
        display_width, display_height = int(display.lcd.get_width() / RESIZE_FACTOR), int(
            display.lcd.get_height() / RESIZE_FACTOR)
        x1, y1 = event.x, event.y

        # Do not draw zone outside of theme preview
        if x1 < 0:
            x1 = 0
        elif x1 >= display_width:
            x1 = display_width - 1
        if y1 < 0:
            y1 = 0
        elif y1 >= display_height:
            y1 = display_height - 1

        label_coord.config(text='Drawing zone from [{:0.0f},{:0.0f}] to [{:0.0f},{:0.0f}]'.format(x0 * RESIZE_FACTOR,
                                                                                                  y0 * RESIZE_FACTOR,
                                                                                                  x1 * RESIZE_FACTOR,
                                                                                                  y1 * RESIZE_FACTOR))
        draw_zone(x0, y0, x1, y1)


    def on_button1_release(event):
        display_width, display_height = int(display.lcd.get_width() / RESIZE_FACTOR), int(
            display.lcd.get_height() / RESIZE_FACTOR)
        x1, y1 = event.x, event.y
        if x1 != x0 or y1 != y0:
            # Do not draw zone outside of theme preview
            if x1 < 0:
                x1 = 0
            elif x1 >= display_width:
                x1 = display_width - 1
            if y1 < 0:
                y1 = 0
            elif y1 >= display_height:
                y1 = display_height - 1

            # Display drawn zone and coordinates
            draw_zone(x0, y0, x1, y1)

            # Display relative zone coordinates, to set in theme
            x = min(x0, x1)
            y = min(y0, y1)
            width = max(x0, x1) - min(x0, x1)
            height = max(y0, y1) - min(y0, y1)

            label_coord.config(text='Zone: X={:0.0f}, Y={:0.0f}, width={:0.0f} height={:0.0f}'.format(x * RESIZE_FACTOR,
                                                                                                      y * RESIZE_FACTOR,
                                                                                                      width * RESIZE_FACTOR,
                                                                                                      height * RESIZE_FACTOR))
        else:
            # Display click coordinates
            label_coord.config(
                text='X={:0.0f}, Y={:0.0f} (click and drag to draw a zone)'.format(x0 * RESIZE_FACTOR,
                                                                                   y0 * RESIZE_FACTOR))


    def on_zone_click(event):
        label_zone.place_forget()


    def on_mousewheel(event):
        global RESIZE_FACTOR
        if event.delta > 0:
            RESIZE_FACTOR = RESIZE_FACTOR - 0.2
        else:
            RESIZE_FACTOR = RESIZE_FACTOR + 0.2


    def on_zoom_plus():
        global RESIZE_FACTOR
        RESIZE_FACTOR = RESIZE_FACTOR - 0.2


    def on_zoom_minus():
        global RESIZE_FACTOR
        RESIZE_FACTOR = RESIZE_FACTOR + 0.2


    # Apply system locale to this program
    locale.setlocale(locale.LC_ALL, '')

    logger.debug("Starting Theme Editor...")

    # Get theme file to edit
    theme_file = config.THEME_DATA['PATH'] + "theme.yaml"
    last_edit_time = os.path.getmtime(theme_file)
    logger.debug("Using theme file " + theme_file)

    # Open theme in default editor. You can also open the file manually in another program
    logger.debug("Opening theme file in your default editor. If it does not work, open it manually in the "
                 "editor of your choice")
    if platform.system() == 'Darwin':  # macOS
        subprocess.call(('open', config.MAIN_DIRECTORY / theme_file))
    elif platform.system() == 'Windows':  # Windows
        os.startfile(config.MAIN_DIRECTORY / theme_file)
    else:  # linux variants
        subprocess.call(('xdg-open', config.MAIN_DIRECTORY / theme_file))

    # Load theme file and generate first preview
    try:
        refresh_theme()
        error_in_theme = False
    except Exception as e:
        logger.error(f"Error in theme: {e}")
        error_in_theme = True

    while True:
        display_width, display_height = int(display.lcd.get_width() / RESIZE_FACTOR), int(
            display.lcd.get_height() / RESIZE_FACTOR)
        current_resize_factor = RESIZE_FACTOR

        # Create preview window
        logger.debug("Opening theme preview window with static data")
        viewer = tkinter.Tk()
        viewer.title("Turing SysMon Theme Editor")
        viewer.iconphoto(True, tkinter.PhotoImage(file=config.MAIN_DIRECTORY / "res/icons/monitor-icon-17865/64.png"))
        viewer.geometry(str(display_width + 2 * RGB_LED_MARGIN) + "x" + str(display_height + 2 * RGB_LED_MARGIN + 80))
        viewer.protocol("WM_DELETE_WINDOW", on_closing)
        viewer.call('wm', 'attributes', '.', '-topmost', '1')  # Preview window always on top
        viewer.config(cursor="cross")

        # Display RGB backplate LEDs color as background color
        led_color = config.THEME_DATA['display'].get("DISPLAY_RGB_LED", (255, 255, 255))
        if isinstance(led_color, str):
            led_color = tuple(map(int, led_color.split(', ')))
        viewer.configure(bg='#%02x%02x%02x' % led_color)

        circular_mask = Image.open(config.MAIN_DIRECTORY / "res/backgrounds/circular-mask.png")

        # Display preview in the window
        if not error_in_theme:
            screen_image = display.lcd.screen_image
            if config.THEME_DATA["display"].get("DISPLAY_SIZE", '3.5"') == '2.1"':
                # This is a circular screen: apply a circle mask over the preview
                screen_image.paste(circular_mask, mask=circular_mask)
            display_image = ImageTk.PhotoImage(
                screen_image.resize(
                    (int(screen_image.width / RESIZE_FACTOR), int(screen_image.height / RESIZE_FACTOR))))
        else:
            size = display_width if display_width < display_height else display_height
            display_image = ImageTk.PhotoImage(ERROR_IN_THEME.resize((size, size)))
        viewer_picture = tkinter.Label(viewer, image=display_image, borderwidth=0)
        viewer_picture.place(x=RGB_LED_MARGIN, y=RGB_LED_MARGIN)

        # Allow to click on preview to show coordinates and draw zones
        viewer_picture.bind("<ButtonPress-1>", on_button1_press)
        viewer_picture.bind("<B1-Motion>", on_button1_press_and_drag)
        viewer_picture.bind("<ButtonRelease-1>", on_button1_release)

        # Allow to resize editor using mouse wheel or buttons
        viewer.bind_all("<MouseWheel>", on_mousewheel)

        zoom_plus_btn = tkinter.Button(viewer, text="Zoom +", command=lambda: on_zoom_plus())
        zoom_plus_btn.place(x=RGB_LED_MARGIN, y=display_height + 2 * RGB_LED_MARGIN, height=30,
                            width=int(display_width / 2))

        zoom_minus_btn = tkinter.Button(viewer, text="Zoom -", command=lambda: on_zoom_minus())
        zoom_minus_btn.place(x=int(display_width / 2) + RGB_LED_MARGIN, y=display_height + 2 * RGB_LED_MARGIN,
                             height=30, width=int(display_width / 2))

        label_coord = tkinter.Label(viewer, text="Click or draw a zone to show coordinates")
        label_coord.place(x=0, y=display_height + 2 * RGB_LED_MARGIN + 40,
                          width=display_width + 2 * RGB_LED_MARGIN)

        label_info = tkinter.Label(viewer, text="This preview will reload when theme file is updated")
        label_info.place(x=0, y=display_height + 2 * RGB_LED_MARGIN + 60,
                         width=display_width + 2 * RGB_LED_MARGIN)

        label_zone = tkinter.Label(viewer, bg='#%02x%02x%02x' % tuple(map(lambda x: 255 - x, led_color)))
        label_zone.bind("<ButtonRelease-1>", on_zone_click)
        viewer.update()

        logger.debug(
            "You can now edit the theme file in the editor. When you save your changes, the preview window will "
            "update automatically")

        while current_resize_factor == RESIZE_FACTOR:
            # Every time the theme file is modified: reload preview
            if os.path.exists(theme_file) and os.path.getmtime(theme_file) > last_edit_time:
                logger.debug("The theme file has been updated, the preview window will refresh")
                try:
                    refresh_theme()
                    error_in_theme = False
                except Exception as e:
                    logger.error(f"Error in theme: {e}")
                    error_in_theme = True
                last_edit_time = os.path.getmtime(theme_file)

                # Update the preview.png that is in the theme folder
                display.lcd.screen_image.save(config.THEME_DATA['PATH'] + "preview.png", "PNG")

                # Display new picture
                if not error_in_theme:
                    screen_image = display.lcd.screen_image
                    if config.THEME_DATA["display"].get("DISPLAY_SIZE", '3.5"') == '2.1"':
                        # This is a circular screen: apply a circle mask over the preview
                        screen_image.paste(circular_mask, mask=circular_mask)
                    display_image = ImageTk.PhotoImage(
                        screen_image.resize(
                            (int(screen_image.width / RESIZE_FACTOR), int(screen_image.height / RESIZE_FACTOR))))
                else:
                    size = display_width if display_width < display_height else display_height
                    display_image = ImageTk.PhotoImage(ERROR_IN_THEME.resize((size, size)))
                viewer_picture.config(image=display_image)

                # Refresh RGB backplate LEDs color
                led_color = config.THEME_DATA['display'].get("DISPLAY_RGB_LED", (255, 255, 255))
                if isinstance(led_color, str):
                    led_color = tuple(map(int, led_color.split(', ')))
                viewer.configure(bg='#%02x%02x%02x' % led_color)
                label_zone.configure(bg='#%02x%02x%02x' % tuple(map(lambda x: 255 - x, led_color)))

            # Regularly update the viewer window even if content unchanged, or it will appear as "not responding"
            viewer.update()

            time.sleep(0.1)

        # Zoom level changed, reload editor
        logger.info(
            f"Zoom level changed from {current_resize_factor:.1f} to {RESIZE_FACTOR:.1f}, reloading theme editor")
        viewer.destroy()
