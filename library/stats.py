import GPUtil
import psutil
import pyamdgpuinfo

import library.config as config
import library.lcd_comm as lcd

THEME_DATA = config.THEME_DATA


def get_full_path(path, name):
    if name:
        return path + name
    else:
        return None


class CPU:
    @staticmethod
    def percentage():
        cpu_percentage = psutil.cpu_percent(interval=THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", None))
        # print(f"CPU Percentage: {cpu_percentage}")

        if THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("SHOW", False):
            lcd.DisplayText(
                ser=config.lcd_comm,
                text=str(int(cpu_percentage)).zfill(3),
                x=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT", "roboto/Roboto-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['PERCENTAGE']['TEXT'].get("BACKGROUND_IMAGE", None))
            )

        if THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("SHOW", False):
            lcd.DisplayProgressBar(
                ser=config.lcd_comm,
                x=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("HEIGHT", 0),
                value=int(cpu_percentage),
                min_value=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_IMAGE", None))
            )

    @staticmethod
    def frequency():
        cpu_freq = psutil.cpu_freq()

        if THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("SHOW", False):
            lcd.DisplayText(
                ser=config.lcd_comm,
                text=str(f'{int(cpu_freq.current)/1000:.2f}') + " GHz",
                x=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT", "roboto/Roboto-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['FREQUENCY']['TEXT'].get("BACKGROUND_IMAGE", None))
            )

    @staticmethod
    def load():
        cpu_load = psutil.getloadavg()
        # print(f"CPU Load: ({cpu_load[0]},{cpu_load[1]},{cpu_load[2]})")

        if THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("SHOW", False):
            lcd.DisplayText(
                ser=config.lcd_comm,
                text=f"{str(int(cpu_load[0]))}%",
                x=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT", "roboto/Roboto-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['LOAD']['ONE']['TEXT'].get("BACKGROUND_IMAGE", None))
            )

        if THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("SHOW", False):
            lcd.DisplayText(
                ser=config.lcd_comm,
                text=f"{str(int(cpu_load[1]))}%",
                x=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT", "roboto/Roboto-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['LOAD']['FIVE']['TEXT'].get("BACKGROUND_IMAGE", None))
            )

        if THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("SHOW", False):
            lcd.DisplayText(
                ser=config.lcd_comm,
                text=f"{str(int(cpu_load[2]))}%",
                x=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT", "roboto/Roboto-Regular.ttf"),
                font_size=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['CPU']['LOAD']['FIFTEEN']['TEXT'].get("BACKGROUND_IMAGE", None))
            )

    @staticmethod
    def Temperature():
        pass
        # TODO: Built in function for *nix in psutil, for Windows can use WMI or a third party library


class GpuNvidia:
    @staticmethod
    def stats():
        # Unlike the CPU, the GPU pulls in all the stats at once
        gpu_data = GPUtil.getGPUs()

        memory_used_all = [item.memoryUsed for item in gpu_data]
        memory_used = sum(memory_used_all) / len(memory_used_all)

        memory_total_all = [item.memoryTotal for item in gpu_data]
        memory_total = sum(memory_total_all) / len(memory_total_all)

        memory_percentage = (memory_used / memory_total) * 100

        load_all = [item.load for item in gpu_data]
        load = (sum(load_all) / len(load_all)) * 100

        temperature_all = [item.temperature for item in gpu_data]
        temperature = sum(temperature_all) / len(temperature_all)

        if THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("SHOW", False):
            # print(f"GPU Load: {load}")
            lcd.DisplayProgressBar(
                ser=config.lcd_comm,
                x=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("HEIGHT", 0),
                value=int(load),
                min_value=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_IMAGE", None))
            )

        if THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("SHOW", False):
            # print(f"GPU Load: {load}")
            lcd.DisplayProgressBar(
                ser=config.lcd_comm,
                x=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("HEIGHT", 0),
                value=int(memory_percentage),
                min_value=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['PATH'] + THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BACKGROUND_IMAGE", None))
            )

        if THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("SHOW", False):
            lcd.DisplayText(
                ser=config.lcd_comm,
                text=f"{str(int(temperature))}* c",
                x=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT", "roboto/Roboto-Regular.ttf"),
                font_size=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_IMAGE", None))
            )
    @staticmethod
    def is_available():
        return len(GPUtil.getGPUs()) > 0


