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

# This file is the system monitor configuration GUI

from library.pythoncheck import check_python_version

check_python_version()

import glob
import os
import platform
import subprocess
import sys
import webbrowser
import requests
import babel

try:
    import tkinter.ttk as ttk
    from tkinter import *
    from PIL import ImageTk
    import psutil
    import ruamel.yaml
    import sv_ttk
    from pathlib import Path
    from PIL import Image
    from serial.tools.list_ports import comports
    from TkToolTip.tooltip import ToolTip
except Exception as e:
    print("""Import error: %s
Please follow start guide to install required packages: https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start
Or the troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed""" % str(
        e))
    try:
        sys.exit(0)
    except:
        os._exit(0)

from library.sensors.sensors_python import sensors_fans, is_cpu_fan

TURING_MODEL = "Turing Smart Screen"
USBPCMONITOR_MODEL = "UsbPCMonitor"
XUANFANG_MODEL = "XuanFang rev. B & flagship"
KIPYE_MODEL = "Kipye Qiye Smart Display"
WEACT_MODEL = "WeAct Studio Display FS V1"
SIMULATED_MODEL = "Simulated screen"

SIZE_3_5_INCH = "3.5\""
SIZE_5_INCH = "5\""
SIZE_8_8_INCH = "8.8\""
SIZE_2_1_INCH = "2.1\""  # Only for retro compatibility
SIZE_2_x_INCH = "2.1\" / 2.8\""
SIZE_0_96_INCH = "0.96\""

size_list = (SIZE_0_96_INCH, SIZE_2_x_INCH, SIZE_3_5_INCH, SIZE_5_INCH, SIZE_8_8_INCH)

# Maps between config.yaml values and GUI description
revision_and_size_to_model_map = {
    ('A', SIZE_3_5_INCH): TURING_MODEL,  # Can also be UsbPCMonitor 3.5, does not matter since protocol is the same
    ('A', SIZE_5_INCH): USBPCMONITOR_MODEL,
    ('B', SIZE_3_5_INCH): XUANFANG_MODEL,
    ('C', SIZE_2_x_INCH): TURING_MODEL,
    ('C', SIZE_5_INCH): TURING_MODEL,
    ('C', SIZE_8_8_INCH): TURING_MODEL,
    ('D', SIZE_3_5_INCH): KIPYE_MODEL,
    ('WEACT_A', SIZE_3_5_INCH): WEACT_MODEL,
    ('WEACT_B', SIZE_0_96_INCH): WEACT_MODEL,
    ('SIMU', SIZE_0_96_INCH): SIMULATED_MODEL,
    ('SIMU', SIZE_2_x_INCH): SIMULATED_MODEL,
    ('SIMU', SIZE_3_5_INCH): SIMULATED_MODEL,
    ('SIMU', SIZE_5_INCH): SIMULATED_MODEL,
    ('SIMU', SIZE_8_8_INCH): SIMULATED_MODEL,
}
model_and_size_to_revision_map = {
    (TURING_MODEL, SIZE_3_5_INCH): 'A',
    (USBPCMONITOR_MODEL, SIZE_3_5_INCH): 'A',
    (USBPCMONITOR_MODEL, SIZE_5_INCH): 'A',
    (XUANFANG_MODEL, SIZE_3_5_INCH): 'B',
    (TURING_MODEL, SIZE_2_x_INCH): 'C',
    (TURING_MODEL, SIZE_5_INCH): 'C',
    (TURING_MODEL, SIZE_8_8_INCH): 'C',
    (KIPYE_MODEL, SIZE_3_5_INCH): 'D',
    (WEACT_MODEL, SIZE_3_5_INCH): 'WEACT_A',
    (WEACT_MODEL, SIZE_0_96_INCH): 'WEACT_B',
    (SIMULATED_MODEL, SIZE_0_96_INCH): 'SIMU',
    (SIMULATED_MODEL, SIZE_2_x_INCH): 'SIMU',
    (SIMULATED_MODEL, SIZE_3_5_INCH): 'SIMU',
    (SIMULATED_MODEL, SIZE_5_INCH): 'SIMU',
    (SIMULATED_MODEL, SIZE_8_8_INCH): 'SIMU',
}
hw_lib_map = {"AUTO": "Automatic", "LHM": "LibreHardwareMonitor (admin.)", "PYTHON": "Python libraries",
              "STUB": "Fake random data", "STATIC": "Fake static data"}
