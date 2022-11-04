import sched
import threading
import time
from datetime import timedelta
from functools import wraps

import library.config as config
import library.stats as stats
from library.log import logger

THEME_DATA = config.THEME_DATA

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
            global STOPPING
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
            scheduler = sched.scheduler(time.time, time.sleep)
            periodic(scheduler, interval, func)
            scheduler.run()

        return wrap

    return decorator


@async_job("CPU_Percentage")
@schedule(timedelta(seconds=THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", None)).total_seconds())
def CPUPercentage():
    """ Refresh the CPU Percentage """
    # logger.debug("Refresh CPU Percentage")
    stats.CPU.percentage()


@async_job("CPU_Frequency")
@schedule(timedelta(seconds=THEME_DATA['STATS']['CPU']['FREQUENCY'].get("INTERVAL", None)).total_seconds())
def CPUFrequency():
    """ Refresh the CPU Frequency """
    # logger.debug("Refresh CPU Frequency")
    stats.CPU.frequency()


@async_job("CPU_Load")
@schedule(timedelta(seconds=THEME_DATA['STATS']['CPU']['LOAD'].get("INTERVAL", None)).total_seconds())
def CPULoad():
    """ Refresh the CPU Load """
    # logger.debug("Refresh CPU Load")
    stats.CPU.load()


@async_job("CPU_Load")
@schedule(timedelta(seconds=THEME_DATA['STATS']['CPU']['TEMPERATURE'].get("INTERVAL", None)).total_seconds())
def CPUTemperature():
    """ Refresh the CPU Temperature """
    # logger.debug("Refresh CPU Temperature")
    stats.CPU.temperature()


@async_job("GPU_Stats")
@schedule(timedelta(seconds=THEME_DATA['STATS']['GPU'].get("INTERVAL", None)).total_seconds())
def GpuNvidiaStats():
    """ Refresh the GPU Stats """
    # logger.debug("Refresh GPU Stats")
    stats.GpuNvidia.stats()


@async_job("GPU_Stats")
@schedule(timedelta(seconds=THEME_DATA['STATS']['GPU'].get("INTERVAL", None)).total_seconds())
def GpuAmdStats():
    """ Refresh the GPU Stats """
    # logger.debug("Refresh GPU Stats")
    stats.GpuAmd.stats()


@async_job("Memory_Stats")
@schedule(timedelta(seconds=THEME_DATA['STATS']['MEMORY'].get("INTERVAL", None)).total_seconds())
def MemoryStats():
    # logger.debug("Refresh memory stats")
    stats.Memory.stats()


@async_job("Disk_Stats")
@schedule(timedelta(seconds=THEME_DATA['STATS']['DISK'].get("INTERVAL", None)).total_seconds())
def DiskStats():
    # logger.debug("Refresh disk stats")
    stats.Disk.stats()


@async_job("Net_Stats")
@schedule(timedelta(seconds=THEME_DATA['STATS']['NET'].get("INTERVAL", None)).total_seconds())
def NetStats():
    # logger.debug("Refresh net stats")
    stats.Net.stats()


@async_job("Date_Stats")
@schedule(timedelta(seconds=THEME_DATA['STATS']['DATE'].get("INTERVAL", None)).total_seconds())
def DateStats():
    # logger.debug("Refresh date stats")
    stats.Date.stats()


@async_job("Queue_Handler")
@schedule(timedelta(milliseconds=1).total_seconds())
def QueueHandler():
    # Do next action waiting in the queue
    global STOPPING
    if STOPPING:
        # Empty the action queue to allow program to exit cleanly
        while not config.update_queue.empty():
            f, args = config.update_queue.get()
            f(*args)
    else:
        # Execute first action in the queue
        f, args = config.update_queue.get()
        if f:
            f(*args)


def is_queue_empty() -> bool:
    return config.update_queue.empty()
