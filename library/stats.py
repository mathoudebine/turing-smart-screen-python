import datetime
import math
import os
import platform
import sys

from psutil._common import bytes2human

import library.config as config
from library.display import display
from library.log import logger

THEME_DATA = config.THEME_DATA
CONFIG_DATA = config.CONFIG_DATA
ETH_CARD = CONFIG_DATA["config"]["ETH"]
WLO_CARD = CONFIG_DATA["config"]["WLO"]
HW_SENSORS = CONFIG_DATA["config"]["HW_SENSORS"]

if HW_SENSORS == "PYTHON":
    import library.sensors.sensors_python as sensors
elif HW_SENSORS == "LHM":
    pass
elif HW_SENSORS == "STUB":
    import library.sensors.sensors_stub as sensors
elif HW_SENSORS == "AUTO":
    if platform.system() == 'Windows':
        pass
    else:
        import library.sensors.sensors_python as sensors
else:
    logger.error("Unsupported SENSORS value in config.yaml")
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
        cpu_percentage = sensors.Cpu.percentage(interval=THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", None))
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
        cpu_freq = sensors.Cpu.frequency()

        if THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=str(f'{int(cpu_freq) / 1000:.2f}') + " GHz",
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
        cpu_load = sensors.Cpu.load()
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
        return sensors.Cpu.is_temperature_available()

    @staticmethod
    def temperature():
        cpu_temp = sensors.Cpu.temperature()

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

        virtual_percent = sensors.Memory.virtual_percent()

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

        virtual_used = sensors.Memory.virtual_used()

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

        virtual_free = sensors.Memory.virtual_free()

        if THEME_DATA['STATS']['MEMORY']['VIRTUAL']['FREE'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int(virtual_free / 1000000):>5} M",
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
        used = sensors.Disk.disk_used()
        free = sensors.Disk.disk_free()
        if THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("SHOW", False):
            display.lcd.DisplayProgressBar(
                x=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['DISK']['USED']['GRAPH'].get("HEIGHT", 0),
                value=int(sensors.Disk.disk_usage_percent()),
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
                text=f"{int(used / 1000000000):>5} G",
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
                text=f"{int(sensors.Disk.disk_usage_percent()):>3}%",
                x=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT",
                                                                             "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get("BACKGROUND_COLOR",
                                                                                         (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DISK']['USED']['PERCENT_TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if THEME_DATA['STATS']['DISK']['TOTAL']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{int((free + used) / 1000000000):>5} G",
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
                text=f"{int(free / 1000000000):>5} G",
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
        interval = THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", None)
        upload_wlo, uploaded_wlo, download_wlo, downloaded_wlo = sensors.Net.stats(WLO_CARD, interval)

        upload_wlo_text = f"{bytes2human(upload_wlo)}/s"
        uploaded_wlo_text = f"{bytes2human(uploaded_wlo)}"
        download_wlo_text = f"{bytes2human(download_wlo)}/s"
        downloaded_wlo_text = f"{bytes2human(downloaded_wlo)}"

        if THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{upload_wlo_text:>8}",
                x=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT",
                                                                             "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get("BACKGROUND_COLOR",
                                                                                         (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['WLO']['UPLOAD']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{uploaded_wlo_text:>6}",
                x=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT",
                                                                               "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                           (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['WLO']['UPLOADED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{download_wlo_text:>8}",
                x=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT",
                                                                               "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get("BACKGROUND_COLOR",
                                                                                           (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['WLO']['DOWNLOAD']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{downloaded_wlo_text:>6}",
                x=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT",
                                                                                 "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                             (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['WLO']['DOWNLOADED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        upload_eth, uploaded_eth, download_eth, downloaded_eth = sensors.Net.stats(ETH_CARD, interval)

        upload_eth_text = f"{bytes2human(upload_eth)}/s"
        uploaded_eth_text = f"{bytes2human(uploaded_eth)}"
        download_eth_text = f"{bytes2human(download_eth)}/s"
        downloaded_eth_text = f"{bytes2human(downloaded_eth)}"

        if THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{upload_eth_text:>8}",
                x=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT",
                                                                             "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get("BACKGROUND_COLOR",
                                                                                         (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['ETH']['UPLOAD']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{uploaded_eth_text:>6}",
                x=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT",
                                                                               "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                           (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['ETH']['UPLOADED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{download_eth_text:>8}",
                x=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT",
                                                                               "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get("BACKGROUND_COLOR",
                                                                                           (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['ETH']['DOWNLOAD']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )

        if THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("SHOW", False):
            display.lcd.DisplayText(
                text=f"{downloaded_eth_text:>6}",
                x=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT",
                                                                                 "roboto-mono/RobotoMono-Regular.ttf"),
                font_size=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get("BACKGROUND_COLOR",
                                                                                             (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['NET']['ETH']['DOWNLOADED']['TEXT'].get(
                                                   "BACKGROUND_IMAGE",
                                                   None))
            )


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