reverse_map = {False: "classic", True: "reverse"}
weather_unit_map = {"metric": "metric - °C", "imperial": "imperial - °F", "standard": "standard - °K"}
weather_lang_map = {"sq": "Albanian", "af": "Afrikaans", "ar": "Arabic", "az": "Azerbaijani", "eu": "Basque",
                    "be": "Belarusian", "bg": "Bulgarian", "ca": "Catalan", "zh_cn": "Chinese Simplified",
                    "zh_tw": "Chinese Traditional", "hr": "Croatian", "cz": "Czech", "da": "Danish", "nl": "Dutch",
                    "en": "English", "fi": "Finnish", "fr": "French", "gl": "Galician", "de": "German", "el": "Greek",
                    "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "is": "Icelandic", "id": "Indonesian",
                    "it": "Italian", "ja": "Japanese", "kr": "Korean", "ku": "Kurmanji (Kurdish)", "la": "Latvian",
                    "lt": "Lithuanian", "mk": "Macedonian", "no": "Norwegian", "fa": "Persian (Farsi)", "pl": "Polish",
                    "pt": "Portuguese", "pt_br": "Português Brasil", "ro": "Romanian", "ru": "Russian", "sr": "Serbian",
                    "sk": "Slovak", "sl": "Slovenian", "sp": "Spanish", "sv": "Swedish", "th": "Thai", "tr": "Turkish",
                    "ua": "Ukrainian", "vi": "Vietnamese", "zu": "Zulu"}

MAIN_DIRECTORY = str(Path(__file__).parent.resolve()) + "/"
THEMES_DIR = MAIN_DIRECTORY + 'res/themes'

circular_mask = Image.open(MAIN_DIRECTORY + "res/backgrounds/circular-mask.png")


def get_theme_data(name: str):
    folder = os.path.join(THEMES_DIR, name)
    # checking if it is a directory
    if os.path.isdir(folder):
        # Check if a theme.yaml file exists
        theme = os.path.join(folder, 'theme.yaml')
        if os.path.isfile(theme):
            # Get display size from theme.yaml
            with open(theme, "rt", encoding='utf8') as stream:
                theme_data, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)
                return theme_data
    return None


def get_themes(size: str):
    themes = []
    for filename in os.listdir(THEMES_DIR):
        theme_data = get_theme_data(filename)
        if theme_data and theme_data['display'].get("DISPLAY_SIZE", '3.5"') == size:
            themes.append(filename)
    return sorted(themes, key=str.casefold)


def get_theme_size(name: str) -> str:
    theme_data = get_theme_data(name)
    return theme_data['display'].get("DISPLAY_SIZE", '3.5"')


def get_com_ports():
    com_ports_names = ["Automatic detection"]  # Add manual entry on top for automatic detection
    for com_port in comports():
        com_ports_names.append(com_port.name)
    return com_ports_names


def get_net_if():
    if_list = list(psutil.net_if_addrs().keys())
    if_list.insert(0, "None")  # Add manual entry on top for unavailable/not selected interface
    return if_list


def get_fans():
    fan_list = list()
    auto_detected_cpu_fan = "None"
    for name, entries in sensors_fans().items():
        for entry in entries:
            fan_list.append("%s/%s (%d%% - %d RPM)" % (name, entry.label, entry.percent, entry.current))
            if (is_cpu_fan(entry.label) or is_cpu_fan(name)) and auto_detected_cpu_fan == "None":
                auto_detected_cpu_fan = f"Auto-detected: {name}/{entry.label}"

    fan_list.insert(0, auto_detected_cpu_fan)  # Add manual entry on top if auto-detection succeeded
    return fan_list


