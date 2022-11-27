import math

import GPUtil
import psutil
from psutil._common import bytes2human

import datetime

# AMD GPU on Linux
try:
    import pyamdgpuinfo
except:
    pyamdgpuinfo = None

# AMD GPU on Windows
try:
    import pyadl
except:
    pyadl = None

import library.config as config
from library.display import display
from library.log import logger

THEME_DATA = config.THEME_DATA
CONFIG_DATA = config.CONFIG_DATA
ETH_CARD = CONFIG_DATA["config"]["ETH"]
WLO_CARD = CONFIG_DATA["config"]["WLO"]

def get_full_path(path, name):
    if name:
        return path + name
    else:
        return None


class CPU:
    @staticmethod
    def percentage():
        cpu_percentage = psutil.cpu_percent(interval=THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", None))
        # logger.debug(f"CPU Percentage: {cpu_percentage}")

        if THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(cpu_percentage):>3}%",
                x=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                      (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                    None))
            )

        if THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("HEIGHT", 0),
                value=int(cpu_percentage),
                min_value=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                       (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_IMAGE",
                                                                                                     None))
            )

    @staticmethod
    def frequency():
        cpu_freq = psutil.cpu_freq()

        if THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=str(f'{int(cpu_freq.current) / 1000:.2f}') + " GHz",
                x=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("BACKGROUND_COLOR",
                                                                                     (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                   None))
            )

    @staticmethod
    def load():
        cpu_load = psutil.getloadavg()
        # logger.debug(f"CPU Load: ({cpu_load[0]},{cpu_load[1]},{cpu_load[2]})")

        if THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(cpu_load[0]):>3}%",
                x=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT",
                                                                           "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                       (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                     None))
            )

        if THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(cpu_load[1]):>3}%",
                x=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT",
                                                                            "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                        (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get(
                                                   "BACKGROUND_IMAGE", None))
            )

        if THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(cpu_load[2]):>3}%",
                x=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT",
                                                                               "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("BACKGROUND_COLOR",
                                                                                           (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get(
                                                   "BACKGROUND_IMAGE", None))
            )

    @staticmethod
    def is_temperature_available():
        try:
            sensors_temps = psutil.sensors_temperatures()
            if 'coretemp' in sensors_temps or 'k10temp' in sensors_temps or 'cpu_thermal' in sensors_temps:
                return True
            else:
                return False
        except AttributeError:
            # sensors_temperatures may not be available at all
            return False

    @staticmethod
    def temperature():
        cpu_temp = 0
        sensors_temps = psutil.sensors_temperatures()
        if 'coretemp' in sensors_temps:
            # Intel CPU
            cpu_temp = sensors_temps['coretemp'][0].current
        elif 'k10temp' in sensors_temps:
            # AMD CPU
            cpu_temp = sensors_temps['k10temp'][0].current
        elif 'cpu_thermal' in sensors_temps:
            # ARM CPU
            cpu_temp = sensors_temps['cpu_thermal'][0].current

        if THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(cpu_temp):>3}°C",
                x=THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("FONT",
                                                                           "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                       (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                     None))
            )
        # TODO: Built in function for *nix in psutil, for Windows can use WMI or a third party library


def display_gpu_stats(load, memory_percentage, memory_used_mb, temperature):
    if THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("SHOW", False):
        if math.isnan(load):
            logger.warning("Your GPU load is not supported yet")
            THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH']['SHOW'] = False
            THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT']['SHOW'] = False
        else:
            # logger.debug(f"GPU Load: {load}")
            display.lcd.DisplayProgressBar(
                x=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("HEIGHT", 0),
                value=int(load),
                min_value=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                       (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_IMAGE",
                                                                                                     None))
            )

    if THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("SHOW", False):
        if math.isnan(load):
            logger.warning("Your GPU load is not supported yet")
            THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH']['SHOW'] = False
            THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT']['SHOW'] = False
        else:
            display.lcd.DisplayText(
                text=f"{int(load):>3}%",
                x=THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                      (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['PERCENTAGE']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                    None))
            )

    if THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("SHOW", False):
        if math.isnan(memory_percentage):
            logger.warning("Your GPU memory relative usage (%) is not supported yet")
            THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH']['SHOW'] = False
        else:
            display.lcd.DisplayProgressBar(
                x=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("HEIGHT", 0),
                value=int(memory_percentage),
                min_value=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                       (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BACKGROUND_IMAGE",
                                                                                                 None))
            )

    if THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("SHOW", False):
        if math.isnan(memory_used_mb):
            logger.warning("Your GPU memory absolute usage (M) is not supported yet")
            THEME_DATA['STATS']['GPU']['MEMORY']['TEXT']['SHOW'] = False
        else:
            display.lcd.DisplayText(
                text=f"{int(memory_used_mb):>5} M",
                x=THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['MEMORY']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                None))
            )

    if THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("SHOW", False):
        if math.isnan(temperature):
            logger.warning("Your GPU temperature is not supported yet")
            THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT']['SHOW'] = False
        else:
            display.lcd.DisplayText(
                text=f"{int(temperature):>3}°C",
                x=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT",
                                                                           "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_COLOR",
                                                                                       (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                     None))
            )
    pass


