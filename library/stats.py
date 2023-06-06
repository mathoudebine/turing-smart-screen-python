# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022-2023  Rollbacke
# Copyright (C) 2022-2023  Ebag333
# Copyright (C) 2022-2023  w1ld3r
# Copyright (C) 2022-2023  Charles Ferguson (gerph)
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

import datetime
import locale
import math
import os
import platform
import sys

import babel.dates
from psutil._common import bytes2human

import library.config as config
from library.display import display
from library.log import logger

ETH_CARD = config.CONFIG_DATA["config"]["ETH"]
WLO_CARD = config.CONFIG_DATA["config"]["WLO"]
HW_SENSORS = config.CONFIG_DATA["config"]["HW_SENSORS"]

if HW_SENSORS == "PYTHON":
    if platform.system() == 'Windows':
        logger.warning("It is recommended to use LibreHardwareMonitor integration for Windows instead of Python "
                       "libraries (require admin. rights)")
    import library.sensors.sensors_python as sensors
elif HW_SENSORS == "LHM":
    if platform.system() == 'Windows':
        import library.sensors.sensors_librehardwaremonitor as sensors
    else:
        logger.error("LibreHardwareMonitor integration is only available on Windows")
        try:
            sys.exit(0)
        except:
            os._exit(0)
elif HW_SENSORS == "STUB":
    logger.warning("Stub sensors, not real HW sensors")
    import library.sensors.sensors_stub_random as sensors
elif HW_SENSORS == "STATIC":
    logger.warning("Stub sensors, not real HW sensors")
    import library.sensors.sensors_stub_static as sensors
elif HW_SENSORS == "AUTO":
    if platform.system() == 'Windows':
        import library.sensors.sensors_librehardwaremonitor as sensors
    else:
        import library.sensors.sensors_python as sensors
else:
    logger.error("Unsupported HW_SENSORS value in config.yaml")
    try:
        sys.exit(0)
    except:
        os._exit(0)


def get_full_path(path, name):
    if name:
        return path + name
    else:
        return None


