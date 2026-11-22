# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022 Rollbacke
# Copyright (C) 2022 Ebag333
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

import queue
import sched
import threading
import time
from datetime import timedelta
from functools import wraps

import library.config as config
import library.stats as stats

STOPPING = False


def async_job(threadname=None):
    """ wrapper to handle asynchronous threads """

    def decorator(func):
        """ Decorator to extend async_func """

        @wraps(func)
        def async_func(*args, **kwargs):
            """ create an asynchronous function to wrap around our thread """
            func_hl = threading.Thread(target=func, name=threadname, args=args, kwargs=kwargs)
            func_hl.start()
            return func_hl

        return async_func

    return decorator


def schedule(interval):
    """ wrapper to schedule asynchronous threads """

    def decorator(func):
        """ Decorator to extend periodic """

        def periodic(scheduler, periodic_interval, action, actionargs=()):
            """ Wrap the scheduler with our periodic interval """
            if not STOPPING:
                # If the program is not stopping: re-schedule the task for future execution
                scheduler.enter(periodic_interval, 1, periodic,
                                (scheduler, periodic_interval, action, actionargs))
            action(*actionargs)

        @wraps(func)
        def wrap(
                *args,
                **kwargs
        ):
            """ Wrapper to create our schedule and run it at the appropriate time """
            if interval == 0:
                return
            scheduler = sched.scheduler(time.time, time.sleep)
            periodic(scheduler, interval, func)
            scheduler.run()

        return wrap

    return decorator


@async_job("CPU_Percentage")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", 0)).total_seconds())
def CPUPercentage():
    """ Refresh the CPU Percentage """
    # logger.debug("Refresh CPU Percentage")
    stats.CPU.percentage()


@async_job("CPU_Frequency")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['FREQUENCY'].get("INTERVAL", 0)).total_seconds())
def CPUFrequency():
    """ Refresh the CPU Frequency """
    # logger.debug("Refresh CPU Frequency")
    stats.CPU.frequency()


@async_job("CPU_Load")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['LOAD'].get("INTERVAL", 0)).total_seconds())
def CPULoad():
    """ Refresh the CPU Load """
    # logger.debug("Refresh CPU Load")
    stats.CPU.load()


@async_job("CPU_Load")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['TEMPERATURE'].get("INTERVAL", 0)).total_seconds())
def CPUTemperature():
    """ Refresh the CPU Temperature """
    # logger.debug("Refresh CPU Temperature")
    stats.CPU.temperature()


@async_job("CPU_FanSpeed")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['FAN_SPEED'].get("INTERVAL", 0)).total_seconds())
def CPUFanSpeed():
    """ Refresh the CPU Fan Speed """
    # logger.debug("Refresh CPU Fan Speed")
    stats.CPU.fan_speed()


@async_job("GPU_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('GPU', {}).get("INTERVAL", 0)).total_seconds())
def GpuStats():
    """ Refresh the GPU Stats """
    # logger.debug("Refresh GPU Stats")
    stats.Gpu.stats()


@async_job("Memory_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('MEMORY', {}).get("INTERVAL", 0)).total_seconds())
def MemoryStats():
    # logger.debug("Refresh memory stats")
    stats.Memory.stats()


@async_job("Disk_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('DISK', {}).get("INTERVAL", 0)).total_seconds())
def DiskStats():
    # logger.debug("Refresh disk stats")
    stats.Disk.stats()


@async_job("Net_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('NET', {}).get("INTERVAL", 0)).total_seconds())
def NetStats():
    # logger.debug("Refresh net stats")
    stats.Net.stats()


@async_job("Date_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('DATE', {}).get("INTERVAL", 0)).total_seconds())
def DateStats():
    # logger.debug("Refresh date stats")
    stats.Date.stats()


@async_job("SystemUptime_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('UPTIME', {}).get("INTERVAL", 0)).total_seconds())
def SystemUptimeStats():
    # logger.debug("Refresh system uptime stats")
    stats.SystemUptime.stats()


@async_job("Custom_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('CUSTOM', {}).get("INTERVAL", 0)).total_seconds())
def CustomStats():
    # print("Refresh custom stats")
    stats.Custom.stats()


@async_job("Weather_Stats")
@schedule(timedelta(seconds=max(300.0, config.THEME_DATA['STATS'].get('WEATHER', {}).get("INTERVAL", 0))).total_seconds())
def WeatherStats():
    # logger.debug("Refresh Weather data")
    stats.Weather.stats()


@async_job("Ping_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('PING', {}).get("INTERVAL", 0)).total_seconds())
def PingStats():
    # logger.debug("Refresh Ping data")
    stats.Ping.stats()


def _group_transmission_units(items):
    # Group freshly drained queue items into transmission units: consecutive items sharing a non-None
    # tu_id form one unit (all lines of one rendered image); everything else is its own unit.
    units = []
    for item in items:
        region_key = item[2] if len(item) > 2 else None
        tu_id = item[3] if len(item) > 3 else None
        if tu_id is not None and units and units[-1][1] == tu_id:
            units[-1][2].append(item)
        else:
            units.append([region_key, tu_id, [item]])
    return units


def _process_update_queue(block: bool):
    # Send pending requests to the display. Instead of a pure FIFO, everything queued since the last
    # call is drained at once and coalesced: if several frames of the same screen region piled up
    # (producer faster than the device), only the newest one is transmitted, so the displayed data
    # never lags further behind than the device current frame instead of accumulating stale snapshots.
    update_queue = config.update_queue

    drained = []
    if block:
        # Park the writer thread until the next request comes in
        drained.append(update_queue.get())
    while True:
        try:
            drained.append(update_queue.get_nowait())
        except queue.Empty:
            break
    if not drained:
        return

    driver = getattr(config, "display_driver", None)
    dedup_cache = getattr(driver, "_last_sent_payload", None)

    units = _group_transmission_units(drained)
    # Keep only the newest frame per region, but at the position where that region first appeared:
    # superseded frames are dropped and different regions never get reordered relative to each other
    scheduled = []
    region_position = {}
    for unit in units:
        region_key = unit[0]
        if region_key is None:
            scheduled.append(unit)
        elif region_key in region_position:
            scheduled[region_position[region_key]] = unit
        else:
            region_position[region_key] = len(scheduled)
            scheduled.append(unit)

    for region_key, _, unit_items in scheduled:
        payload = None
        if region_key is not None and dedup_cache is not None:
            payload = b"".join(
                bytes(item[1][0]) for item in unit_items
                if len(item) > 1 and item[1] and isinstance(item[1][0], (bytes, bytearray)))
            if dedup_cache.get(region_key) == payload:
                # The device already shows exactly this content: no need to retransmit
                continue

        for item in unit_items:
            item[0](*item[1])

        if payload is not None:
            dedup_cache[region_key] = payload


@async_job("Queue_Handler")
@schedule(timedelta(milliseconds=1).total_seconds())
def QueueHandler():
    # Do next action waiting in the queue
    if STOPPING:
        # Empty the action queue to allow program to exit cleanly
        while not config.update_queue.empty():
            _process_update_queue(block=False)
    else:
        # Coalesce and execute everything waiting in the queue
        _process_update_queue(block=True)


def is_queue_empty() -> bool:
    return config.update_queue.empty()
