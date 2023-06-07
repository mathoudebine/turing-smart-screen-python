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

# This file is the system monitor configuration GUI


import os
import subprocess
import sys

MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import tkinter.ttk as ttk
    from tkinter import *
except:
    print(
        "[ERROR] Tkinter dependency not installed. Please follow troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed")
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import psutil
    import ruamel.yaml
    import sv_ttk
    from PIL import Image, ImageTk
    from serial.tools.list_ports import comports
except:
    print(
        "[ERROR] Python dependencies not installed. Please follow start guide: https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start")
    try:
        sys.exit(0)
    except:
        os._exit(0)

# Maps between config.yaml values and GUI description
revision_map = {'A': "Turing 3.5\" / rev. A", 'B': "XuanFang / rev. B / flagship", 'C': "Turing 5\"",
                'SIMU': "Simulated 3.5\" screen", 'SIMU5': "Simulated 5\" screen"}
hw_lib_map = {"AUTO": "Automatic", "LHM": "LibreHardwareMonitor (admin.)", "PYTHON": "Python libraries",
              "STUB": "Fake random data", "STATIC": "Fake static data"}
reverse_map = {False: "classic", True: "reverse"}
revision_size = {'A': '3.5"', 'B': '3.5"', 'C': '5"', 'SIMU': '3.5"', 'SIMU5': '5"'}


def get_themes(revision: str):
    themes = []
    directory = 'res/themes/'
    for filename in os.listdir('res/themes'):
        dir = os.path.join(directory, filename)
        # checking if it is a directory
        if os.path.isdir(dir):
            # Check if a theme.yaml file exists
            theme = os.path.join(dir, 'theme.yaml')
            if os.path.isfile(theme):
                # Get display size from theme.yaml
                with open(theme, "rt", encoding='utf8') as stream:
                    theme_data, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)
                    if theme_data['display'].get("DISPLAY_SIZE", '3.5"') == revision_size[revision]:
                        themes.append(filename)
    return sorted(themes, key=str.casefold)


def get_com_ports():
    com_ports_names = ["Automatic detection"]  # Add manual entry on top for automatic detection
    com_ports = comports()
    for com_port in com_ports:
        com_ports_names.append(com_port.name)
    return com_ports_names


def get_net_if():
    if_list = list(psutil.net_if_addrs().keys())
    if_list.insert(0, "None")  # Add manual entry on top for unavailable/not selected interface
    return if_list