class CPU:
    @staticmethod
    def percentage():
        cpu_percentage = sensors.Cpu.percentage(
            interval=config.THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", None))
        # logger.debug(f"CPU Percentage: {cpu_percentage}")

        if config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("SHOW", False):

            cpu_percentage_text = f"{int(cpu_percentage):>3}"
            if config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("SHOW_UNIT", True):
                cpu_percentage_text += "%"

            display.lcd.DisplayText(
                text=cpu_percentage_text,
                x=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT",
                                                                                 "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                             (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("X", 0),
                y=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("Y", 0),
                width=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("WIDTH", 0),
                height=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("HEIGHT", 0),
                value=int(cpu_percentage),
                min_value=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("MIN_VALUE", 0),
                max_value=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                              (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

    @staticmethod
    def frequency():
        if config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("SHOW", False):

            cpu_freq = f'{sensors.Cpu.frequency() / 1000:.2f}'
            if config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("SHOW_UNIT", True):
                cpu_freq += " GHz"

            display.lcd.DisplayText(
                text=cpu_freq,
                x=config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT",
                                                                                "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("BACKGROUND_COLOR",
                                                                                            (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

    @staticmethod
    def load():
        cpu_load = sensors.Cpu.load()
        # logger.debug(f"CPU Load: ({cpu_load[0]},{cpu_load[1]},{cpu_load[2]})")

        if config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("SHOW", False):

            cpu_load_one = f"{int(cpu_load[0]):>3}"
            if config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("SHOW_UNIT", True):
                cpu_load_one += "%"

            display.lcd.DisplayText(
                text=cpu_load_one,
                x=config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT",
                                                                                  "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                              (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("SHOW", False):

            cpu_load_five = f"{int(cpu_load[1]):>3}"
            if config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("SHOW_UNIT", True):
                cpu_load_five += "%"

            display.lcd.DisplayText(
                text=cpu_load_five,
                x=config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT",
                                                                                   "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                               (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get(
                                                   "BACKGROUND_IMAGE", None))
            )

        if config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("SHOW", False):

            cpu_load_fifteen = f"{int(cpu_load[2]):>3}"
            if config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("SHOW_UNIT", True):
                cpu_load_fifteen += "%"

            display.lcd.DisplayText(
                text=cpu_load_fifteen,
                x=config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT",
                                                                                      "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                  (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get(
                                                   "BACKGROUND_IMAGE", None))
            )

    @staticmethod
    def is_temperature_available():
        return sensors.Cpu.is_temperature_available()

    @staticmethod
    def temperature():
        if config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("SHOW", False):

            cpu_temp = f"{int(sensors.Cpu.temperature()):>3}"
            if config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("SHOW_UNIT", True):
                cpu_temp += "°C"

            display.lcd.DisplayText(
                text=cpu_temp,
                x=config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("FONT",
                                                                                  "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                              (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )


def display_gpu_stats(load, memory_percentage, memory_used_mb, temperature):
    if config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("SHOW", False):
        if math.isnan(load):
            logger.warning("Your GPU load is not supported yet")
            config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH']['SHOW'] = False
            config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT']['SHOW'] = False
        else:
            # logger.debug(f"GPU Load: {load}")
            display.lcd.DisplayProgressBar(
                x=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("X", 0),
                y=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("Y", 0),
                width=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("WIDTH", 0),
                height=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("HEIGHT", 0),
                value=int(load),
                min_value=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("MIN_VALUE", 0),
                max_value=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                              (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

    if config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("SHOW", False):
        if math.isnan(load):
            logger.warning("Your GPU load is not supported yet")
            config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH']['SHOW'] = False
            config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT']['SHOW'] = False
        else:
            load_text = f"{int(load):>3}"
            if config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("SHOW_UNIT", True):
                load_text += "%"

            display.lcd.DisplayText(
                text=load_text,
                x=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("FONT",
                                                                                 "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                             (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

    if config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("SHOW", False):
        if math.isnan(memory_percentage):
            logger.warning("Your GPU memory relative usage (%) is not supported yet")
            config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH']['SHOW'] = False
        else:
            display.lcd.DisplayProgressBar(
                x=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("X", 0),
                y=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("Y", 0),
                width=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("WIDTH", 0),
                height=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("HEIGHT", 0),
                value=int(memory_percentage),
                min_value=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("MIN_VALUE", 0),
                max_value=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                          (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

    if config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("SHOW", False):
        if math.isnan(memory_used_mb):
            logger.warning("Your GPU memory absolute usage (M) is not supported yet")
            config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT']['SHOW'] = False
        else:
            mem_used_text = f"{int(memory_used_mb):>5}"
            if config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("SHOW_UNIT", True):
                mem_used_text += " M"

            display.lcd.DisplayText(
                text=mem_used_text,
                x=config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("FONT",
                                                                             "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("BACKGROUND_COLOR",
                                                                                         (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

    if config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("SHOW", False):
        if math.isnan(temperature):
            logger.warning("Your GPU temperature is not supported yet")
            config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT']['SHOW'] = False
        else:
            temp_text = f"{int(temperature):>3}"
            if config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("SHOW_UNIT", True):
                temp_text += "°C"

            display.lcd.DisplayText(
                text=temp_text,
                x=config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT",
                                                                                  "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                              (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )


class Gpu:
    @staticmethod
    def stats():
        load, memory_percentage, memory_used_mb, temperature = sensors.Gpu.stats()
        display_gpu_stats(load, memory_percentage, memory_used_mb, temperature)

    @staticmethod
    def is_available():
        return sensors.Gpu.is_available()


class Memory:
    @staticmethod
    def stats():
        swap_percent = sensors.Memory.swap_percent()

        if config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("X", 0),
                y=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("Y", 0),
                width=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("WIDTH", 0),
                height=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("HEIGHT", 0),
                value=int(swap_percent),
                min_value=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("MIN_VALUE", 0),
                max_value=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                           (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        virtual_percent = sensors.Memory.virtual_percent()

        if config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("X", 0),
                y=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("Y", 0),
                width=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("WIDTH", 0),
                height=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("HEIGHT", 0),
                value=int(virtual_percent),
                min_value=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("MIN_VALUE", 0),
                max_value=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                              (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("SHOW", False):
            virtual_percent_text = f"{int(virtual_percent):>3}"
            if config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("SHOW_UNIT", True):
                virtual_percent_text += "%"

            display.lcd.DisplayText(
                text=virtual_percent_text,
                x=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("FONT",
                                                                                         "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("BACKGROUND_COLOR",
                                                                                                     (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get(
                                                   "BACKGROUND_IMAGE", None))
            )

        if config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("SHOW", False):
            virtual_used = sensors.Memory.virtual_used()

            virtual_used_text = f"{int(virtual_used / 1000000):>5}"
            if config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("SHOW_UNIT", True):
                virtual_used_text += " M"

            display.lcd.DisplayText(
                text=virtual_used_text,
                x=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("X", 0),
                y=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("Y", 0),
                font=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("FONT",
                                                                                 "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("BACKGROUND_COLOR",
                                                                                             (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get(
                                                   "BACKGROUND_IMAGE", None))
            )

        if config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("SHOW", False):
            virtual_free = sensors.Memory.virtual_free()

            virtual_free_text = f"{int(virtual_free / 1000000):>5}"
            if config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("SHOW_UNIT", True):
                virtual_free_text += " M"

            display.lcd.DisplayText(
                text=virtual_free_text,
                x=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("X", 0),
                y=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("Y", 0),
                font=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("FONT",
                                                                                 "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("BACKGROUND_COLOR",
                                                                                             (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get(
                                                   "BACKGROUND_IMAGE", None))
            )


class Disk:
    @staticmethod
    def stats():
        used = sensors.Disk.disk_used()
        free = sensors.Disk.disk_free()
        if config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("X", 0),
                y=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("Y", 0),
                width=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("WIDTH", 0),
                height=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("HEIGHT", 0),
                value=int(sensors.Disk.disk_usage_percent()),
                min_value=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("MIN_VALUE", 0),
                max_value=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                         (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("SHOW", False):
            used_text = f"{int(used / 1000000000):>5}"
            if config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("SHOW_UNIT", True):
                used_text += " G"

            display.lcd.DisplayText(
                text=used_text,
                x=config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("FONT",
                                                                            "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                        (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['DISK']['USED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("SHOW", False):
            percent_text = f"{int(sensors.Disk.disk_usage_percent()):>3}"
            if config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("SHOW_UNIT", True):
                percent_text += "%"

            display.lcd.DisplayText(
                text=percent_text,
                x=config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT",
                                                                                    "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("BACKGROUND_COLOR",
                                                                                                (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("SHOW", False):
            total_text = f"{int((free + used) / 1000000000):>5}"
            if config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("SHOW_UNIT", True):
                total_text += " G"

            display.lcd.DisplayText(
                text=total_text,
                x=config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("FONT",
                                                                             "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("BACKGROUND_COLOR",
                                                                                         (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("SHOW", False):
            free_text = f"{int(free / 1000000000):>5}"
            if config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("SHOW_UNIT", True):
                free_text += " G"

            display.lcd.DisplayText(
                text=free_text,
                x=config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("FONT",
                                                                            "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                        (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )


class Net:
    @staticmethod
    def stats():
        interval = config.THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", None)
        upload_wlo, uploaded_wlo, download_wlo, downloaded_wlo = sensors.Net.stats(WLO_CARD, interval)

        if config.THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("SHOW", False):
            upload_wlo_text = f"{bytes2human(upload_wlo, '%(value).1f %(symbol)s/s')}"
            display.lcd.DisplayText(
                text=f"{upload_wlo_text:>10}",
                x=config.THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT",
                                                                                    "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("SHOW", False):
            uploaded_wlo_text = f"{bytes2human(uploaded_wlo)}"
            display.lcd.DisplayText(
                text=f"{uploaded_wlo_text:>6}",
                x=config.THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT",
                                                                                      "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                  (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("SHOW", False):
            download_wlo_text = f"{bytes2human(download_wlo, '%(value).1f %(symbol)s/s')}"
            display.lcd.DisplayText(
                text=f"{download_wlo_text:>10}",
                x=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT",
                                                                                      "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                  (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("SHOW", False):
            downloaded_wlo_text = f"{bytes2human(downloaded_wlo)}"
            display.lcd.DisplayText(
                text=f"{downloaded_wlo_text:>6}",
                x=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT",
                                                                                        "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                    (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        upload_eth, uploaded_eth, download_eth, downloaded_eth = sensors.Net.stats(ETH_CARD, interval)

        if config.THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("SHOW", False):
            upload_eth_text = f"{bytes2human(upload_eth, '%(value).1f %(symbol)s/s')}"
            display.lcd.DisplayText(
                text=f"{upload_eth_text:>10}",
                x=config.THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT",
                                                                                    "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("SHOW", False):
            uploaded_eth_text = f"{bytes2human(uploaded_eth)}"
            display.lcd.DisplayText(
                text=f"{uploaded_eth_text:>6}",
                x=config.THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT",
                                                                                      "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                  (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("SHOW", False):
            download_eth_text = f"{bytes2human(download_eth, '%(value).1f %(symbol)s/s')}"
            display.lcd.DisplayText(
                text=f"{download_eth_text:>10}",
                x=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT",
                                                                                      "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                  (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("SHOW", False):
            downloaded_eth_text = f"{bytes2human(downloaded_eth)}"
            display.lcd.DisplayText(
                text=f"{downloaded_eth_text:>6}",
                x=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT",
                                                                                        "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                                    (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )


class Date:
    @staticmethod
    def stats():
        if HW_SENSORS == "STATIC":
            # For static sensors, use predefined date/time
            date_now = datetime.datetime.fromtimestamp(1694014609)
        else:
            date_now = datetime.datetime.now()

        if platform.system() == "Windows":
            # Windows does not have LC_TIME environment variable, use deprecated getdefaultlocale() that returns language code following RFC 1766
            lc_time = locale.getdefaultlocale()[0]
        else:
            lc_time = babel.dates.LC_TIME

        if config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("SHOW", False):
            date_format = config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("FORMAT", 'medium')
            display.lcd.DisplayText(
                text=f"{babel.dates.format_date(date_now, format=date_format, locale=lc_time)}",
                x=config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("FONT",
                                                                           "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("BACKGROUND_COLOR",
                                                                                       (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                     None))
            )

        if config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("SHOW", False):
            time_format = config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("FORMAT", 'medium')
            display.lcd.DisplayText(
                text=f"{babel.dates.format_time(date_now, format=time_format, locale=lc_time)}",
                x=config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("X", 0),
                y=config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("Y", 0),
                font=config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("FONT",
                                                                            "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("FONT_SIZE", 10),
                font_color=config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("BACKGROUND_COLOR",
                                                                                        (255, 255, 255)),
                background_image=get_full_path(config.THEME_DATA['PATH'],
                                               config.THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )
