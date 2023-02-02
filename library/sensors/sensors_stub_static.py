# turing-smart-screen-python - a Python system monitor and library for 3.5" USB-C displays like Turing Smart Screen or XuanFang
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

# This file will use static data instead of real hardware sensors
# Used for screenshots and tests
# For all platforms (Linux, Windows, macOS)

from typing import Tuple

import library.sensors.sensors as sensors


class Cpu(sensors.Cpu):
    @staticmethod
    def percentage(interval: float) -> float:
        return 18.3

    @staticmethod
    def frequency() -> float:
        return 2400.0

    @staticmethod
    def load() -> Tuple[float, float, float]:  # 1 / 5 / 15min avg:
        return 25.0, 37.8, 75.6

    @staticmethod
    def is_temperature_available() -> bool:
        return True

    @staticmethod
    def temperature() -> float:
        return 68.9


class Gpu(sensors.Gpu):
    @staticmethod
    def stats() -> Tuple[float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / temp (°C)
        return 75.8, 22.7, 1480, 52.3

    @staticmethod
    def is_available() -> bool:
        return True


class Memory(sensors.Memory):
    @staticmethod
    def swap_percent() -> float:
        return 12.4

    @staticmethod
    def virtual_percent() -> float:
        return 37.0

    @staticmethod
    def virtual_used() -> int:  # In bytes
        return 5920000000

    @staticmethod
    def virtual_free() -> int:  # In bytes
        return 10080000000


class Disk(sensors.Disk):
    @staticmethod
    def disk_usage_percent() -> float:
        return 59.0

    @staticmethod
    def disk_used() -> int:  # In bytes
        return 1180000000000

    @staticmethod
    def disk_free() -> int:  # In bytes
        return 820000000000


class Net(sensors.Net):
    @staticmethod
    def stats(if_name, interval) -> Tuple[
        int, int, int, int]:  # up rate (B/s), uploaded (B), dl rate (B/s), downloaded (B)
        return 2000000, 4857000, 839000000, 5623000000