class TuringConfigWindow:
    def __init__(self):
        self.window = Tk()
        self.window.title('Turing System Monitor configuration')
        self.window.geometry("730x510")
        self.window.iconphoto(True, PhotoImage(file="res/icons/monitor-icon-17865/64.png"))
        # When window gets focus again, reload theme preview in case it has been updated by theme editor
        self.window.bind("<FocusIn>", self.on_theme_change)

        # Make TK look better with Sun Valley ttk theme
        sv_ttk.set_theme("light")

        self.theme_preview_img = None
        self.theme_preview = ttk.Label(self.window)
        self.theme_preview.place(x=10, y=10)

        sysmon_label = ttk.Label(self.window, text='System Monitor configuration', font='bold')
        sysmon_label.place(x=320, y=0)

        self.theme_label = ttk.Label(self.window, text='Theme')
        self.theme_label.place(x=320, y=35)
        self.theme_cb = ttk.Combobox(self.window, state='readonly')
        self.theme_cb.place(x=500, y=30, width=210)
        self.theme_cb.bind('<<ComboboxSelected>>', self.on_theme_change)

        self.hwlib_label = ttk.Label(self.window, text='Hardware monitoring')
        self.hwlib_label.place(x=320, y=75)
        if sys.platform != "win32":
            del hw_lib_map["LHM"]  # LHM is for Windows platforms only
        self.hwlib_cb = ttk.Combobox(self.window, values=list(hw_lib_map.values()), state='readonly')
        self.hwlib_cb.place(x=500, y=70, width=210)
        self.hwlib_cb.bind('<<ComboboxSelected>>', self.on_hwlib_change)

        self.eth_label = ttk.Label(self.window, text='Ethernet interface')
        self.eth_label.place(x=320, y=115)
        self.eth_cb = ttk.Combobox(self.window, values=get_net_if(), state='readonly')
        self.eth_cb.place(x=500, y=110, width=210)

        self.wl_label = ttk.Label(self.window, text='Wi-Fi interface')
        self.wl_label.place(x=320, y=155)
        self.wl_cb = ttk.Combobox(self.window, values=get_net_if(), state='readonly')
        self.wl_cb.place(x=500, y=150, width=210)

        self.lhm_admin_warning = ttk.Label(self.window,
                                           text="❌ Restart as admin. or select another Hardware monitoring",
                                           foreground='#f00')

        sysmon_label = ttk.Label(self.window, text='Display configuration', font='bold')
        sysmon_label.place(x=320, y=220)

        self.model_label = ttk.Label(self.window, text='Smart screen model')
        self.model_label.place(x=320, y=265)
        self.model_cb = ttk.Combobox(self.window, values=list(revision_map.values()), state='readonly')
        self.model_cb.bind('<<ComboboxSelected>>', self.on_model_change)
        self.model_cb.place(x=500, y=260, width=210)

        self.com_label = ttk.Label(self.window, text='COM port')
        self.com_label.place(x=320, y=305)
        self.com_cb = ttk.Combobox(self.window, values=get_com_ports(), state='readonly')
        self.com_cb.place(x=500, y=300, width=210)

        self.orient_label = ttk.Label(self.window, text='Orientation')
        self.orient_label.place(x=320, y=345)
        self.orient_cb = ttk.Combobox(self.window, values=list(reverse_map.values()), state='readonly')
        self.orient_cb.place(x=500, y=340, width=210)

        self.brightness_string = StringVar()
        self.brightness_label = ttk.Label(self.window, text='Brightness')
        self.brightness_label.place(x=320, y=385)
        self.brightness_slider = ttk.Scale(self.window, from_=0, to=100, orient=HORIZONTAL,
                                           command=self.on_brightness_change)
        self.brightness_slider.place(x=550, y=380, width=160)
        self.brightness_val_label = ttk.Label(self.window, textvariable=self.brightness_string)
        self.brightness_val_label.place(x=500, y=385)
        self.brightness_warning_label = ttk.Label(self.window,
                                                  text="⚠ Turing / rev. A displays can get hot at high brightness!",
                                                  foreground='#ff8c00')

        self.edit_theme_btn = ttk.Button(self.window, text="Edit theme", command=lambda: self.on_theme_editor_click())
        self.edit_theme_btn.place(x=310, y=450, height=50, width=130)

        self.save_btn = ttk.Button(self.window, text="Save settings", command=lambda: self.on_save_click())
        self.save_btn.place(x=450, y=450, height=50, width=130)

        self.save_run_btn = ttk.Button(self.window, text="Save and run", command=lambda: self.on_saverun_click())
        self.save_run_btn.place(x=590, y=450, height=50, width=130)

        self.config = None
        self.load_config_values()

    def run(self):
        self.window.mainloop()

    def load_theme_preview(self):
        try:
            theme_preview = Image.open("res/themes/" + self.theme_cb.get() + "/preview.png")
        except:
            theme_preview = Image.open("res/docs/no-preview.png")
        finally:
            if theme_preview.width > theme_preview.height:
                theme_preview = theme_preview.resize((300, 200), Image.Resampling.LANCZOS)
            else:
                theme_preview = theme_preview.resize((280, 420), Image.Resampling.LANCZOS)
            self.theme_preview_img = ImageTk.PhotoImage(theme_preview)
            self.theme_preview.config(image=self.theme_preview_img)

    def load_config_values(self):
        with open("config.yaml", "rt", encoding='utf8') as stream:
            self.config, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)

        try:
            self.theme_cb.set(self.config['config']['THEME'])
        except:
            self.theme_cb.current(0)
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

        try:
            self.model_cb.set(revision_map[self.config['display']['REVISION']])
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

        # Reload content on screen
        self.on_model_change()
        self.on_theme_change()
        self.on_brightness_change()
        self.on_hwlib_change()

    def save_config_values(self):
        self.config['config']['THEME'] = self.theme_cb.get()
        self.config['config']['HW_SENSORS'] = [k for k, v in hw_lib_map.items() if v == self.hwlib_cb.get()][0]
        if self.eth_cb.current() == 0:
            self.config['config']['ETH'] = ""
        else:
            self.config['config']['ETH'] = self.eth_cb.get()
        if self.wl_cb.current() == 0:
            self.config['config']['WLO'] = ""
        else:
            self.config['config']['WLO'] = self.wl_cb.get()
        if self.com_cb.current() == 0:
            self.config['config']['COM_PORT'] = "AUTO"
        else:
            self.config['config']['COM_PORT'] = self.com_cb.get()
        self.config['display']['REVISION'] = [k for k, v in revision_map.items() if v == self.model_cb.get()][0]
        self.config['display']['DISPLAY_REVERSE'] = [k for k, v in reverse_map.items() if v == self.orient_cb.get()][0]
        self.config['display']['BRIGHTNESS'] = int(self.brightness_slider.get())

        with open("config.yaml", "w", encoding='utf-8') as file:
            ruamel.yaml.YAML().dump(self.config, file)

    def on_theme_change(self, e=None):
        self.load_theme_preview()

    def on_theme_editor_click(self):
        subprocess.Popen(os.path.join(os.getcwd(), "theme-editor.py") + " \"" + self.theme_cb.get() + "\"", shell=True)

    def on_save_click(self):
        self.save_config_values()

    def on_saverun_click(self):
        self.save_config_values()
        subprocess.Popen(os.path.join(os.getcwd(), "main.py"), shell=True)
        self.window.destroy()

    def on_brightness_change(self, e=None):
        self.brightness_string.set(str(int(self.brightness_slider.get())) + "%")
        self.show_hide_brightness_warning()

    def on_model_change(self, e=None):
        self.show_hide_brightness_warning()
        revision = [k for k, v in revision_map.items() if v == self.model_cb.get()][0]
        if revision == "SIMU" or revision == "SIMU5":
            self.com_cb.configure(state="disabled", foreground="#C0C0C0")
            self.orient_cb.configure(state="disabled", foreground="#C0C0C0")
            self.brightness_slider.configure(state="disabled")
            self.brightness_val_label.configure(foreground="#C0C0C0")
        else:
            self.com_cb.configure(state="readonly", foreground="#000")
            self.orient_cb.configure(state="readonly", foreground="#000")
            self.brightness_slider.configure(state="normal")
            self.brightness_val_label.configure(foreground="#000")

        themes = get_themes(revision)
        self.theme_cb.config(values=themes)

        if not self.theme_cb.get() in themes:
            # The selected theme does not exist anymore / is not allowed for this screen model : select 1st theme avail.
            self.theme_cb.set(themes[0])

    def on_hwlib_change(self, e=None):
        hwlib = [k for k, v in hw_lib_map.items() if v == self.hwlib_cb.get()][0]
        if hwlib == "STUB" or hwlib == "STATIC":
            self.eth_cb.configure(state="disabled", foreground="#C0C0C0")
            self.wl_cb.configure(state="disabled", foreground="#C0C0C0")
        else:
            self.eth_cb.configure(state="readonly", foreground="#000")
            self.wl_cb.configure(state="readonly", foreground="#000")

        if sys.platform == "win32":
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if (hwlib == "LHM" or hwlib == "AUTO") and not is_admin:
                self.lhm_admin_warning.place(x=320, y=190)
                self.save_run_btn.state(["disabled"])
            else:
                self.lhm_admin_warning.place_forget()
                self.save_run_btn.state(["!disabled"])

    def show_hide_brightness_warning(self, e=None):
        if int(self.brightness_slider.get()) > 50 and [k for k, v in revision_map.items() if v == self.model_cb.get()][
            0] == "A":
            # Show warning for Turing Smart screen with high brightness
            self.brightness_warning_label.place(x=320, y=420)
        else:
            self.brightness_warning_label.place_forget()


if __name__ == "__main__":
    configurator = TuringConfigWindow()
    configurator.run()
