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

import library.sensors.sensors_custom as sensors_custom


def get_theme_file_path(name):
    if name:
        return os.path.join(config.THEME_DATA['PATH'], name)
    else:
        return None


def display_themed_value(theme_data, value, min_size=0, unit=''):
    if not theme_data.get("SHOW", False):
        return

    text = f"{{:>{min_size}}}".format(value)
    if theme_data.get("SHOW_UNIT", True) and unit:
        text += str(unit)

    display.lcd.DisplayText(
        text=text,
        x=theme_data.get("X", 0),
        y=theme_data.get("Y", 0),
        font=theme_data.get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
        font_size=theme_data.get("FONT_SIZE", 10),
        font_color=theme_data.get("FONT_COLOR", (0, 0, 0)),
        background_color=theme_data.get("BACKGROUND_COLOR", (255, 255, 255)),
        background_image=get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None)),
        anchor="lt"
    )


def display_themed_progress_bar(theme_data, value):
    if not theme_data.get("SHOW", False):
        return

    display.lcd.DisplayProgressBar(
        x=theme_data.get("X", 0),
        y=theme_data.get("Y", 0),
        width=theme_data.get("WIDTH", 0),
        height=theme_data.get("HEIGHT", 0),
        value=int(value),
        min_value=theme_data.get("MIN_VALUE", 0),
        max_value=theme_data.get("MAX_VALUE", 100),
        bar_color=theme_data.get("BAR_COLOR", (0, 0, 0)),
        bar_outline=theme_data.get("BAR_OUTLINE", False),
        background_color=theme_data.get("BACKGROUND_COLOR", (255, 255, 255)),
        background_image=get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None))
    )


def display_themed_radial_bar(theme_data, value, min_size=0, unit='', custom_text=None):
    if not theme_data.get("SHOW", False):
        return

    if theme_data.get("SHOW_TEXT", False):
        if custom_text:
            text = custom_text
        else:
            text = f"{{:>{min_size}}}".format(value)
            if theme_data.get("SHOW_UNIT", True) and unit:
                text += str(unit)
    else:
        text = ""

    display.lcd.DisplayRadialProgressBar(
        xc=theme_data.get("X", 0),
        yc=theme_data.get("Y", 0),
        radius=theme_data.get("RADIUS", 1),
        bar_width=theme_data.get("WIDTH", 1),
        min_value=theme_data.get("MIN_VALUE", 0),
        max_value=theme_data.get("MAX_VALUE", 100),
        angle_start=theme_data.get("ANGLE_START", 0),
        angle_end=theme_data.get("ANGLE_END", 360),
        angle_steps=theme_data.get("ANGLE_STEPS", 1),
        angle_sep=theme_data.get("ANGLE_SEP", 0),
        clockwise=theme_data.get("CLOCKWISE", False),
        value=value,
        bar_color=theme_data.get("BAR_COLOR", (0, 0, 0)),
        text=text,
        font=theme_data.get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
        font_size=theme_data.get("FONT_SIZE", 10),
        font_color=theme_data.get("FONT_COLOR", (0, 0, 0)),
        background_color=theme_data.get("BACKGROUND_COLOR", (0, 0, 0)),
        background_image=get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None))
    )


