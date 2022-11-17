from abc import ABC, abstractmethod
from collections import namedtuple


class CPU(ABC):
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
    def load() -> tuple[float, float, float]:  # 1 / 5 / 15min avg
        pass

    @staticmethod
    @abstractmethod
    def is_temperature_available() -> bool:
        pass

    @staticmethod
    @abstractmethod
    def temperature() -> float:
        pass


class GPU(ABC):
    @staticmethod
    @abstractmethod
    def stats() -> tuple[float, float, float, float]:  # load (%) / used mem (%) / used mem (Mb) / temp (°C)
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
    def virtual_used() -> int:
        pass

    @staticmethod
    @abstractmethod
    def virtual_free() -> int:
        pass


class Disk(ABC):
    @staticmethod
    @abstractmethod
    def disk_usage_percent() -> float:
        pass

    @staticmethod
    @abstractmethod
    def disk_used() -> int:
        pass

    @staticmethod
    @abstractmethod
    def disk_total() -> int:
        pass

    @staticmethod
    @abstractmethod
    def disk_free() -> int:
        pass


class Net(ABC):
    @abstractmethod
    def stats(self) -> tuple[float, float, float, float]:  # dl rate (B/s), downloaded (B), up rate (B/s), uploaded (B)
        pass
