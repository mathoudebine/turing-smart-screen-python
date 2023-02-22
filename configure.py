import os
import subprocess
from tkinter import *
from tkinter.ttk import Combobox

import psutil
import ruamel.yaml
from PIL import Image, ImageTk
from serial.tools.list_ports import comports

# Maps between config.yaml values and GUI description
revision_map = {'A': "Turing / rev. A", 'B': "XuanFang / rev. B / flagship", 'SIMU': "Simulated screen"}
hw_lib_map = {"AUTO": "Automatic", "LHM": "LibreHardwareMonitor (Win.)", "PYTHON": "Python libraries (all OS)",
              "STUB": "Fake random data", "STATIC": "Fake static data"}
reverse_map = {False: "classic", True: "reverse"}


def get_themes():
    themes = []
    directory = 'res/themes/'
    for filename in os.listdir('res/themes'):
        f = os.path.join(directory, filename)
        # checking if it is a file
        if os.path.isdir(f):
            theme = os.path.join(f, 'theme.yaml')
            if os.path.isfile(theme):
                themes.append(filename)
    return themes


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
        self.window.geometry("680x450")
        self.window.iconphoto(True, PhotoImage(file="res/icons/monitor-icon-17865/64.png"))

        self.theme_preview_img = None
        self.theme_preview = Label(self.window)
        self.theme_preview.place(x=10, y=10)

        sysmon_label = Label(self.window, text='System Monitor configuration', font='bold')
        sysmon_label.place(x=320, y=0)

        self.theme_label = Label(self.window, text='Theme')
        self.theme_label.place(x=320, y=40)
        self.theme_cb = Combobox(self.window, values=get_themes(), state='readonly')
        self.theme_cb.place(x=500, y=40, width=170)
        self.theme_cb.bind('<<ComboboxSelected>>', self.on_theme_change)

        self.hwlib_label = Label(self.window, text='Hardware Monitoring library')
        self.hwlib_label.place(x=320, y=70)
        self.hwlib_cb = Combobox(self.window, values=list(hw_lib_map.values()))
        self.hwlib_cb.place(x=500, y=70, width=170)

        self.eth_label = Label(self.window, text='Ethernet interface')
        self.eth_label.place(x=320, y=100)
        self.eth_cb = Combobox(self.window, values=get_net_if())
        self.eth_cb.place(x=500, y=100, width=170)

        self.wl_label = Label(self.window, text='Wi-Fi interface')
        self.wl_label.place(x=320, y=130)
        self.wl_cb = Combobox(self.window, values=get_net_if())
        self.wl_cb.place(x=500, y=130, width=170)

        sysmon_label = Label(self.window, text='Display configuration', font='bold')
        sysmon_label.place(x=320, y=180)

        self.com_label = Label(self.window, text='COM port')
        self.com_label.place(x=320, y=220)
        self.com_cb = Combobox(self.window, values=get_com_ports())
        self.com_cb.place(x=500, y=220, width=170)

        self.model_label = Label(self.window, text='Smart screen model')
        self.model_label.place(x=320, y=250)
        self.model_cb = Combobox(self.window, values=list(revision_map.values()))
        self.model_cb.place(x=500, y=250, width=170)

        self.orient_label = Label(self.window, text='Orientation')
        self.orient_label.place(x=320, y=280)
        self.orient_cb = Combobox(self.window, values=list(reverse_map.values()))
        self.orient_cb.place(x=500, y=280, width=170)

        self.brightness_label = Label(self.window, text='Brightness')
        self.brightness_label.place(x=320, y=310)
        self.brightness_slider = Scale(self.window, from_=0, to=100, orient=HORIZONTAL)
        self.brightness_slider.place(x=500, y=305, width=170)

        self.edit_theme_btn = Button(self.window, text="Theme Editor", command=lambda: self.on_theme_editor_click())
        self.edit_theme_btn.place(x=320, y=380, height=50, width=100)

        self.save_btn = Button(self.window, text="Save settings", command=lambda: self.on_save_click())
        self.save_btn.place(x=440, y=380, height=50, width=100)

        self.save_run_btn = Button(self.window, text="Save and run", command=lambda: self.on_saverun_click())
        self.save_run_btn.place(x=560, y=380, height=50, width=100)

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

        self.theme_cb.set(self.config['config']['THEME'])
        self.load_theme_preview()
        self.hwlib_cb.set(hw_lib_map[self.config['config']['HW_SENSORS']])
        if self.config['config']['ETH'] == "":
            self.eth_cb.current(0)
        else:
            self.eth_cb.set(self.config['config']['ETH'])
        if self.config['config']['WLO'] == "":
            self.wl_cb.current(0)
        else:
            self.wl_cb.set(self.config['config']['WLO'])
        if self.config['config']['COM_PORT'] == "AUTO":
            self.com_cb.current(0)
        else:
            self.com_cb.set(self.config['config']['COM_PORT'])
        self.model_cb.set(revision_map[self.config['display']['REVISION']])
        self.orient_cb.set(reverse_map[self.config['display']['DISPLAY_REVERSE']])
        self.brightness_slider.set(int(self.config['display']['BRIGHTNESS']))

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
        self.config['display']['BRIGHTNESS'] = self.brightness_slider.get()

        with open("config.yaml", "w") as file:
            ruamel.yaml.YAML().dump(self.config, file)

    def on_theme_change(self, event):
        self.load_theme_preview()

    def on_theme_editor_click(self):
        subprocess.Popen("theme-editor.py " + self.theme_cb.get(), shell=True)

    def on_save_click(self):
        self.save_config_values()

    def on_saverun_click(self):
        self.save_config_values()
        subprocess.Popen("main.py", shell=True)
        self.window.destroy()


if __name__ == "__main__":
    configurator = TuringConfigWindow()
    configurator.run()