class CPU:
    @staticmethod
    def percentage():
        theme_data = config.THEME_DATA['STATS']['CPU']['PERCENTAGE']
        cpu_percentage = sensors.Cpu.percentage(
            interval=theme_data.get("INTERVAL", None)
        )
        # logger.debug(f"CPU Percentage: {cpu_percentage}")

        display_themed_progress_bar(
            theme_data=theme_data['GRAPH'],
            value=int(cpu_percentage)
        )

        display_themed_radial_bar(
            theme_data=(theme_data['RADIAL']),
            value=int(cpu_percentage),
            unit="%",
            min_size=3)

        display_themed_value(
            theme_data=(theme_data['TEXT']),
            value=int(cpu_percentage),
            unit="%",
            min_size=3
        )

    @staticmethod
    def frequency():
        display_themed_value(
            theme_data=config.THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'],
            value=f'{sensors.Cpu.frequency() / 1000:.2f}',
            unit=" GHz",
            min_size=4
        )

    @staticmethod
    def load():
        cpu_load = sensors.Cpu.load()
        # logger.debug(f"CPU Load: ({cpu_load[0]},{cpu_load[1]},{cpu_load[2]})")
        load_theme_data = config.THEME_DATA['STATS']['CPU']['LOAD']

        CPU._display_load_data(load_theme_data['ONE']['TEXT'], cpu_load[0])

        CPU._display_load_data(load_theme_data['FIVE']['TEXT'], cpu_load[1])

        CPU._display_load_data(load_theme_data['FIFTEEN']['TEXT'], cpu_load[2])

    @staticmethod
    def _display_load_data(theme_one_text_data, value):
        display_themed_value(
            theme_data=theme_one_text_data,
            value=int(value),
            min_size=3,
            unit="%"
        )

    @staticmethod
    def is_temperature_available():
        return sensors.Cpu.is_temperature_available()

    @staticmethod
    def temperature():
        display_themed_value(
            theme_data=config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'],
            value=int(sensors.Cpu.temperature()),
            min_size=3,
            unit="°C"
        )


def display_gpu_stats(load, memory_percentage, memory_used_mb, temperature, fps):
    theme_gpu_data = config.THEME_DATA['STATS']['GPU']

    gpu_percent_graph_data = theme_gpu_data['PERCENTAGE']['GRAPH']
    gpu_percent_radial_data = theme_gpu_data['PERCENTAGE']['RADIAL']
    gpu_percent_text_data = theme_gpu_data['PERCENTAGE']['TEXT']
    if math.isnan(load):
        load = 0
        if gpu_percent_graph_data['SHOW'] or gpu_percent_text_data['SHOW'] or gpu_percent_radial_data['SHOW']:
            logger.warning("Your GPU load is not supported yet")
            gpu_percent_graph_data['SHOW'] = False
            gpu_percent_text_data['SHOW'] = False
            gpu_percent_radial_data['SHOW'] = False

    gpu_mem_graph_data = theme_gpu_data['MEMORY']['GRAPH']
    gpu_mem_radial_data = theme_gpu_data['MEMORY']['RADIAL']
    if math.isnan(memory_percentage):
        memory_percentage = 0
        if gpu_mem_graph_data['SHOW'] or gpu_mem_radial_data['SHOW']:
            logger.warning("Your GPU memory relative usage (%) is not supported yet")
            gpu_mem_graph_data['SHOW'] = False
            gpu_mem_radial_data['SHOW'] = False

    gpu_mem_text_data = theme_gpu_data['MEMORY']['TEXT']
    if math.isnan(memory_used_mb):
        memory_used_mb = 0
        if gpu_mem_text_data['SHOW']:
            logger.warning("Your GPU memory absolute usage (M) is not supported yet")
            gpu_mem_text_data['SHOW'] = False

    gpu_temp_text_data = theme_gpu_data['TEMPERATURE']['TEXT']
    if math.isnan(temperature):
        temperature = 0
        if gpu_temp_text_data['SHOW']:
            logger.warning("Your GPU temperature is not supported yet")
            gpu_temp_text_data['SHOW'] = False

    gpu_fps_text_data = theme_gpu_data['FPS']['TEXT']
    if fps < 0:
        if gpu_fps_text_data['SHOW']:
            logger.warning("Your GPU FPS is not supported yet")
            gpu_fps_text_data['SHOW'] = False

    # logger.debug(f"GPU Load: {load}")
    display_themed_progress_bar(gpu_percent_graph_data, load)

    display_themed_radial_bar(
        theme_data=gpu_percent_radial_data,
        value=int(load),
        min_size=3,
        unit="%")

    display_themed_progress_bar(gpu_mem_graph_data, memory_percentage)

    display_themed_radial_bar(
        theme_data=gpu_mem_radial_data,
        value=int(memory_percentage),
        min_size=3,
        unit="%"
    )

    display_themed_value(
        theme_data=gpu_percent_text_data,
        value=int(load),
        min_size=3,
        unit="%"
    )

    display_themed_value(
        theme_data=gpu_mem_text_data,
        value=int(memory_used_mb),
        min_size=5,
        unit=" M"
    )

    display_themed_value(
        theme_data=gpu_temp_text_data,
        value=int(temperature),
        min_size=3,
        unit="°C"
    )

    display_themed_value(
        theme_data=gpu_fps_text_data,
        value=int(fps),
        min_size=4,
        unit=" FPS"
    )