class TuringConfigWindow(Tk):
    def __init__(self):
        super().__init__()
        self.title('Turing System Monitor configuration')
        self.geometry("820x580")
        self.iconphoto(True, PhotoImage(file=f"{MAIN_DIRECTORY}/res/icons/monitor-icon-17865/64.png"))
        # When window gets focus again, reload theme preview in case it has been updated by theme editor
        self.bind("<FocusIn>", lambda *_: self.load_theme_preview())
        self.after(0, self.on_fan_speed_update)

        # Subwindow for weather/ping config.
        self.more_config_window = MoreConfigWindow(self)

        # Make TK look better with Sun Valley ttk theme
        self.app_theme = StringVar(value='light')
        sv_ttk.set_theme(self.app_theme.get())

        self.theme_preview_img = None
        self.theme_preview = ttk.Label(self)
        self.theme_preview.place(x=10, y=10)

        self.theme_author = ttk.Label(self)

        sysmon_label = ttk.Label(self, text='Display configuration', font='bold')
        sysmon_label.place(x=370, y=0)

        self.model_label = ttk.Label(self, text='Smart screen model')
        self.model_label.place(x=370, y=35)
        self.model_cb = ttk.Combobox(self, values=list(dict.fromkeys((revision_and_size_to_model_map.values()))),
                                     state='readonly')
        self.model_cb.bind('<<ComboboxSelected>>', lambda *_: self.on_model_change())
        self.model_cb.place(x=550, y=30, width=250)

        self.size_label = ttk.Label(self, text='Smart screen size')
        self.size_label.place(x=370, y=75)
        self.size_cb = ttk.Combobox(self, values=size_list, state='readonly')
        self.size_cb.bind('<<ComboboxSelected>>', lambda *_: self.on_size_change())
        self.size_cb.place(x=550, y=70, width=250)

        self.com_label = ttk.Label(self, text='COM port')
        self.com_label.place(x=370, y=115)
        self.com_cb = ttk.Combobox(self, values=get_com_ports(), state='readonly')
        self.com_cb.place(x=550, y=110, width=250)

        self.orient_label = ttk.Label(self, text='Orientation')
        self.orient_label.place(x=370, y=155)
        self.orient_cb = ttk.Combobox(self, values=list(reverse_map.values()), state='readonly')
        self.orient_cb.place(x=550, y=150, width=250)

        self.brightness_string = StringVar()
        self.brightness_label = ttk.Label(self, text='Brightness')
        self.brightness_label.place(x=370, y=195)
        self.brightness_slider = ttk.Scale(self, from_=0, to=100, orient=HORIZONTAL,
                                           command=lambda *_: self.on_brightness_change())
        self.brightness_slider.place(x=600, y=195, width=180)
        self.brightness_val_label = ttk.Label(self, textvariable=self.brightness_string)
        self.brightness_val_label.place(x=550, y=195)
        self.brightness_warning_label = ttk.Label(self,
                                                  text="⚠ Turing 3.5\" displays can get hot at high brightness!",
                                                  foreground='#ff8c00')

        sysmon_label = ttk.Label(self, text='System Monitor Configuration', font='bold')
        sysmon_label.place(x=370, y=260)

        self.theme_label = ttk.Label(self, text='Theme')
        self.theme_label.place(x=370, y=300)
        self.theme_cb = ttk.Combobox(self, state='readonly')
        self.theme_cb.place(x=550, y=295, width=250)
        self.theme_cb.bind('<<ComboboxSelected>>', lambda *_: self.load_theme_preview())

        self.hwlib_label = ttk.Label(self, text='Hardware monitoring')
        self.hwlib_label.place(x=370, y=340)
        if sys.platform != "win32":
            del hw_lib_map["LHM"]  # LHM is for Windows platforms only
        self.hwlib_cb = ttk.Combobox(self, values=list(hw_lib_map.values()), state='readonly')
        self.hwlib_cb.place(x=550, y=335, width=250)
        self.hwlib_cb.bind('<<ComboboxSelected>>', lambda *_: self.on_hwlib_change())

        self.eth_label = ttk.Label(self, text='Ethernet interface')
        self.eth_label.place(x=370, y=380)
        self.eth_cb = ttk.Combobox(self, values=get_net_if(), state='readonly')
        self.eth_cb.place(x=550, y=375, width=250)

        self.wl_label = ttk.Label(self, text='Wi-Fi interface')
        self.wl_label.place(x=370, y=420)
        self.wl_cb = ttk.Combobox(self, values=get_net_if(), state='readonly')
        self.wl_cb.place(x=550, y=415, width=250)

        # For Windows platform only
        self.lhm_admin_warning = ttk.Label(self,
                                           text="❌ Restart as admin. or select another Hardware monitoring",
                                           foreground='#f00')
        # For platform != Windows
        self.cpu_fan_label = ttk.Label(self, text='CPU fan (？)')
        self.cpu_fan_label.config(foreground="#a3a3ff", cursor="hand2")
        self.cpu_fan_cb = ttk.Combobox(self, values=get_fans(), state='readonly')

        self.tooltip = ToolTip(self.cpu_fan_label,
                               msg="If \"None\" is selected, CPU fan was not auto-detected.\n"
                                   "Manually select your CPU fan from the list.\n\n"
                                   "Fans missing from the list? Install lm-sensors package\n"
                                   "and run 'sudo sensors-detect' command, then reboot.")

        self.weather_ping_btn = ttk.Button(self, text="Weather & ping",
                                           command=lambda: self.more_config_window.deiconify())
        self.weather_ping_btn.place(x=80, y=520, height=50, width=130)

        self.open_theme_folder_btn = ttk.Button(self, text="Open themes\nfolder",
                                                command=lambda: self.on_open_theme_folder_click())
        self.open_theme_folder_btn.place(x=220, y=520, height=50, width=130)

        self.edit_theme_btn = ttk.Button(self, text="Edit theme", command=lambda: self.on_theme_editor_click())
        self.edit_theme_btn.place(x=360, y=520, height=50, width=130)

        self.save_btn = ttk.Button(self, text="Save settings", command=lambda: self.save_config_values())
        self.save_btn.place(x=500, y=520, height=50, width=130)

        self.save_run_btn = ttk.Button(self, text="Save and run", command=lambda: self.on_saverun_click())
        self.save_run_btn.place(x=640, y=520, height=50, width=130)
        self.change_app_theme = ttk.Button(self, textvariable=self.app_theme, command=lambda: self.on_change_theme())
        self.change_app_theme.place(x=5, y=520, height=50, width=70)

        self.config = None
        self.load_config_values()

    def run(self):
        self.mainloop()

    def load_theme_preview(self):
        theme_data = get_theme_data(self.theme_cb.get())

        try:
            theme_preview = Image.open(f"{MAIN_DIRECTORY}res/themes/{self.theme_cb.get()}/preview.png")

            if theme_data['display'].get("DISPLAY_SIZE", '3.5"') == SIZE_2_1_INCH:
                # This is a circular screen: apply a circle mask over the preview
                theme_preview.paste(circular_mask, mask=circular_mask)
        except:
            theme_preview = Image.open(f"{MAIN_DIRECTORY}res/docs/no-preview.png")
        finally:
            theme_preview.thumbnail((320, 480), Image.Resampling.LANCZOS)
            self.theme_preview_img = ImageTk.PhotoImage(theme_preview)
            self.theme_preview.config(image=self.theme_preview_img)

            author_name = theme_data.get('author', 'unknown')
            self.theme_author.config(text=f"Author: {author_name}")
            if author_name.startswith("@"):
                self.theme_author.config(foreground="#a3a3ff", cursor="hand2")
                self.theme_author.bind("<Button-1>",
                                       lambda e: webbrowser.open_new_tab(f"https://github.com/{author_name[1:]}"))
            else:
                self.theme_author.config(foreground="#a3a3a3", cursor="")
                self.theme_author.unbind("<Button-1>")
            self.theme_author.place(x=10, y=self.theme_preview_img.height() + 15)

    def load_config_values(self):
        with open(MAIN_DIRECTORY + "config.yaml", "rt", encoding='utf8') as stream:
            self.config, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)

        # Check if theme is valid
        if get_theme_data(self.config['config']['THEME']) is None:
            # Theme from config.yaml is not valid: use first theme available default size 3.5"
            self.config['config']['THEME'] = get_themes(SIZE_3_5_INCH)[0]

        try:
            self.theme_cb.set(self.config['config']['THEME'])
        except:
            self.theme_cb.set("")

        self.load_theme_preview()

        try:
            self.hwlib_cb.set(hw_lib_map[self.config['config']['HW_SENSORS']])
        except:
            self.hwlib_cb.current(0)

        try:
            if self.config['config']['ETH'] == "":
                self.eth_cb.current(0)
            else:
                self.eth_cb.set(self.config['config']['ETH'])
        except:
            self.eth_cb.current(0)

        try:
            if self.config['config']['WLO'] == "":
                self.wl_cb.current(0)
            else:
                self.wl_cb.set(self.config['config']['WLO'])
        except:
            self.wl_cb.current(0)

        try:
            if self.config['config']['COM_PORT'] == "AUTO":
                self.com_cb.current(0)
            else:
                self.com_cb.set(self.config['config']['COM_PORT'])
        except:
            self.com_cb.current(0)

        # Guess display size from theme in the configuration
        size = get_theme_size(self.config['config']['THEME'])
        size = size.replace(SIZE_2_1_INCH, SIZE_2_x_INCH)  # If a theme is for 2.1" then it also is for 2.8"
        try:
            self.size_cb.set(size)
        except:
            self.size_cb.current(0)

        # Guess model from revision and size
        revision = self.config['display']['REVISION']
        try:
            self.model_cb.set(revision_and_size_to_model_map[(revision, size)])
        except:
            self.model_cb.current(0)

        try:
            self.orient_cb.set(reverse_map[self.config['display']['DISPLAY_REVERSE']])
        except:
            self.orient_cb.current(0)

        try:
            self.brightness_slider.set(int(self.config['display']['BRIGHTNESS']))
        except:
            self.brightness_slider.set(50)

        try:
            if self.config['config']['CPU_FAN'] == "AUTO":
                self.cpu_fan_cb.current(0)
            else:
                self.cpu_fan_cb.set(self.config['config']['CPU_FAN'])
        except:
            self.cpu_fan_cb.current(0)

        # Reload content on screen
        self.on_model_change()
        self.on_size_change()
        self.load_theme_preview()
        self.on_brightness_change()
        self.on_hwlib_change()

        # Load configuration to sub-window as well
        self.more_config_window.load_config_values(self.config)

    def save_config_values(self):
        self.config['config']['THEME'] = self.theme_cb.get()
        self.config['config']['HW_SENSORS'] = [k for k, v in hw_lib_map.items() if v == self.hwlib_cb.get()][0]
        self.config['config']['ETH'] = self.eth_cb.get() if self.eth_cb.current() != 0 else ""
        self.config['config']['WLO'] = self.wl_cb.get() if self.wl_cb.current() != 0 else ""
        self.config['config']['COM_PORT'] = self.com_cb.get() if self.com_cb.current() != 0 else "AUTO"
        self.config['config']['CPU_FAN'] = self.cpu_fan_cb.get().split(' ')[0] if self.cpu_fan_cb.current() != 0 else "AUTO"
        self.config['display']['REVISION'] = model_and_size_to_revision_map[(self.model_cb.get(), self.size_cb.get())]
        self.config['display']['DISPLAY_REVERSE'] = [k for k, v in reverse_map.items() if v == self.orient_cb.get()][0]
        self.config['display']['BRIGHTNESS'] = int(self.brightness_slider.get())

        with open(MAIN_DIRECTORY + "config.yaml", "w", encoding='utf-8') as file:
            ruamel.yaml.YAML().dump(self.config, file)

    def save_additional_config(self, ping: str, api_key: str, lat: str, long: str, unit: str, lang: str):
        self.config['config']['PING'] = ping
        self.config['config']['WEATHER_API_KEY'] = api_key
        self.config['config']['WEATHER_LATITUDE'] = lat
        self.config['config']['WEATHER_LONGITUDE'] = long
        self.config['config']['WEATHER_UNITS'] = unit
        self.config['config']['WEATHER_LANGUAGE'] = lang

        with open(MAIN_DIRECTORY + "config.yaml", "w", encoding='utf-8') as file:
            ruamel.yaml.YAML().dump(self.config, file)

    def on_open_theme_folder_click(self):
        path = f'{MAIN_DIRECTORY}/res/themes'
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def on_theme_editor_click(self):
        from theme_editor import main
        main(self.theme_cb.get())

    def on_change_theme(self):
        if self.app_theme.get() == 'light':
            self.app_theme.set('dark')
        else:
            self.app_theme.set('light')
        sv_ttk.set_theme(self.app_theme.get())

    def on_saverun_click(self):
        self.save_config_values()
        subprocess.Popen(f'"{MAIN_DIRECTORY}{glob.glob("main.*", root_dir=MAIN_DIRECTORY)[0]}"', shell=True)
        self.destroy()

    def on_brightness_change(self):
        self.brightness_string.set(f"{int(self.brightness_slider.get())} %")
        self.show_hide_brightness_warning()

    def on_model_change(self):
        self.show_hide_brightness_warning()
        if self.model_cb.get() == SIMULATED_MODEL:
            self.com_cb.configure(state="disabled", foreground="#C0C0C0")
            self.orient_cb.configure(state="disabled", foreground="#C0C0C0")
            self.brightness_slider.configure(state="disabled")
            self.brightness_val_label.configure(foreground="#C0C0C0")
        else:
            self.com_cb.configure(state="readonly", foreground="#000")
            self.orient_cb.configure(state="readonly", foreground="#000")
            self.brightness_slider.configure(state="normal")
            self.brightness_val_label.configure(foreground="#000")

    def on_size_change(self):
        size = self.size_cb.get()
        size = size.replace(SIZE_2_x_INCH,
                            SIZE_2_1_INCH)  # For '2.1" / 2.8"' size, keep '2.1"' as size to get themes for
        themes = get_themes(size)
        self.theme_cb.config(values=themes)

        if not self.theme_cb.get() in themes:
            # The selected theme does not exist anymore / is not allowed for this screen model : select 1st theme avail.
            self.theme_cb.set(themes[0])

        self.show_hide_brightness_warning()

    def on_hwlib_change(self):
        hwlib = [k for k, v in hw_lib_map.items() if v == self.hwlib_cb.get()][0]
        if hwlib in ["STUB", "STATIC"]:
            self.eth_cb.configure(state="disabled", foreground="#C0C0C0")
            self.wl_cb.configure(state="disabled", foreground="#C0C0C0")
        else:
            self.eth_cb.configure(state="readonly", foreground="#000")
            self.wl_cb.configure(state="readonly", foreground="#000")

        if sys.platform == "win32":
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if (hwlib in ["LHM", "AUTO"]) and not is_admin:
                self.lhm_admin_warning.place(x=370, y=460)
                self.save_run_btn.state(["disabled"])
            else:
                self.lhm_admin_warning.place_forget()
                self.save_run_btn.state(["!disabled"])
        else:
            if hwlib in ["PYTHON", "AUTO"]:
                self.cpu_fan_label.place(x=370, y=460)
                self.cpu_fan_cb.place(x=550, y=455, width=250)
            else:
                self.cpu_fan_label.place_forget()
                self.cpu_fan_cb.place_forget()

    def show_hide_brightness_warning(self):
        if int(self.brightness_slider.get()) > 50 and self.model_cb.get() == TURING_MODEL and self.size_cb.get() == SIZE_3_5_INCH:
            # Show warning for Turing Smart screen 3.5 with high brightness
            self.brightness_warning_label.place(x=370, y=225)
        else:
            self.brightness_warning_label.place_forget()

    def on_fan_speed_update(self):
        # Update fan speed periodically
        prev_value = self.cpu_fan_cb.current()  # Save currently selected index
        self.cpu_fan_cb.config(values=get_fans())
        if prev_value != -1:
            self.cpu_fan_cb.current(prev_value)  # Force select same index to refresh displayed value
        self.after(500, self.on_fan_speed_update)


