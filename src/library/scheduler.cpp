// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
//
// Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
// Copyright (C) 2022 Rollbacke
// Copyright (C) 2022 Ebag333
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// C++ port of library/scheduler.py

#include "library/scheduler.h"

#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <exception>
#include <mutex>
#include <thread>

#include <pthread.h>

#include "library/config.h"
#include "library/log.h"
#include "library/stats.h"

namespace scheduler {

std::atomic<bool> STOPPING = false;

namespace {

// Used to wake up the sleeping jobs when the program stops
std::mutex stop_mutex;
std::condition_variable stop_condition;

void set_thread_name(const std::string &threadname)
{
    // Linux thread names are limited to 15 characters
    pthread_setname_np(pthread_self(), threadname.substr(0, 15).c_str());
}

// Interval (seconds) of a stats item in the theme: STATS/<key>/INTERVAL, or STATS/<key>/<subkey>/INTERVAL
double theme_interval(const std::string &key, const std::string &subkey = "")
{
    const YAML::Node &theme = config::THEME_DATA;
    const YAML::Node node = subkey.empty() ? theme["STATS"][key] : theme["STATS"][key][subkey];
    return config::get(node, "INTERVAL", 0.0);
}

}  // namespace

void schedule(const std::string &threadname, double interval_s, std::function<void()> func)
{
    if (interval_s == 0) {
        return;
    }

    std::thread([threadname, interval_s, func = std::move(func)] {
        set_thread_name(threadname);
        const auto interval = std::chrono::duration_cast<std::chrono::steady_clock::duration>(
            std::chrono::duration<double>(interval_s));
        auto next_run = std::chrono::steady_clock::now();
        while (!STOPPING) {
            // The next execution is scheduled before running the job, so the period does not depend on the job duration
            next_run += interval;
            try {
                func();
            } catch (const std::exception &e) {
                logger.error("Error in {}: {}", threadname, e.what());
            }

            // If the job took longer than its interval, it is executed again right now
            const auto now = std::chrono::steady_clock::now();
            if (next_run < now) {
                next_run = now;
            }
            std::unique_lock lock(stop_mutex);
            stop_condition.wait_until(lock, next_run, [] { return STOPPING.load(); });
        }
    }).detach();
}

void stop()
{
    {
        std::lock_guard lock(stop_mutex);
        STOPPING = true;
    }
    stop_condition.notify_all();
}

void CPUPercentage()
{
    // Refresh the CPU Percentage
    schedule("CPU_Percentage", theme_interval("CPU", "PERCENTAGE"), stats::CPU::percentage);
}

void CPUFrequency()
{
    // Refresh the CPU Frequency
    schedule("CPU_Frequency", theme_interval("CPU", "FREQUENCY"), stats::CPU::frequency);
}

void CPULoad()
{
    // Refresh the CPU Load
    schedule("CPU_Load", theme_interval("CPU", "LOAD"), stats::CPU::load);
}

void CPUTemperature()
{
    // Refresh the CPU Temperature
    schedule("CPU_Temperature", theme_interval("CPU", "TEMPERATURE"), stats::CPU::temperature);
}

void CPUFanSpeed()
{
    // Refresh the CPU Fan Speed
    schedule("CPU_FanSpeed", theme_interval("CPU", "FAN_SPEED"), stats::CPU::fan_speed);
}

void GpuStats()
{
    // Refresh the GPU Stats
    schedule("GPU_Stats", theme_interval("GPU"), stats::Gpu::stats);
}

void MemoryStats()
{
    schedule("Memory_Stats", theme_interval("MEMORY"), stats::Memory::stats);
}

void DiskStats()
{
    schedule("Disk_Stats", theme_interval("DISK"), stats::Disk::stats);
}

void NetStats()
{
    schedule("Net_Stats", theme_interval("NET"), stats::Net::stats);
}

void DateStats()
{
    schedule("Date_Stats", theme_interval("DATE"), stats::Date::stats);
}

void SystemUptimeStats()
{
    schedule("SystemUptime_Stats", theme_interval("UPTIME"), stats::SystemUptime::stats);
}

void CustomStats()
{
    schedule("Custom_Stats", theme_interval("CUSTOM"), stats::Custom::stats);
}

void WeatherStats()
{
    // Weather data is refreshed at most every 5 minutes
    schedule("Weather_Stats", std::max(300.0, theme_interval("WEATHER")), stats::Weather::stats);
}

void PingStats()
{
    schedule("Ping_Stats", theme_interval("PING"), stats::Ping::stats);
}

void QueueHandler()
{
    std::thread([] {
        set_thread_name("Queue_Handler");
        auto execute = [](const UpdateQueue::Request &request) {
            if (!request) {
                return;
            }
            try {
                request();
            } catch (const std::exception &e) {
                logger.error("Error sending data to the display: {}", e.what());
            }
        };

        while (true) {
            if (STOPPING) {
                // Empty the action queue to allow program to exit cleanly
                while (const auto request = config::update_queue.get(std::chrono::milliseconds(0))) {
                    execute(*request);
                }
                break;
            }
            // Execute first action in the queue
            if (const auto request = config::update_queue.get(std::chrono::milliseconds(100))) {
                execute(*request);
            }
        }
    }).detach();
}

bool is_queue_empty()
{
    return config::update_queue.empty();
}

}  // namespace scheduler