class Gpu:
    @staticmethod
    def stats():
        load, memory_percentage, memory_used_mb, temperature = sensors.Gpu.stats()
        fps = sensors.Gpu.fps()
        display_gpu_stats(load, memory_percentage, memory_used_mb, temperature, fps)

    @staticmethod
    def is_available():
        return sensors.Gpu.is_available()


class Memory:
    @staticmethod
    def stats():
        memory_stats_theme_data = config.THEME_DATA['STATS']['MEMORY']

        swap_percent = sensors.Memory.swap_percent()
        display_themed_progress_bar(memory_stats_theme_data['SWAP']['GRAPH'], swap_percent)
        display_themed_radial_bar(
            theme_data=memory_stats_theme_data['SWAP']['RADIAL'],
            value=int(swap_percent),
            min_size=3,
            unit="%"
        )

        virtual_percent = sensors.Memory.virtual_percent()
        display_themed_progress_bar(memory_stats_theme_data['VIRTUAL']['GRAPH'], virtual_percent)
        display_themed_radial_bar(
            theme_data=memory_stats_theme_data['VIRTUAL']['RADIAL'],
            value=int(virtual_percent),
            min_size=3,
            unit="%"
        )

        display_themed_value(
            theme_data=memory_stats_theme_data['VIRTUAL']['PERCENT_TEXT'],
            value=int(virtual_percent),
            min_size=3,
            unit="%"
        )

        display_themed_value(
            theme_data=memory_stats_theme_data['VIRTUAL']['USED'],
            value=int(sensors.Memory.virtual_used() / 1000000),
            min_size=5,
            unit=" M"
        )

        display_themed_value(
            theme_data=memory_stats_theme_data['VIRTUAL']['FREE'],
            value=int(sensors.Memory.virtual_free() / 1000000),
            min_size=5,
            unit=" M"
        )

        display_themed_value(
            theme_data=memory_stats_theme_data['VIRTUAL']['TOTAL'],
            value=int((sensors.Memory.virtual_free() + sensors.Memory.virtual_used()) / 1000000),
            min_size=5,
            unit=" M"
        )


class Disk:
    @staticmethod
    def stats():
        used = sensors.Disk.disk_used()
        free = sensors.Disk.disk_free()

        disk_theme_data = config.THEME_DATA['STATS']['DISK']

        disk_usage_percent = sensors.Disk.disk_usage_percent()
        display_themed_progress_bar(disk_theme_data['USED']['GRAPH'], disk_usage_percent)
        display_themed_radial_bar(
            theme_data=disk_theme_data['USED']['RADIAL'],
            value=int(disk_usage_percent),
            min_size=3,
            unit="%"
        )

        display_themed_value(
            theme_data=disk_theme_data['USED']['TEXT'],
            value=int(used / 1000000000),
            min_size=5,
            unit=" G"
        )

        display_themed_value(
            theme_data=disk_theme_data['USED']['PERCENT_TEXT'],
            value=int(disk_usage_percent),
            min_size=3,
            unit="%"
        )

        display_themed_value(
            theme_data=disk_theme_data['TOTAL']['TEXT'],
            value=int((free + used) / 1000000000),
            min_size=5,
            unit=" G"
        )

        display_themed_value(
            theme_data=disk_theme_data['FREE']['TEXT'],
            value=int(free / 1000000000),
            min_size=5,
            unit=" G"
        )