class GpuAmd:
    @staticmethod
    def stats():
        # Unlike the CPU, the GPU pulls in all the stats at once
        i=0
        gpu_data = []
        while i < pyamdgpuinfo.detect_gpus():
            gpu_data.append(pyamdgpuinfo.get_gpu(i))
            i = i+1

        memory_used_all = [item.query_vram_usage() for item in gpu_data]
        memory_used = sum(memory_used_all) / len(memory_used_all)

        memory_total_all = [item.memory_info["vram_size"] for item in gpu_data]
        memory_total = sum(memory_total_all) / len(memory_total_all)

        memory_percentage = (memory_used / memory_total) * 100

        load_all = [item.query_load() for item in gpu_data]
        load = (sum(load_all) / len(load_all)) * 100

        temperature_all = [item.query_temperature() for item in gpu_data]
        temperature = sum(temperature_all) / len(temperature_all)

        if THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("SHOW", False):
            # print(f"GPU Load: {load}")
            lcd.DisplayProgressBar(
                ser=config.lcd_comm,
                x=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("HEIGHT", 0),
                value=int(load),
                min_value=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_IMAGE", None))
            )

        if THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("SHOW", False):
            # print(f"GPU Load: {load}")
            lcd.DisplayProgressBar(
                ser=config.lcd_comm,
                x=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("HEIGHT", 0),
                value=int(memory_percentage),
                min_value=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['GPU']['PERCENTAGE']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['MEMORY']['GRAPH'].get("BACKGROUND_IMAGE", None))
            )

        if THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("SHOW", False):
            lcd.DisplayText(
                ser=config.lcd_comm,
                text=f"{str(int(temperature))}* c",
                x=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("X", 0),
                y=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("Y", 0),
                font=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT", "roboto/Roboto-Regular.ttf"),
                font_size=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT_SIZE", 10),
                font_color=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("FONT_COLOR", (0, 0, 0)),
                background_color=THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['GPU']['TEMPERATURE']['TEXT'].get("BACKGROUND_IMAGE", None))
            )
    @staticmethod
    def is_available():
        return pyamdgpuinfo.detect_gpus() > 0


class Memory:
    @staticmethod
    def stats():
        swap_percent = psutil.swap_memory().percent

        if THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("SHOW", False):
            lcd.DisplayProgressBar(
                ser=config.lcd_comm,
                x=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("HEIGHT", 0),
                value=int(swap_percent),
                min_value=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['MEMORY']['SWAP']['GRAPH'].get("BACKGROUND_IMAGE", None))
            )

        virtual_percent = psutil.virtual_memory().percent

        if THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("SHOW", False):
            lcd.DisplayProgressBar(
                ser=config.lcd_comm,
                x=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("HEIGHT", 0),
                value=int(virtual_percent),
                min_value=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['MEMORY']['VIRTUAL']['GRAPH'].get("BACKGROUND_IMAGE", None))
            )

class Disk:
    @staticmethod
    def stats():
        percent = psutil.disk_usage("/").percent

        if THEME_DATA['STATS']['DISK']['GRAPH'].get("SHOW", False):
            lcd.DisplayProgressBar(
                ser=config.lcd_comm,
                x=THEME_DATA['STATS']['DISK']['GRAPH'].get("X", 0),
                y=THEME_DATA['STATS']['DISK']['GRAPH'].get("Y", 0),
                width=THEME_DATA['STATS']['DISK']['GRAPH'].get("WIDTH", 0),
                height=THEME_DATA['STATS']['DISK']['GRAPH'].get("HEIGHT", 0),
                value=int(percent),
                min_value=THEME_DATA['STATS']['DISK']['GRAPH'].get("MIN_VALUE", 0),
                max_value=THEME_DATA['STATS']['DISK']['GRAPH'].get("MAX_VALUE", 100),
                bar_color=THEME_DATA['STATS']['DISK']['GRAPH'].get("BAR_COLOR", (0, 0, 0)),
                bar_outline=THEME_DATA['STATS']['DISK']['GRAPH'].get("BAR_OUTLINE", False),
                background_color=THEME_DATA['STATS']['DISK']['GRAPH'].get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=get_full_path(THEME_DATA['PATH'],
                                               THEME_DATA['STATS']['DISK']['GRAPH'].get("BACKGROUND_IMAGE", None))
            )
