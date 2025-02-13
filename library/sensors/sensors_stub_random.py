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

# This file will use randomly generated data instead of real hardware sensors
# For all platforms (Linux, Windows, macOS)

import random
from typing import Tuple

import library.sensors.sensors as sensors


class Cpu(sensors.Cpu):
    @staticmethod
    def percentage(interval: float) -> float:
        return random.uniform(0, 100)

    @staticmethod
    def frequency() -> float:
        return random.uniform(800, 3400)

    @staticmethod
    def load() -> Tuple[float, float, float]:  # 1 / 5 / 15min avg (%):
        return random.uniform(0, 100), random.uniform(0, 100), random.uniform(0, 100)

    @staticmethod
    def temperature() -> float:
        return random.uniform(30, 90)

    @staticmethod
    def fan_percent(fan_name: str = None) -> float:
        return random.uniform(0, 100)


class Gpu(sensors.Gpu):
    @staticmethod
    def stats() -> Tuple[
        float, float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / total mem (Mb) / temp (°C)
        return random.uniform(0, 100), random.uniform(0, 100), random.uniform(300, 16000), 16000.0, random.uniform(30,
                                                                                                                   90)

    @staticmethod
    def fps() -> int:
        return random.randint(20, 120)

    @staticmethod
    def fan_percent() -> float:
        return random.uniform(0, 100)

    @staticmethod
    def frequency() -> float:
        return random.uniform(800, 3400)

    @staticmethod
    def is_available() -> bool:
        return True


class Memory(sensors.Memory):
    @staticmethod
    def swap_percent() -> float:
        return random.uniform(0, 100)

    @staticmethod
    def virtual_percent() -> float:
        return random.uniform(0, 100)

    @staticmethod
    def virtual_used() -> int:  # In bytes
        return random.randint(300000000, 16000000000)

    @staticmethod
    def virtual_free() -> int:  # In bytes
        return random.randint(300000000, 16000000000)


class Disk(sensors.Disk):
    @staticmethod
    def disk_usage_percent() -> float:
        return random.uniform(0, 100)

    @staticmethod
    def disk_used() -> int:  # In bytes
        return random.randint(1000000000, 2000000000000)

    @staticmethod
    def disk_free() -> int:  # In bytes
        return random.randint(1000000000, 2000000000000)


class Net(sensors.Net):
    @staticmethod
    def stats(if_name, interval) -> Tuple[
        int, int, int, int]:  # up rate (B/s), uploaded (B), dl rate (B/s), downloaded (B)
        return random.randint(1000000, 999000000), random.randint(1000000, 999000000), random.randint(
            1000000, 999000000), random.randint(1000000, 999000000)