class GpuNvidia:
    @staticmethod
    def stats():
        # Unlike the CPU, the GPU pulls in all the stats at once
        nvidia_gpus = GPUtil.getGPUs()

        try:
            memory_used_all = [item.memoryUsed for item in nvidia_gpus]
            memory_used_mb = sum(memory_used_all) / len(memory_used_all)
        except:
            memory_used_mb = math.nan

        try:
            memory_total_all = [item.memoryTotal for item in nvidia_gpus]
            memory_total_mb = sum(memory_total_all) / len(memory_total_all)
            memory_percentage = (memory_used_mb / memory_total_mb) * 100
        except:
            memory_percentage = math.nan

        try:
            load_all = [item.load for item in nvidia_gpus]
            load = (sum(load_all) / len(load_all)) * 100
        except:
            load = math.nan

        try:
            temperature_all = [item.temperature for item in nvidia_gpus]
            temperature = sum(temperature_all) / len(temperature_all)
        except:
            temperature = math.nan

        display_gpu_stats(load, memory_percentage, memory_used_mb, temperature)

    @staticmethod
    def is_available():
        return len(GPUtil.getGPUs()) > 0


class GpuAmd:
    @staticmethod
    def stats():
        # Unlike the CPU, the GPU pulls in all the stats at once
        if pyamdgpuinfo:
            i = 0
            amd_gpus = []
            while i < pyamdgpuinfo.detect_gpus():
                amd_gpus.append(pyamdgpuinfo.get_gpu(i))
                i = i + 1

            try:
                memory_used_all = [item.query_vram_usage() for item in amd_gpus]
                memory_used_bytes = sum(memory_used_all) / len(memory_used_all)
                memory_used = memory_used_bytes / 1000000
            except:
                memory_used_bytes = math.nan
                memory_used = math.nan

            try:
                memory_total_all = [item.memory_info["vram_size"] for item in amd_gpus]
                memory_total_bytes = sum(memory_total_all) / len(memory_total_all)
                memory_percentage = (memory_used_bytes / memory_total_bytes) * 100
            except:
                memory_percentage = math.nan

            try:
                load_all = [item.query_load() for item in amd_gpus]
                load = (sum(load_all) / len(load_all)) * 100
            except:
                load = math.nan

            try:
                temperature_all = [item.query_temperature() for item in amd_gpus]
                temperature = sum(temperature_all) / len(temperature_all)
            except:
                temperature = math.nan

            display_gpu_stats(load, memory_percentage, memory_used, temperature)
        elif pyadl:
            amd_gpus = pyadl.ADLManager.getInstance().getDevices()

            try:
                load_all = [item.getCurrentUsage() for item in amd_gpus]
                load = (sum(load_all) / len(load_all))
            except:
                load = math.nan

            try:
                temperature_all = [item.getCurrentTemperature() for item in amd_gpus]
                temperature = sum(temperature_all) / len(temperature_all)
            except:
                temperature = math.nan

            # Memory absolute (M) and relative (%) usage not supported by pyadl
            display_gpu_stats(load, math.nan, math.nan, temperature)

    @staticmethod
    def is_available():
        if pyamdgpuinfo and pyamdgpuinfo.detect_gpus() > 0:
            return True
        elif pyadl and len(pyadl.ADLManager.getInstance().getDevices()) > 0:
            return True
        else:
            return False


