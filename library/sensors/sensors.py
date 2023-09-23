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

# This file defines all supported hardware in virtual classes and their abstract methods to access sensors
# To be overriden by child sensors classes

from abc import ABC, abstractmethod
from typing import Tuple


class Cpu(ABC):
    @staticmethod
    @abstractmethod
    def percentage(interval: float) -> float:
        pass

    @staticmethod
    @abstractmethod
    def frequency() -> float:
        pass

    @staticmethod
    @abstractmethod
    def load() -> Tuple[float, float, float]:  # 1 / 5 / 15min avg (%)
        pass

    @staticmethod
    @abstractmethod
    def is_temperature_available() -> bool:
        pass

    @staticmethod
    @abstractmethod
    def temperature() -> float:
        pass


class Gpu(ABC):
    @staticmethod
    @abstractmethod
    def stats() -> Tuple[float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / temp (°C)
        pass

    @staticmethod
    @abstractmethod
    def fps() -> int:
        pass

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        pass


class Memory(ABC):
    @staticmethod
    @abstractmethod
    def swap_percent() -> float:
        pass

    @staticmethod
    @abstractmethod
    def virtual_percent() -> float:
        pass

    @staticmethod
    @abstractmethod
    def virtual_used() -> int:  # In bytes
        pass

    @staticmethod
    @abstractmethod
    def virtual_free() -> int:  # In bytes
        pass


class Disk(ABC):
    @staticmethod
    @abstractmethod
    def disk_usage_percent() -> float:
        pass

    @staticmethod
    @abstractmethod
    def disk_used() -> int:  # In bytes
        pass

    @staticmethod
    @abstractmethod
    def disk_free() -> int:  # In bytes
        pass


class Net(ABC):
    @staticmethod
    @abstractmethod
    def stats(if_name, interval) -> Tuple[
        int, int, int, int]:  # up rate (B/s), uploaded (B), dl rate (B/s), downloaded (B)
        pass
