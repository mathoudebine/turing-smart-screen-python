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
from typing import List, Tuple, Callable  # Added List, Tuple, Callable

import babel.dates
import requests
from ping3 import ping
from psutil._common import bytes2human
from uptime import uptime

import library.config as config
from library.display import display
from library.log import logger

DEFAULT_HISTORY_SIZE = 10

ETH_CARD = config.CONFIG_DATA["config"].get("ETH", "")
WLO_CARD = config.CONFIG_DATA["config"].get("WLO", "")
HW_SENSORS = config.CONFIG_DATA["config"].get("HW_SENSORS", "AUTO")
CPU_FAN = config.CONFIG_DATA["config"].get("CPU_FAN", "AUTO")
PING_DEST = config.CONFIG_DATA["config"].get("PING", "127.0.0.1")

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

    if value is None:
        return

    # overridable MIN_SIZE from theme with backward compatibility
    min_size = theme_data.get("MIN_SIZE", min_size)

    text = f"{{:>{min_size}}}".format(value)
    if theme_data.get("SHOW_UNIT", True) and unit:
        text += str(unit)

    display.lcd.DisplayText(
        text=text,
        x=theme_data.get("X", 0),
        y=theme_data.get("Y", 0),
        width=theme_data.get("WIDTH", 0),
        height=theme_data.get("HEIGHT", 0),
        font=config.FONTS_DIR + theme_data.get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
        font_size=theme_data.get("FONT_SIZE", 10),
        font_color=theme_data.get("FONT_COLOR", (0, 0, 0)),
        background_color=theme_data.get("BACKGROUND_COLOR", (255, 255, 255)),
        background_image=get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None)),
        align=theme_data.get("ALIGN", "left"),
        anchor=theme_data.get("ANCHOR", "lt"),
    )


def display_themed_percent_value(theme_data, value):
    display_val = 0 if math.isnan(value) else int(value)
    display_themed_value(
        theme_data=theme_data,
        value=display_val,
        min_size=3,
        unit="%"
    )


def display_themed_temperature_value(theme_data, value):
    display_val = 0 if math.isnan(value) else int(value)
    display_themed_value(
        theme_data=theme_data,
        value=display_val,
        min_size=3,
        unit="°C"
    )


def display_themed_progress_bar(theme_data, value):
    if not theme_data.get("SHOW", False):
        return

    display_val = 0 if math.isnan(value) else int(value)
    display.lcd.DisplayProgressBar(
        x=theme_data.get("X", 0),
        y=theme_data.get("Y", 0),
        width=theme_data.get("WIDTH", 0),
        height=theme_data.get("HEIGHT", 0),
        value=display_val, # Use the checked value
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

    display_val = 0 if math.isnan(value) else value
    if theme_data.get("SHOW_TEXT", False):
        if custom_text:
            text = custom_text
        else:
            text = f"{{:>{min_size}}}".format(int(display_val) if not isinstance(display_val, str) else display_val) # Ensure int for formatting if not already string
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
        value=display_val,
        bar_color=theme_data.get("BAR_COLOR", (0, 0, 0)),
        text=text,
        font=config.FONTS_DIR + theme_data.get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
        font_size=theme_data.get("FONT_SIZE", 10),
        font_color=theme_data.get("FONT_COLOR", (0, 0, 0)),
        background_color=theme_data.get("BACKGROUND_COLOR", (0, 0, 0)),
        background_image=get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None)),
        custom_bbox=theme_data.get("CUSTOM_BBOX", (0, 0, 0, 0)),
        text_offset=theme_data.get("TEXT_OFFSET", (0, 0)),
        bar_background_color=theme_data.get("BAR_BACKGROUND_COLOR", (0, 0, 0)),
        draw_bar_background=theme_data.get("DRAW_BAR_BACKGROUND", False),
        bar_decoration=theme_data.get("BAR_DECORATION", "")
    )


def display_themed_percent_radial_bar(theme_data, value):
    display_val = 0 if math.isnan(value) else int(value)
    display_themed_radial_bar(
        theme_data=theme_data,
        value=display_val,
        unit="%",
        min_size=3
    )


def display_themed_temperature_radial_bar(theme_data, value):
    display_themed_radial_bar(
        theme_data=theme_data,
        value=int(value),
        min_size=3,
        unit="°C"
    )


def display_themed_line_graph(theme_data, values):
    if not theme_data.get("SHOW", False):
        return

    line_color = theme_data.get("LINE_COLOR", (0, 0, 0))

    display.lcd.DisplayLineGraph(
        x=theme_data.get("X", 0),
        y=theme_data.get("Y", 0),
        width=theme_data.get("WIDTH", 1),
        height=theme_data.get("HEIGHT", 1),
        values=values,
        min_value=theme_data.get("MIN_VALUE", 0),
        max_value=theme_data.get("MAX_VALUE", 100),
        autoscale=theme_data.get("AUTOSCALE", False),
        line_color=line_color,
        line_width=theme_data.get("LINE_WIDTH", 2),
        graph_axis=theme_data.get("AXIS", False),
        axis_color=theme_data.get("AXIS_COLOR", line_color),  # If no color specified, use line color for axis
        axis_font=config.FONTS_DIR + theme_data.get("AXIS_FONT", "roboto/Roboto-Black.ttf"),
        axis_font_size=theme_data.get("AXIS_FONT_SIZE", 10),
        background_color=theme_data.get("BACKGROUND_COLOR", (0, 0, 0)),
        background_image=get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None))
    )


def save_last_value(value: float, last_values: List[float], history_size: int):
    # Initialize last values list the first time with given size
    if len(last_values) != history_size:
        last_values[:] = last_values_list(size=history_size)
    # Store the value to the list that can then be used for line graph
    last_values.append(value)
    # Also remove the oldest value from list
    last_values.pop(0)


def last_values_list(size: int) -> List[float]:
    return [math.nan] * size