class Memory:
    @staticmethod
    def stats():
        swap_percent = psutil.swap_memory().percent

        if THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("HEIGHT", 0),
                value=int(swap_percent),
                min_value=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                    (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BACKGROUND_IMAGE",
                                                                                                  None))
            )

        virtual_percent = psutil.virtual_memory().percent

        if THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("HEIGHT", 0),
                value=int(virtual_percent),
                min_value=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BACKGROUND_COLOR",
                                                                                       (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BACKGROUND_IMAGE",
                                                                                                     None))
            )

        if THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(virtual_percent):>3}%",
                x=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("FONT",
                                                                                  "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get("BACKGROUND_COLOR",
                                                                                              (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['MEMORY']['VIRTUAL']['PERCENT_TEXT'].get(
                                                   "BACKGROUND_IMAGE", None))
            )

        virtual_used = psutil.virtual_memory().used

        if THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(virtual_used / 1000000):>5} M",
                x=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("X", 0),
                y=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("Y", 0),
                font=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("FONT",
                                                                                "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get("BACKGROUND_COLOR",
                                                                                            (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['MEMORY']['VIRTUAL']['USED'].get(
                                                   "BACKGROUND_IMAGE", None))
            )

        virtual_used = psutil.virtual_memory().free

        if THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(virtual_used / 1000000):>5} M",
                x=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("X", 0),
                y=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("Y", 0),
                font=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("FONT",
                                                                                "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("BACKGROUND_COLOR",
                                                                                            (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get(
                                                   "BACKGROUND_IMAGE", None))
            )


class Disk:
    @staticmethod
    def stats():
        disk_usage = psutil.disk_usage("/")

        if THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("HEIGHT", 0),
                value=int(disk_usage.percent),
                min_value=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("BACKGROUND_IMAGE",
                                                                                                None))
            )

        if THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(disk_usage.used / 1000000000):>5} G",
                x=THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DISK']['USED']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(disk_usage.percent):>3}%",
                x=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(disk_usage.total / 1000000000):>5} G",
                x=THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                None))
            )

        if THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(disk_usage.free / 1000000000):>5} G",
                x=THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DISK']['FREE']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )


class Net:
    @staticmethod
    def stats():
        pnic_after = psutil.net_io_counters(pernic=True)
        if config.PNIC_BEFORE:
            pnic_before = config.PNIC_BEFORE
        else:
            pnic_before = pnic_after

        if WLO_CARD in pnic_after:
            upload_wlo = pnic_after[WLO_CARD].bytes_sent - pnic_before[WLO_CARD].bytes_sent
            upload_wlo_text = f"{bytes2human(upload_wlo)}/s"
            uploaded_wlo = pnic_after[WLO_CARD].bytes_sent
            uploaded_wlo_text = f"{bytes2human(uploaded_wlo)}"
            download_wlo = pnic_after[WLO_CARD].bytes_recv - pnic_before[WLO_CARD].bytes_recv
            download_wlo_text = f"{bytes2human(download_wlo)}/s"
            downloaded_wlo = pnic_after[WLO_CARD].bytes_recv
            downloaded_wlo_text = f"{bytes2human(downloaded_wlo)}"
        else:
            upload_wlo_text = f"N/A"
            uploaded_wlo_text = f"N/A"
            download_wlo_text = f"N/A"
            downloaded_wlo_text = f"N/A"
        
        if ETH_CARD in pnic_after:
            upload_eth = pnic_after[ETH_CARD].bytes_sent - pnic_before[ETH_CARD].bytes_sent
            upload_eth_text = f"{bytes2human(upload_eth)}/s"
            uploaded_eth = pnic_after[ETH_CARD].bytes_sent
            uploaded_eth_text = f"{bytes2human(uploaded_eth)}"
            download_eth = pnic_after[ETH_CARD].bytes_recv - pnic_before[ETH_CARD].bytes_recv
            download_eth_text = f"{bytes2human(download_eth)}/s"
            downloaded_eth = pnic_after[ETH_CARD].bytes_recv
            downloaded_eth_text = f"{bytes2human(downloaded_eth)}"
        else:
            upload_eth_text = f"N/A"
            uploaded_eth_text = f"N/A"
            download_eth_text = f"N/A"
            downloaded_eth_text = f"N/A"

        if THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{upload_wlo_text:<8}",
                x=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{uploaded_wlo_text:<6}",
                x=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{download_wlo_text:<8}",
                x=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{downloaded_wlo_text:<6}",
                x=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{upload_eth_text:<8}",
                x=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{uploaded_eth_text:<6}",
                x=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{download_eth_text:<8}",
                x=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{downloaded_eth_text:<6}",
                x=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )
        
        config.PNIC_BEFORE = psutil.net_io_counters(pernic=True)


class Date:
    @staticmethod
    def stats():
        date_now = datetime.datetime.now()

        if THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{date_now.strftime('%d-%m-%Y')}",
                x=THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DATE']['DAY']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                               None))
            )

        if THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{date_now.strftime('%H:%M:%S')}",
                x=THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DATE']['HOUR']['TEXT'].get("BACKGROUND_IMAGE",
                                                                                                None))
            )