class Net:
    @staticmethod
    def stats():
        interval = config.THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", None)
        upload_wlo, uploaded_wlo, download_wlo, downloaded_wlo = sensors.Net.stats(WLO_CARD, interval)
        net_theme_data = config.THEME_DATA['STATS']['NET']

        Net._show_themed_tax_rate(net_theme_data['WLO']['UPLOAD']['TEXT'], upload_wlo)
        Net._show_themed_total_data(net_theme_data['WLO']['UPLOADED']['TEXT'], uploaded_wlo)

        Net._show_themed_tax_rate(net_theme_data['WLO']['DOWNLOAD']['TEXT'], download_wlo)
        Net._show_themed_total_data(net_theme_data['WLO']['DOWNLOADED']['TEXT'], downloaded_wlo)

        upload_eth, uploaded_eth, download_eth, downloaded_eth = sensors.Net.stats(ETH_CARD, interval)

        Net._show_themed_tax_rate(net_theme_data['ETH']['UPLOAD']['TEXT'], upload_eth)
        Net._show_themed_total_data(net_theme_data['ETH']['UPLOADED']['TEXT'], uploaded_eth)

        Net._show_themed_tax_rate(net_theme_data['ETH']['DOWNLOAD']['TEXT'], download_eth)
        Net._show_themed_total_data(net_theme_data['ETH']['DOWNLOADED']['TEXT'], downloaded_eth)

    @staticmethod
    def _show_themed_total_data(theme_data, amount):
        display_themed_value(
            theme_data=theme_data,
            value=f"{bytes2human(amount)}",
            min_size=6
        )

    @staticmethod
    def _show_themed_tax_rate(theme_data, rate):
        display_themed_value(
            theme_data=theme_data,
            value=f"{bytes2human(rate, '%(value).1f %(symbol)s/s')}",
            min_size=10
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

        date_theme_data = config.THEME_DATA['STATS']['DATE']
        day_theme_data = date_theme_data['DAY']['TEXT']
        date_format = day_theme_data.get("FORMAT", 'medium')
        display_themed_value(
            theme_data=day_theme_data,
            value=f"{babel.dates.format_date(date_now, format=date_format, locale=lc_time)}"
        )

        hour_theme_data = date_theme_data['HOUR']['TEXT']
        time_format = hour_theme_data.get("FORMAT", 'medium')
        display_themed_value(
            theme_data=hour_theme_data,
            value=f"{babel.dates.format_time(date_now, format=time_format, locale=lc_time)}"
        )


class Custom:
    @staticmethod
    def stats():
        for custom_stat in config.THEME_DATA['STATS']['CUSTOM']:
            if custom_stat != "INTERVAL":

                # Load the custom sensor class from sensors_custom.py based on the class name
                try:
                    custom_stat_class = getattr(sensors_custom, str(custom_stat))()
                    string_value = custom_stat_class.as_string()
                    numeric_value = custom_stat_class.as_numeric()
                except:
                    logger.error("Custom sensor class " + str(custom_stat) + " not found in sensors_custom.py")
                    return

                if string_value is None:
                    string_value = str(numeric_value)

                # Display text
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("TEXT", None)
                if theme_data and string_value is not None:
                    display_themed_value(theme_data=theme_data, value=string_value)

                # Display graph from numeric value
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("GRAPH", None)
                if theme_data and numeric_value is not None:
                    display_themed_progress_bar(theme_data=theme_data, value=numeric_value)

                # Display radial from numeric and text value
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("RADIAL", None)
                if theme_data and numeric_value is not None and string_value is not None:
                    display_themed_radial_bar(
                        theme_data=theme_data,
                        value=numeric_value,
                        custom_text=string_value
                    )
