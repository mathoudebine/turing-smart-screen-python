from typing import Tuple
import random

import library.sensors.sensors as sensors


class Cpu(sensors.Cpu):
    @staticmethod
    def percentage(interval: float) -> float:
        return random.uniform(0, 100)

    @staticmethod
    def frequency() -> float:
        return random.uniform(800, 3400)

    @staticmethod
    def load() -> Tuple[float, float, float]:  # 1 / 5 / 15min avg:
        return random.uniform(0, 100), random.uniform(0, 100), random.uniform(0, 100)

    @staticmethod
    def is_temperature_available() -> bool:
        return True

    @staticmethod
    def temperature() -> float:
        return random.uniform(30, 90)


class Gpu(sensors.Gpu):
    @staticmethod
    def stats() -> Tuple[float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / temp (°C)
        return random.uniform(0, 100), random.uniform(0, 100), random.uniform(300, 16000), random.uniform(30, 90)

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
    def virtual_used() -> int:
        return random.randint(300, 16000)

    @staticmethod
    def virtual_free() -> int:
        return random.randint(300, 16000)


class Disk(sensors.Disk):
    @staticmethod
    def disk_usage_percent() -> float:
        return random.uniform(0, 100)

    @staticmethod
    def disk_used() -> int:
        return random.randint(1000000000, 2000000000000)

    @staticmethod
    def disk_total() -> int:
        return random.randint(1000000000, 2000000000000)

    @staticmethod
    def disk_free() -> int:
        return random.randint(1000000000, 2000000000000)


class Net(sensors.Net):
    @staticmethod
    def stats(if_name, interval) -> Tuple[
        int, int, int, int]:  # dl rate (B/s), downloaded (B), up rate (B/s), uploaded (B)
        return random.randint(1000000, 999000000), random.randint(1000000, 999000000), random.randint(
            1000000, 999000000), random.randint(1000000, 999000000)