class CPU:
    last_values_cpu_percentage = []
    last_values_cpu_temperature = []
    last_values_cpu_fan_speed = []
    last_values_cpu_frequency = []

    @classmethod
    def percentage(cls):
        theme_data = config.THEME_DATA['STATS']['CPU']['PERCENTAGE']
        cpu_percentage = sensors.Cpu.percentage(
            interval=theme_data.get("INTERVAL", None)
        )
        save_last_value(cpu_percentage, cls.last_values_cpu_percentage,
                        theme_data['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        # logger.debug(f"CPU Percentage: {cpu_percentage}")

        display_themed_progress_bar(theme_data['GRAPH'], cpu_percentage)
        display_themed_percent_radial_bar(theme_data['RADIAL'], cpu_percentage)
        display_themed_percent_value(theme_data['TEXT'], cpu_percentage)
        display_themed_line_graph(theme_data['LINE_GRAPH'], cls.last_values_cpu_percentage)

    @classmethod
    def frequency(cls):
        freq_ghz = sensors.Cpu.frequency() / 1000
        theme_data = config.THEME_DATA['STATS']['CPU']['FREQUENCY']

        save_last_value(freq_ghz, cls.last_values_cpu_frequency,
                        theme_data['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))

        display_themed_value(
            theme_data=theme_data['TEXT'],
            value=f'{freq_ghz:.2f}',
            unit=" GHz",
            min_size=4
        )
        display_themed_progress_bar(theme_data['GRAPH'], freq_ghz)
        display_themed_radial_bar(
            theme_data=theme_data['RADIAL'],
            value=f'{freq_ghz:.2f}',
            unit=" GHz",
            min_size=4
        )
        display_themed_line_graph(theme_data['LINE_GRAPH'], cls.last_values_cpu_frequency)

    @classmethod
    def load(cls):
        cpu_load = sensors.Cpu.load()
        # logger.debug(f"CPU Load: ({cpu_load[0]},{cpu_load[1]},{cpu_load[2]})")
        load_theme_data = config.THEME_DATA['STATS']['CPU']['LOAD']

        display_themed_percent_value(load_theme_data['ONE']['TEXT'], cpu_load[0])
        display_themed_percent_value(load_theme_data['FIVE']['TEXT'], cpu_load[1])
        display_themed_percent_value(load_theme_data['FIFTEEN']['TEXT'], cpu_load[2])

    @classmethod
    def temperature(cls):
        temperature = sensors.Cpu.temperature()
        save_last_value(temperature, cls.last_values_cpu_temperature,
                        config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['LINE_GRAPH'].get("HISTORY_SIZE",
                                                                                           DEFAULT_HISTORY_SIZE))

        cpu_temp_text_data = config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT']
        cpu_temp_radial_data = config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['RADIAL']
        cpu_temp_graph_data = config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['GRAPH']
        cpu_temp_line_graph_data = config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['LINE_GRAPH']

        if math.isnan(temperature):
            temperature = 0
            if cpu_temp_text_data['SHOW'] or cpu_temp_radial_data['SHOW'] or cpu_temp_graph_data[
                'SHOW'] or cpu_temp_line_graph_data['SHOW']:
                logger.warning("Your CPU temperature is not supported yet")
                cpu_temp_text_data['SHOW'] = False
                cpu_temp_radial_data['SHOW'] = False
                cpu_temp_graph_data['SHOW'] = False
                cpu_temp_line_graph_data['SHOW'] = False

        display_themed_temperature_value(cpu_temp_text_data, temperature)
        display_themed_progress_bar(cpu_temp_graph_data, temperature)
        display_themed_temperature_radial_bar(cpu_temp_radial_data, temperature)
        display_themed_line_graph(cpu_temp_line_graph_data, cls.last_values_cpu_temperature)

    @classmethod
    def fan_speed(cls):
        if CPU_FAN != "AUTO":
            fan_percent = sensors.Cpu.fan_percent(CPU_FAN)
        else:
            fan_percent = sensors.Cpu.fan_percent()

        save_last_value(fan_percent, cls.last_values_cpu_fan_speed,
                        config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['LINE_GRAPH'].get("HISTORY_SIZE",
                                                                                         DEFAULT_HISTORY_SIZE))

        cpu_fan_text_data = config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['TEXT']
        cpu_fan_radial_data = config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['RADIAL']
        cpu_fan_graph_data = config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['GRAPH']
        cpu_fan_line_graph_data = config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['LINE_GRAPH']

        if math.isnan(fan_percent):
            fan_percent = 0
            if cpu_fan_text_data['SHOW'] or cpu_fan_radial_data['SHOW'] or cpu_fan_graph_data[
                'SHOW'] or cpu_fan_line_graph_data['SHOW']:
                if sys.platform == "win32":
                    logger.warning("Your CPU Fan sensor could not be auto-detected")
                else:
                    logger.warning("Your CPU Fan sensor could not be auto-detected. Select it from Configuration UI.")
                cpu_fan_text_data['SHOW'] = False
                cpu_fan_radial_data['SHOW'] = False
                cpu_fan_graph_data['SHOW'] = False
                cpu_fan_line_graph_data['SHOW'] = False

        display_themed_percent_value(cpu_fan_text_data, fan_percent)
        display_themed_progress_bar(cpu_fan_graph_data, fan_percent)
        display_themed_percent_radial_bar(cpu_fan_radial_data, fan_percent)
        display_themed_line_graph(cpu_fan_line_graph_data, cls.last_values_cpu_fan_speed)


class Gpu:
    loads = []
    memory_percentages = []
    memory_used_mbs = []
    total_memory_mbs = []
    temperatures = []
    fps_values = []
    fan_percents = []
    frequencies_ghz = []
    gpu_names = []  # Added GPU names storage array

    last_values_gpu_percentage = []
    last_values_gpu_mem_percentage = []
    last_values_gpu_temperature = []
    last_values_gpu_fps = []
    last_values_gpu_fan_speed = []
    last_values_gpu_frequency = []

    @classmethod
    def stats(cls):
        """Main entry point for GPU statistics collection and display"""
        # 1. Fetch data and prepare storage
        num_gpus = cls._fetch_gpu_data()
        
        # 2. Process each GPU's data and update histories
        for i in range(num_gpus):
            cls._update_history(i)
        
        # 3. Render multi-GPU data (new structure with GPU0, GPU1, etc.)
        cls._render_multi_gpu(num_gpus)
        
        # 4. Handle legacy/backward compatibility (first GPU)
        if num_gpus > 0:
            cls._render_legacy_gpu()

    @classmethod
    def _fetch_gpu_data(cls):
        """Fetch GPU data and resize storage if needed"""
        all_stats_tuples = sensors.Gpu.stats()
        all_fps = sensors.Gpu.fps()
        all_fan_percent = sensors.Gpu.fan_percent()
        all_frequency_mhz = sensors.Gpu.frequency()
        all_names = sensors.Gpu.get_gpu_names()
        
        num_gpus = len(all_stats_tuples)

        if len(all_names) < num_gpus:
             all_names.extend([f"GPU {i}" for i in range(len(all_names), num_gpus)])
        elif len(all_names) > num_gpus:
             all_names = all_names[:num_gpus]

        if len(cls.loads) != num_gpus:
            cls._resize_storage(num_gpus)
            
        for i in range(num_gpus):
            if i < len(all_stats_tuples):
                cls.loads[i], cls.memory_percentages[i], cls.memory_used_mbs[i], cls.total_memory_mbs[i], cls.temperatures[i] = all_stats_tuples[i]
            else:
                cls.loads[i], cls.memory_percentages[i], cls.memory_used_mbs[i], cls.total_memory_mbs[i], cls.temperatures[i] = [math.nan]*5
            
            cls.fps_values[i] = all_fps[i] if i < len(all_fps) else -1
            cls.fan_percents[i] = all_fan_percent[i] if i < len(all_fan_percent) else math.nan
            freq_mhz = all_frequency_mhz[i] if i < len(all_frequency_mhz) else math.nan
            cls.frequencies_ghz[i] = freq_mhz / 1000.0 if freq_mhz is not None and not math.isnan(freq_mhz) else math.nan
            cls.gpu_names[i] = all_names[i]
            
        return num_gpus

    @classmethod
    def _render_multi_gpu(cls, num_gpus):
        """Render metrics for multiple GPUs using the GPU0, GPU1, etc. structure"""
        theme_gpu_main_data = config.THEME_DATA['STATS']['GPU']
        for i in range(num_gpus):
            gpu_key = f"GPU{i}"
            if gpu_key in theme_gpu_main_data:
                gpu_theme_section = theme_gpu_main_data[gpu_key]
                
                # Render GPU name if configured in theme
                if 'NAME' in gpu_theme_section and 'TEXT' in gpu_theme_section['NAME']:
                    display_themed_value(gpu_theme_section['NAME']['TEXT'], cls.gpu_names[i])
                
                # Render stats using helper methods
                cls._render_gpu_stat(gpu_theme_section, 'PERCENTAGE', cls.loads[i], 
                                    cls.last_values_gpu_percentage[i], 
                                    display_themed_percent_value, display_themed_percent_radial_bar)
                                    
                cls._render_gpu_stat(gpu_theme_section, 'MEMORY_PERCENT', cls.memory_percentages[i], 
                                    cls.last_values_gpu_mem_percentage[i], 
                                    display_themed_percent_value, display_themed_percent_radial_bar)
                                    
                cls._render_gpu_stat(gpu_theme_section, 'TEMPERATURE', cls.temperatures[i], 
                                    cls.last_values_gpu_temperature[i], 
                                    display_themed_temperature_value, display_themed_temperature_radial_bar)
                                    
                cls._render_gpu_stat(gpu_theme_section, 'FAN_SPEED', cls.fan_percents[i], 
                                    cls.last_values_gpu_fan_speed[i], 
                                    display_themed_percent_value, display_themed_percent_radial_bar)
                                    
                cls._render_gpu_stat_custom_format(gpu_theme_section, 'MEMORY_USED', 
                                                cls.memory_used_mbs[i], unit=" M", min_size=5)
                                                
                cls._render_gpu_stat_custom_format(gpu_theme_section, 'MEMORY_TOTAL', 
                                                cls.total_memory_mbs[i], unit=" M", min_size=5)
                                                
                cls._render_gpu_stat_custom_format(gpu_theme_section, 'FPS', cls.fps_values[i], 
                                                unit=" FPS", min_size=4, 
                                                history_list=cls.last_values_gpu_fps[i])
                                                
                cls._render_gpu_stat_custom_format(gpu_theme_section, 'FREQUENCY', cls.frequencies_ghz[i], 
                                                unit=" GHz", min_size=4, format_str='{:.2f}', 
                                                history_list=cls.last_values_gpu_frequency[i])


    @classmethod
    def _render_legacy_gpu(cls):
        """Render metrics for the first GPU in the legacy format for backward compatibility"""
        theme_gpu_data = config.THEME_DATA['STATS']['GPU']
        
        # Extract data for the first GPU
        load = cls.loads[0]
        memory_percentage = cls.memory_percentages[0]
        memory_used_mb = cls.memory_used_mbs[0]
        total_memory_mb = cls.total_memory_mbs[0]
        temperature = cls.temperatures[0]
        fps = cls.fps_values[0]
        fan_percent = cls.fan_percents[0]
        freq_ghz = cls.frequencies_ghz[0]
        
        # Legacy memory section
        cls._render_legacy_memory(theme_gpu_data, memory_percentage, memory_used_mb)
        
        # GPU load percentage
        cls._render_legacy_percentage(theme_gpu_data, load)
        
        # GPU memory percentage
        cls._render_legacy_memory_percent(theme_gpu_data, memory_percentage)
        
        # GPU memory used
        cls._render_legacy_memory_used(theme_gpu_data, memory_used_mb)
        
        # GPU total memory
        cls._render_legacy_memory_total(theme_gpu_data, total_memory_mb)
        
        # GPU temperature
        cls._render_legacy_temperature(theme_gpu_data, temperature)
        
        # GPU FPS
        cls._render_legacy_fps(theme_gpu_data, fps)
        
        # GPU fan speed
        cls._render_legacy_fan_speed(theme_gpu_data, fan_percent)
        
        # GPU frequency
        cls._render_legacy_frequency(theme_gpu_data, freq_ghz)

    @classmethod
    def _render_legacy_memory(cls, theme_gpu_data, memory_percentage, memory_used_mb):
        """Render legacy memory section"""
        gpu_mem_graph_data = theme_gpu_data['MEMORY']['GRAPH']
        gpu_mem_radial_data = theme_gpu_data['MEMORY']['RADIAL']
        gpu_mem_text_data = theme_gpu_data['MEMORY']['TEXT']
        
        if math.isnan(memory_percentage):
            memory_percentage = 0
            if gpu_mem_graph_data['SHOW'] or gpu_mem_radial_data['SHOW']:
                logger.warning("Your GPU memory relative usage (%) is not supported yet")
                gpu_mem_graph_data['SHOW'] = False
                gpu_mem_radial_data['SHOW'] = False
                
        if math.isnan(memory_used_mb):
            memory_used_mb = 0
            if gpu_mem_text_data['SHOW']:
                logger.warning("Your GPU memory absolute usage (M) is not supported yet")
                gpu_mem_text_data['SHOW'] = False

        display_themed_progress_bar(gpu_mem_graph_data, memory_percentage)
        display_themed_percent_radial_bar(gpu_mem_radial_data, memory_percentage)
        display_themed_value(
            theme_data=gpu_mem_text_data,
            value=int(memory_used_mb),
            min_size=5,
            unit=" M"
        )

    @classmethod
    def _render_legacy_percentage(cls, theme_gpu_data, load):
        """Render legacy GPU load percentage"""
        gpu_percent_graph_data = theme_gpu_data['PERCENTAGE']['GRAPH']
        gpu_percent_radial_data = theme_gpu_data['PERCENTAGE']['RADIAL']
        gpu_percent_text_data = theme_gpu_data['PERCENTAGE']['TEXT']
        gpu_percent_line_graph_data = theme_gpu_data['PERCENTAGE']['LINE_GRAPH']

        if math.isnan(load):
            load = 0
            if gpu_percent_graph_data['SHOW'] or gpu_percent_text_data['SHOW'] or gpu_percent_radial_data['SHOW'] or \
                    gpu_percent_line_graph_data['SHOW']:
                logger.warning("Your GPU load is not supported yet")
                gpu_percent_graph_data['SHOW'] = False
                gpu_percent_text_data['SHOW'] = False
                gpu_percent_radial_data['SHOW'] = False
                gpu_percent_line_graph_data['SHOW'] = False

        display_themed_progress_bar(gpu_percent_graph_data, load)
        display_themed_percent_radial_bar(gpu_percent_radial_data, load)
        display_themed_percent_value(gpu_percent_text_data, load)
        display_themed_line_graph(gpu_percent_line_graph_data, cls.last_values_gpu_percentage[0])

    @classmethod
    def _render_legacy_memory_percent(cls, theme_gpu_data, memory_percentage):
        """Render legacy GPU memory percentage"""
        gpu_mem_percent_graph_data = theme_gpu_data['MEMORY_PERCENT']['GRAPH']
        gpu_mem_percent_radial_data = theme_gpu_data['MEMORY_PERCENT']['RADIAL']
        gpu_mem_percent_text_data = theme_gpu_data['MEMORY_PERCENT']['TEXT']
        gpu_mem_percent_line_graph_data = theme_gpu_data['MEMORY_PERCENT']['LINE_GRAPH']

        if math.isnan(memory_percentage):
            memory_percentage = 0
            if gpu_mem_percent_graph_data['SHOW'] or gpu_mem_percent_radial_data['SHOW'] or gpu_mem_percent_text_data[
                'SHOW'] or gpu_mem_percent_line_graph_data['SHOW']:
                logger.warning("Your GPU memory relative usage (%) is not supported yet")
                gpu_mem_percent_graph_data['SHOW'] = False
                gpu_mem_percent_radial_data['SHOW'] = False
                gpu_mem_percent_text_data['SHOW'] = False

        display_themed_progress_bar(gpu_mem_percent_graph_data, memory_percentage)
        display_themed_percent_radial_bar(gpu_mem_percent_radial_data, memory_percentage)
        display_themed_percent_value(gpu_mem_percent_text_data, memory_percentage)
        display_themed_line_graph(gpu_mem_percent_line_graph_data, cls.last_values_gpu_mem_percentage[0])

    @classmethod
    def _render_legacy_memory_used(cls, theme_gpu_data, memory_used_mb):
        """Render legacy GPU memory used"""
        gpu_mem_used_text_data = theme_gpu_data['MEMORY_USED']['TEXT']
        if math.isnan(memory_used_mb):
            memory_used_mb = 0
            if gpu_mem_used_text_data['SHOW']:
                logger.warning("Your GPU memory absolute usage (M) is not supported yet")
                gpu_mem_used_text_data['SHOW'] = False

        display_themed_value(
            theme_data=gpu_mem_used_text_data,
            value=int(memory_used_mb),
            min_size=5,
            unit=" M"
        )

    @classmethod
    def _render_legacy_memory_total(cls, theme_gpu_data, total_memory_mb):
        """Render legacy GPU total memory"""
        gpu_mem_total_text_data = theme_gpu_data['MEMORY_TOTAL']['TEXT']
        if math.isnan(total_memory_mb):
            total_memory_mb = 0
            if gpu_mem_total_text_data['SHOW']:
                logger.warning("Your GPU total memory capacity (M) is not supported yet")
                gpu_mem_total_text_data['SHOW'] = False

        display_themed_value(
            theme_data=gpu_mem_total_text_data,
            value=int(total_memory_mb),
            min_size=5,
            unit=" M"
        )

    @classmethod
    def _render_legacy_temperature(cls, theme_gpu_data, temperature):
        """Render legacy GPU temperature"""
        gpu_temp_text_data = theme_gpu_data['TEMPERATURE']['TEXT']
        gpu_temp_radial_data = theme_gpu_data['TEMPERATURE']['RADIAL']
        gpu_temp_graph_data = theme_gpu_data['TEMPERATURE']['GRAPH']
        gpu_temp_line_graph_data = theme_gpu_data['TEMPERATURE']['LINE_GRAPH']

        if math.isnan(temperature):
            temperature = 0
            if gpu_temp_text_data['SHOW'] or gpu_temp_radial_data['SHOW'] or gpu_temp_graph_data[
                'SHOW'] or gpu_temp_line_graph_data['SHOW']:
                logger.warning("Your GPU temperature is not supported yet")
                gpu_temp_text_data['SHOW'] = False
                gpu_temp_radial_data['SHOW'] = False
                gpu_temp_graph_data['SHOW'] = False
                gpu_temp_line_graph_data['SHOW'] = False

        display_themed_temperature_value(gpu_temp_text_data, temperature)
        display_themed_progress_bar(gpu_temp_graph_data, temperature)
        display_themed_temperature_radial_bar(gpu_temp_radial_data, temperature)
        display_themed_line_graph(gpu_temp_line_graph_data, cls.last_values_gpu_temperature[0])

    @classmethod
    def _render_legacy_fps(cls, theme_gpu_data, fps):
        """Render legacy GPU FPS"""
        gpu_fps_text_data = theme_gpu_data['FPS']['TEXT']
        gpu_fps_radial_data = theme_gpu_data['FPS']['RADIAL']
        gpu_fps_graph_data = theme_gpu_data['FPS']['GRAPH']
        gpu_fps_line_graph_data = theme_gpu_data['FPS']['LINE_GRAPH']

        if fps < 0:
            fps = 0
            if gpu_fps_text_data['SHOW'] or gpu_fps_radial_data['SHOW'] or gpu_fps_graph_data[
                'SHOW'] or gpu_fps_line_graph_data['SHOW']:
                logger.warning("Your GPU FPS is not supported yet")
                gpu_fps_text_data['SHOW'] = False
                gpu_fps_radial_data['SHOW'] = False
                gpu_fps_graph_data['SHOW'] = False
                gpu_fps_line_graph_data['SHOW'] = False

        display_themed_progress_bar(gpu_fps_graph_data, fps)
        display_themed_value(
            theme_data=gpu_fps_text_data,
            value=int(fps),
            min_size=4,
            unit=" FPS"
        )
        display_themed_radial_bar(
            theme_data=gpu_fps_radial_data,
            value=int(fps),
            min_size=4,
            unit=" FPS"
        )
        display_themed_line_graph(gpu_fps_line_graph_data, cls.last_values_gpu_fps[0])

    @classmethod
    def _render_legacy_fan_speed(cls, theme_gpu_data, fan_percent):
        """Render legacy GPU fan speed"""
        gpu_fan_text_data = theme_gpu_data['FAN_SPEED']['TEXT']
        gpu_fan_radial_data = theme_gpu_data['FAN_SPEED']['RADIAL']
        gpu_fan_graph_data = theme_gpu_data['FAN_SPEED']['GRAPH']
        gpu_fan_line_graph_data = theme_gpu_data['FAN_SPEED']['LINE_GRAPH']

        if math.isnan(fan_percent):
            fan_percent = 0
            if gpu_fan_text_data['SHOW'] or gpu_fan_radial_data['SHOW'] or gpu_fan_graph_data[
                'SHOW'] or gpu_fan_line_graph_data['SHOW']:
                logger.warning("Your GPU Fan Speed is not supported yet")
                gpu_fan_text_data['SHOW'] = False
                gpu_fan_radial_data['SHOW'] = False
                gpu_fan_graph_data['SHOW'] = False
                gpu_fan_line_graph_data['SHOW'] = False

        display_themed_percent_value(gpu_fan_text_data, fan_percent)
        display_themed_progress_bar(gpu_fan_graph_data, fan_percent)
        display_themed_percent_radial_bar(gpu_fan_radial_data, fan_percent)
        display_themed_line_graph(gpu_fan_line_graph_data, cls.last_values_gpu_fan_speed[0])

    @classmethod
    def _render_legacy_frequency(cls, theme_gpu_data, freq_ghz):
        """Render legacy GPU frequency"""
        gpu_freq_text_data = theme_gpu_data['FREQUENCY']['TEXT']
        gpu_freq_radial_data = theme_gpu_data['FREQUENCY']['RADIAL']
        gpu_freq_graph_data = theme_gpu_data['FREQUENCY']['GRAPH']
        gpu_freq_line_graph_data = theme_gpu_data['FREQUENCY']['LINE_GRAPH']
        
        display_themed_value(
            theme_data=gpu_freq_text_data,
            value=f'{freq_ghz:.2f}',
            unit=" GHz",
            min_size=4
        )
        display_themed_progress_bar(gpu_freq_graph_data, freq_ghz)
        display_themed_radial_bar(
            theme_data=gpu_freq_radial_data,
            value=f'{freq_ghz:.2f}',
            unit=" GHz",
            min_size=4
        )
        display_themed_line_graph(gpu_freq_line_graph_data, cls.last_values_gpu_frequency[0])
        
    @classmethod
    def _resize_storage(cls, num_gpus):
        """ Helper to initialize/resize GPU storage lists """
        logger.info(f"Resizing GPU storage for {num_gpus} GPU(s).")
        default_hist_size = DEFAULT_HISTORY_SIZE
        try:
            default_hist_size = config.THEME_DATA['STATS']['GPU'].get('GPU0',{}).get('PERCENTAGE',{}).get('LINE_GRAPH',{}).get('HISTORY_SIZE', DEFAULT_HISTORY_SIZE)
        except:
            pass
            
        # Initialize value lists
        cls.loads = [math.nan] * num_gpus
        cls.memory_percentages = [math.nan] * num_gpus
        cls.memory_used_mbs = [math.nan] * num_gpus
        cls.total_memory_mbs = [math.nan] * num_gpus
        cls.temperatures = [math.nan] * num_gpus
        cls.fps_values = [-1] * num_gpus
        cls.fan_percents = [math.nan] * num_gpus
        cls.frequencies_ghz = [math.nan] * num_gpus
        cls.gpu_names = [""] * num_gpus  # Initialize GPU names array
        
        # Initialize history lists
        cls.last_values_gpu_percentage = [last_values_list(default_hist_size) for _ in range(num_gpus)]
        cls.last_values_gpu_mem_percentage = [last_values_list(default_hist_size) for _ in range(num_gpus)]
        cls.last_values_gpu_temperature = [last_values_list(default_hist_size) for _ in range(num_gpus)]
        cls.last_values_gpu_fps = [last_values_list(default_hist_size) for _ in range(num_gpus)]
        cls.last_values_gpu_fan_speed = [last_values_list(default_hist_size) for _ in range(num_gpus)]
        cls.last_values_gpu_frequency = [last_values_list(default_hist_size) for _ in range(num_gpus)]


    @classmethod
    def _update_history(cls, gpu_index):
        """ Helper to update history for a specific GPU """
        if gpu_index >= len(cls.last_values_gpu_percentage):
            return  # Safety check
            
        hist_size = len(cls.last_values_gpu_percentage[gpu_index])  # Get size from list itself
        
        save_last_value(cls.loads[gpu_index], cls.last_values_gpu_percentage[gpu_index], hist_size)
        save_last_value(cls.memory_percentages[gpu_index], cls.last_values_gpu_mem_percentage[gpu_index], hist_size)
        save_last_value(cls.temperatures[gpu_index], cls.last_values_gpu_temperature[gpu_index], hist_size)
        save_last_value(float(cls.fps_values[gpu_index]), cls.last_values_gpu_fps[gpu_index], hist_size)
        save_last_value(cls.fan_percents[gpu_index], cls.last_values_gpu_fan_speed[gpu_index], hist_size)
        save_last_value(cls.frequencies_ghz[gpu_index], cls.last_values_gpu_frequency[gpu_index], hist_size)

    @classmethod
    def _render_gpu_stat(cls, gpu_theme_section, stat_key, value, history_list, text_func, radial_func):
        """ Helper to render common stat types """
        # Method remains unchanged
        if stat_key in gpu_theme_section:
            theme_def = gpu_theme_section[stat_key]
            if theme_def:  # Check if theme definition exists
                if 'TEXT' in theme_def:
                    text_func(theme_def.get('TEXT',{}), value)
                if 'GRAPH' in theme_def:
                    display_themed_progress_bar(theme_def.get('GRAPH',{}), value)
                if 'RADIAL' in theme_def:
                    radial_func(theme_def.get('RADIAL',{}), value)
                if 'LINE_GRAPH' in theme_def:
                    display_themed_line_graph(theme_def.get('LINE_GRAPH',{}), history_list)

    @classmethod
    def _render_gpu_stat_custom_format(cls, gpu_theme_section, stat_key, value, unit, min_size, format_str='{}', history_list=None):
        """ Helper to render stats requiring specific formatting """
        if stat_key in gpu_theme_section:
            theme_def = gpu_theme_section[stat_key] # Check if theme definition exists
            
            if theme_def:
                is_nan_value = value is None or math.isnan(value)
                display_value = 0 if is_nan_value else value

                try: # Attempt to format the value
                    formatted_val_str = "N/A" if is_nan_value else format_str.format(value)
                except:
                    formatted_val_str = "N/A"

                if 'TEXT' in theme_def:
                    display_themed_value(theme_def.get('TEXT',{}), formatted_val_str, unit=unit, min_size=min_size)
                if 'GRAPH' in theme_def:
                    display_themed_progress_bar(theme_def.get('GRAPH',{}), display_value)
                if 'RADIAL' in theme_def:
                    radial_text = "N/A"
                    if not is_nan_value: # Only format if value is valid
                        radial_text = f"{formatted_val_str}{unit}" if theme_def.get('RADIAL',{}).get("SHOW_UNIT", True) else formatted_val_str
                    display_themed_radial_bar(theme_def.get('RADIAL',{}), display_value, custom_text=radial_text) # Pass the potentially 0 value
                if 'LINE_GRAPH' in theme_def and history_list is not None:
                    # Note: save_last_value already handles appending NaN to history
                    display_themed_line_graph(theme_def.get('LINE_GRAPH',{}), history_list)

    @staticmethod
    def is_available():
        return sensors.Gpu.is_available()

class Memory:
    last_values_memory_swap = []
    last_values_memory_virtual = []

    @classmethod
    def stats(cls):
        memory_stats_theme_data = config.THEME_DATA['STATS']['MEMORY']

        swap_percent = sensors.Memory.swap_percent()
        save_last_value(swap_percent, cls.last_values_memory_swap,
                        memory_stats_theme_data['SWAP']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        display_themed_progress_bar(memory_stats_theme_data['SWAP']['GRAPH'], swap_percent)
        display_themed_percent_radial_bar(memory_stats_theme_data['SWAP']['RADIAL'], swap_percent)
        display_themed_line_graph(memory_stats_theme_data['SWAP']['LINE_GRAPH'], cls.last_values_memory_swap)

        virtual_percent = sensors.Memory.virtual_percent()
        save_last_value(virtual_percent, cls.last_values_memory_virtual,
                        memory_stats_theme_data['VIRTUAL']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        display_themed_progress_bar(memory_stats_theme_data['VIRTUAL']['GRAPH'], virtual_percent)
        display_themed_percent_radial_bar(memory_stats_theme_data['VIRTUAL']['RADIAL'], virtual_percent)
        display_themed_percent_value(memory_stats_theme_data['VIRTUAL']['PERCENT_TEXT'], virtual_percent)
        display_themed_line_graph(memory_stats_theme_data['VIRTUAL']['LINE_GRAPH'], cls.last_values_memory_virtual)

        display_themed_value(
            theme_data=memory_stats_theme_data['VIRTUAL']['USED'],
            value=int(sensors.Memory.virtual_used() / 1024 ** 2),
            min_size=5,
            unit=" M"
        )
        display_themed_value(
            theme_data=memory_stats_theme_data['VIRTUAL']['FREE'],
            value=int(sensors.Memory.virtual_free() / 1024 ** 2),
            min_size=5,
            unit=" M"
        )
        display_themed_value(
            theme_data=memory_stats_theme_data['VIRTUAL']['TOTAL'],
            value=int((sensors.Memory.virtual_free() + sensors.Memory.virtual_used()) / 1024 ** 2),
            min_size=5,
            unit=" M"
        )


class Disk:
    last_values_disk_usage = []

    @classmethod
    def stats(cls):
        used = sensors.Disk.disk_used()
        free = sensors.Disk.disk_free()

        disk_theme_data = config.THEME_DATA['STATS']['DISK']

        disk_usage_percent = sensors.Disk.disk_usage_percent()
        save_last_value(disk_usage_percent, cls.last_values_disk_usage,
                        disk_theme_data['USED']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        display_themed_progress_bar(disk_theme_data['USED']['GRAPH'], disk_usage_percent)
        display_themed_percent_radial_bar(disk_theme_data['USED']['RADIAL'], disk_usage_percent)
        display_themed_percent_value(disk_theme_data['USED']['PERCENT_TEXT'], disk_usage_percent)
        display_themed_line_graph(disk_theme_data['USED']['LINE_GRAPH'], cls.last_values_disk_usage)

        display_themed_value(
            theme_data=disk_theme_data['USED']['TEXT'],
            value=int(used / 1000000000),
            min_size=5,
            unit=" G"
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
    last_values_wlo_upload = []
    last_values_wlo_download = []
    last_values_eth_upload = []
    last_values_eth_download = []

    @classmethod
    def stats(cls):
        net_theme_data = config.THEME_DATA['STATS']['NET']
        interval = net_theme_data.get("INTERVAL", None)
        upload_wlo, uploaded_wlo, download_wlo, downloaded_wlo = sensors.Net.stats(WLO_CARD, interval)

        save_last_value(upload_wlo, cls.last_values_wlo_upload,
                        net_theme_data['WLO']['UPLOAD']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        Net._show_themed_tax_rate(net_theme_data['WLO']['UPLOAD']['TEXT'], upload_wlo)
        Net._show_themed_total_data(net_theme_data['WLO']['UPLOADED']['TEXT'], uploaded_wlo)
        display_themed_line_graph(net_theme_data['WLO']['UPLOAD']['LINE_GRAPH'], cls.last_values_wlo_upload)

        save_last_value(download_wlo, cls.last_values_wlo_download,
                        net_theme_data['WLO']['DOWNLOAD']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        Net._show_themed_tax_rate(net_theme_data['WLO']['DOWNLOAD']['TEXT'], download_wlo)
        Net._show_themed_total_data(net_theme_data['WLO']['DOWNLOADED']['TEXT'], downloaded_wlo)
        display_themed_line_graph(net_theme_data['WLO']['DOWNLOAD']['LINE_GRAPH'], cls.last_values_wlo_download)

        upload_eth, uploaded_eth, download_eth, downloaded_eth = sensors.Net.stats(ETH_CARD, interval)

        save_last_value(upload_eth, cls.last_values_eth_upload,
                        net_theme_data['ETH']['UPLOAD']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        Net._show_themed_tax_rate(net_theme_data['ETH']['UPLOAD']['TEXT'], upload_eth)
        Net._show_themed_total_data(net_theme_data['ETH']['UPLOADED']['TEXT'], uploaded_eth)
        display_themed_line_graph(net_theme_data['ETH']['UPLOAD']['LINE_GRAPH'], cls.last_values_eth_upload)

        save_last_value(download_eth, cls.last_values_eth_download,
                        net_theme_data['ETH']['DOWNLOAD']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        Net._show_themed_tax_rate(net_theme_data['ETH']['DOWNLOAD']['TEXT'], download_eth)
        Net._show_themed_total_data(net_theme_data['ETH']['DOWNLOADED']['TEXT'], downloaded_eth)
        display_themed_line_graph(net_theme_data['ETH']['DOWNLOAD']['LINE_GRAPH'], cls.last_values_eth_download)

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

        try:
            if platform.system() == "Windows":
                # Windows does not have LC_TIME environment variable, use deprecated getdefaultlocale() that returns language code following RFC 1766
                lc_time = locale.getdefaultlocale()[0]
            else:
                lc_time = babel.dates.LC_TIME
        except:
            lc_time = None

        if not lc_time:
            lc_time = "en_US"

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


class SystemUptime:
    @staticmethod
    def stats():
        if HW_SENSORS == "STATIC":
            # For static sensors, use predefined uptime
            uptimesec = 4294036
        else:
            uptimesec = int(uptime())

        uptimeformatted = str(datetime.timedelta(seconds=uptimesec))

        systemuptime_theme_data = config.THEME_DATA['STATS']['UPTIME']

        systemuptime_sec_theme_data = systemuptime_theme_data['SECONDS']['TEXT']
        display_themed_value(
            theme_data=systemuptime_sec_theme_data,
            value=uptimesec
        )

        systemuptime_formatted_theme_data = systemuptime_theme_data['FORMATTED']['TEXT']
        display_themed_value(
            theme_data=systemuptime_formatted_theme_data,
            value=uptimeformatted
        )


class Custom:
    @staticmethod
    def stats():
        for custom_stat in config.THEME_DATA['STATS']['CUSTOM']:
            if custom_stat != "INTERVAL":

                # Load the custom sensor class from sensors_custom.py based on the class name
                try:
                    custom_stat_class = getattr(sensors_custom, str(custom_stat))()
                    numeric_value = custom_stat_class.as_numeric()
                    string_value = custom_stat_class.as_string()
                    last_values = custom_stat_class.last_values()
                except Exception as e:
                    logger.error(
                        "Error loading custom sensor class " + str(custom_stat) + " from sensors_custom.py : " + str(e))
                    return

                if string_value is None:
                    string_value = str(numeric_value)

                # Display text
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("TEXT", None)
                if theme_data is not None and string_value is not None:
                    display_themed_value(theme_data=theme_data, value=string_value)

                # Display graph from numeric value
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("GRAPH", None)
                if theme_data is not None and numeric_value is not None and not math.isnan(numeric_value):
                    display_themed_progress_bar(theme_data=theme_data, value=numeric_value)

                # Display radial from numeric and text value
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("RADIAL", None)
                if theme_data is not None and numeric_value is not None and not math.isnan(
                        numeric_value) and string_value is not None:
                    display_themed_radial_bar(
                        theme_data=theme_data,
                        value=numeric_value,
                        custom_text=string_value
                    )

                # Display plot graph from histo values
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("LINE_GRAPH", None)
                if theme_data is not None and last_values is not None:
                    display_themed_line_graph(theme_data=theme_data, values=last_values)


class Weather:
    @staticmethod
    def stats():
        WEATHER_UNITS = {'metric': '°C', 'imperial': '°F', 'standard': '°K'}

        weather_theme_data = config.THEME_DATA['STATS'].get('WEATHER', {})
        wtemperature_theme_data = weather_theme_data.get('TEMPERATURE', {}).get('TEXT', {})
        wfelt_theme_data = weather_theme_data.get('TEMPERATURE_FELT', {}).get('TEXT', {})
        wupdatetime_theme_data = weather_theme_data.get('UPDATE_TIME', {}).get('TEXT', {})
        wdescription_theme_data = weather_theme_data.get('WEATHER_DESCRIPTION', {}).get('TEXT', {})
        whumidity_theme_data = weather_theme_data.get('HUMIDITY', {}).get('TEXT', {})

        activate = True if wtemperature_theme_data.get("SHOW") or wfelt_theme_data.get(
            "SHOW") or wupdatetime_theme_data.get("SHOW") or wdescription_theme_data.get(
            "SHOW") or whumidity_theme_data.get("SHOW") else False

        if activate:
            temp = None
            feel = None
            time = None
            humidity = None
            if HW_SENSORS in ["STATIC", "STUB"]:
                temp = "17.5°C"
                feel = "(17.2°C)"
                desc = "Cloudy"
                time = "@15:33"
                humidity = "45%"
            else:
                # API Parameters
                lat = config.CONFIG_DATA['config'].get('WEATHER_LATITUDE', "")
                lon = config.CONFIG_DATA['config'].get('WEATHER_LONGITUDE', "")
                api_key = config.CONFIG_DATA['config'].get('WEATHER_API_KEY', "")
                units = config.CONFIG_DATA['config'].get('WEATHER_UNITS', "metric")
                lang = config.CONFIG_DATA['config'].get('WEATHER_LANGUAGE', "en")
                deg = WEATHER_UNITS.get(units, '°?')
                if api_key:
                    url = f'https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily,alerts&appid={api_key}&units={units}&lang={lang}'
                    try:
                        response = requests.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            temp = f"{data['current']['temp']:.1f}{deg}"
                            feel = f"({data['current']['feels_like']:.1f}{deg})"
                            desc = data['current']['weather'][0]['description'].capitalize()
                            humidity = f"{data['current']['humidity']:.0f}%"
                            now = datetime.datetime.now()
                            time = f"@{now.hour:02d}:{now.minute:02d}"
                        else:
                            logger.error(f"Error {response.status_code} fetching OpenWeatherMap API:")
                            # logger.error(f"Response content: {response.content}")
                            # logger.error(response.text)
                            desc = response.json().get('message')
                    except Exception as e:
                        logger.error(f"Error fetching OpenWeatherMap API: {str(e)}")
                        desc = "Error fetching OpenWeatherMap API"
                else:
                    logger.warning("No OpenWeatherMap API key provided in config.yaml")
                    desc = "No OpenWeatherMap API key"

        if activate:
            # Display Temperature
            display_themed_value(theme_data=wtemperature_theme_data, value=temp)
            # Display Temperature Felt
            display_themed_value(theme_data=wfelt_theme_data, value=feel)
            # Display Update Time
            display_themed_value(theme_data=wupdatetime_theme_data, value=time)
            # Display Humidity
            display_themed_value(theme_data=whumidity_theme_data, value=humidity)
            # Display Weather Description (or error message)
            display_themed_value(theme_data=wdescription_theme_data, value=desc)


class Ping:
    last_values_ping = []

    @classmethod
    def stats(cls):
        theme_data = config.THEME_DATA['STATS']['PING']

        delay = ping(dest_addr=PING_DEST, unit="ms")

        save_last_value(delay, cls.last_values_ping,
                        theme_data['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        # logger.debug(f"Ping delay: {delay}ms")

        display_themed_progress_bar(theme_data['GRAPH'], delay)
        display_themed_radial_bar(
            theme_data=theme_data['RADIAL'],
            value=int(delay),
            unit="ms",
            min_size=6
        )
        display_themed_value(
            theme_data=theme_data['TEXT'],
            value=int(delay),
            unit="ms",
            min_size=6
        )
        display_themed_line_graph(theme_data['LINE_GRAPH'], cls.last_values_ping)