class MoreConfigWindow(Toplevel):
    def __init__(self, main_window: TuringConfigWindow):
        super().__init__(main_window)
        self.withdraw()
        self.title('Configure weather & ping')
        self.geometry("750x680")

        self.main_window = main_window

        self.ping_label = ttk.Label(self, text='Hostname / IP to ping')
        self.ping_label.place(x=10, y=10)
        self.ping_entry = ttk.Entry(self)
        self.ping_entry.place(x=190, y=5, width=250)

        weather_label = ttk.Label(self, text='Weather forecast (OpenWeatherMap API)', font='bold')
        weather_label.place(x=10, y=70)

        weather_info_label = ttk.Label(self,
                                       text="To display weather forecast on themes that support it, you need an OpenWeatherMap \"One Call API 3.0\" key.\n"
                                            "You will get 1,000 API calls per day for free. This program is configured to stay under this threshold (~300 calls/day).")
        weather_info_label.place(x=10, y=100)
        weather_api_link_label = ttk.Label(self,
                                           text="Click here to subscribe to OpenWeatherMap One Call API 3.0.")
        weather_api_link_label.place(x=10, y=140)
        weather_api_link_label.config(foreground="#a3a3ff", cursor="hand2")
        weather_api_link_label.bind("<Button-1>",
                                    lambda e: webbrowser.open_new_tab("https://openweathermap.org/api"))

        self.api_label = ttk.Label(self, text='OpenWeatherMap API key')
        self.api_label.place(x=10, y=170)
        self.api_entry = ttk.Entry(self)
        self.api_entry.place(x=190, y=165, width=250)

        latlong_label = ttk.Label(self,
                                  text="You can use online services to get your latitude/longitude e.g. latlong.net (click here)")
        latlong_label.place(x=10, y=210)
        latlong_label.config(foreground="#a3a3ff", cursor="hand2")
        latlong_label.bind("<Button-1>",
                           lambda e: webbrowser.open_new_tab("https://www.latlong.net/"))

        self.lat_label = ttk.Label(self, text='Latitude')
        self.lat_label.place(x=10, y=250)
        self.lat_entry = ttk.Entry(self, validate='key',
                                   validatecommand=(self.register(self.validateCoord), '%P'))
        self.lat_entry.place(x=80, y=245, width=100)

        self.long_label = ttk.Label(self, text='Longitude')
        self.long_label.place(x=270, y=250)
        self.long_entry = ttk.Entry(self, validate='key',
                                    validatecommand=(self.register(self.validateCoord), '%P'))
        self.long_entry.place(x=340, y=245, width=100)

        self.unit_label = ttk.Label(self, text='Units')
        self.unit_label.place(x=10, y=290)
        self.unit_cb = ttk.Combobox(self, values=list(weather_unit_map.values()), state='readonly')
        self.unit_cb.place(x=190, y=285, width=250)

        self.lang_label = ttk.Label(self, text='Language')
        self.lang_label.place(x=10, y=330)
        self.lang_cb = ttk.Combobox(self, values=list(weather_lang_map.values()), state='readonly')
        self.lang_cb.place(x=190, y=325, width=250)

        self.citysearch1_label = ttk.Label(self, text='Location search', font='bold')
        self.citysearch1_label.place(x=80, y=370)

        self.citysearch2_label = ttk.Label(self,
                                           text="Enter location to automatically get coordinates (latitude/longitude).\n"
                                                "For example \"Berlin\" \"London, GB\", \"London, Quebec\".\n"
                                                "Remember to set valid API key and pick language first!")
        self.citysearch2_label.place(x=10, y=396)

        self.citysearch3_label = ttk.Label(self, text="Enter location")
        self.citysearch3_label.place(x=10, y=474)
        self.citysearch_entry = ttk.Entry(self)
        self.citysearch_entry.place(x=140, y=470, width=300)
        self.citysearch_btn = ttk.Button(self, text="Search", command=lambda: self.on_search_click())
        self.citysearch_btn.place(x=450, y=468, height=40, width=130)

        self.citysearch4_label = ttk.Label(self, text="Select location\n(use after Search)")
        self.citysearch4_label.place(x=10, y=540)
        self.citysearch_cb = ttk.Combobox(self, values=[], state='readonly')
        self.citysearch_cb.place(x=140, y=544, width=360)
        self.citysearch_btn2 = ttk.Button(self, text="Fill in lat/long", command=lambda: self.on_filllatlong_click())
        self.citysearch_btn2.place(x=520, y=540, height=40, width=130)

        self.citysearch_warn_label = ttk.Label(self, text="")
        self.citysearch_warn_label.place(x=20, y=600)
        self.citysearch_warn_label.config(foreground="#ff0000")

        self.save_btn = ttk.Button(self, text="Save settings", command=lambda: self.on_save_click())
        self.save_btn.place(x=590, y=620, height=50, width=130)

        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self._city_entries = []

    def validateCoord(self, coord: str):
        if not coord:
            return True
        try:
            float(coord)
        except:
            return False
        return True

    def load_config_values(self, config):
        self.config = config

        try:
            self.ping_entry.insert(0, self.config['config']['PING'])
        except:
            self.ping_entry.insert(0, "8.8.8.8")

        try:
            self.api_entry.insert(0, self.config['config']['WEATHER_API_KEY'])
        except:
            pass

        try:
            self.lat_entry.insert(0, self.config['config']['WEATHER_LATITUDE'])
        except:
            self.lat_entry.insert(0, "45.75")

        try:
            self.long_entry.insert(0, self.config['config']['WEATHER_LONGITUDE'])
        except:
            self.long_entry.insert(0, "45.75")

        try:
            self.unit_cb.set(weather_unit_map[self.config['config']['WEATHER_UNITS']])
        except:
            self.unit_cb.set(0)

        try:
            self.lang_cb.set(weather_lang_map[self.config['config']['WEATHER_LANGUAGE']])
        except:
            self.lang_cb.set(weather_lang_map["en"])

    def citysearch_show_warning(self, warning):
        self.citysearch_warn_label.config(text=warning)

    def on_search_click(self):
        OPENWEATHER_GEOAPI_URL = "http://api.openweathermap.org/geo/1.0/direct"
        api_key = self.api_entry.get()
        lang = [k for k, v in weather_lang_map.items() if v == self.lang_cb.get()][0]
        city = self.citysearch_entry.get()

        if len(api_key) == 0 or len(city) == 0:
            self.citysearch_show_warning("API key and city name cannot be empty.")
            return

        try:
            request = requests.get(OPENWEATHER_GEOAPI_URL, timeout=5, params={"appid": api_key, "lang": lang,
                                                                              "q": city, "limit": 10})
        except:
            self.citysearch_show_warning("Error fetching OpenWeatherMap Geo API")
            return

        if request.status_code == 401:
            self.citysearch_show_warning("Invalid OpenWeatherMap API key.")
            return
        elif request.status_code != 200:
            self.citysearch_show_warning(f"Error #{request.status_code} fetching OpenWeatherMap Geo API.")
            return

        self._city_entries = []
        cb_entries = []
        for entry in request.json():
            name = entry['name']
            state = entry.get('state', None)
            lat = entry['lat']
            long = entry['lon']
            country_code = entry['country'].upper()
            country = babel.Locale(lang).territories[country_code]
            if state is not None:
                full_name = f"{name}, {state}, {country}"
            else:
                full_name = f"{name}, {country}"
            self._city_entries.append({"full_name": full_name, "lat": str(lat), "long": str(long)})
            cb_entries.append(full_name)

        self.citysearch_cb.config(values=cb_entries)
        if not cb_entries:
            self.citysearch_show_warning("No given city found.")
        else:
            self.citysearch_cb.current(0)
            self.citysearch_show_warning("Select your city now from list and apply \"Fill in lat/long\".")

    def on_filllatlong_click(self):
        if not self._city_entries:
            self.citysearch_show_warning("No city selected or no search results.")
            return
        city = [i for i in self._city_entries if i['full_name'] == self.citysearch_cb.get()][0]
        self.lat_entry.delete(0, END)
        self.lat_entry.insert(0, city['lat'])
        self.long_entry.delete(0, END)
        self.long_entry.insert(0, city['long'])
        self.citysearch_show_warning(f"Lat/long values filled for {city['full_name']}")

    def on_save_click(self):
        self.save_config_values()
        self.withdraw()

    def save_config_values(self):
        ping = self.ping_entry.get()
        api_key = self.api_entry.get()
        lat = self.lat_entry.get()
        long = self.long_entry.get()
        unit = [k for k, v in weather_unit_map.items() if v == self.unit_cb.get()][0]
        lang = [k for k, v in weather_lang_map.items() if v == self.lang_cb.get()][0]

        self.main_window.save_additional_config(ping, api_key, lat, long, unit, lang)


if __name__ == "__main__":
    configurator = TuringConfigWindow()
    configurator.run()
