// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
//
// Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
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

// C++ port of library/sensors/sensors.py
// This file defines all supported hardware in abstract classes and their abstract methods to access sensors.
// To be overridden by child sensors classes. Unsupported values are NaN (or -1 for integer values).

#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>

namespace sensors {

class Cpu
{
public:
    virtual ~Cpu() = default;

    // CPU usage (%). With an interval, the usage is measured during this time (blocking call), otherwise it is
    // measured since the previous call (0.0 is returned the first time)
    virtual double percentage(std::optional<double> interval) = 0;

    // Current frequency (MHz)
    virtual double frequency() = 0;

    // 1 / 5 / 15min load average
    virtual std::array<double, 3> load() = 0;

    // Temperature (°C)
    virtual double temperature() = 0;

    // Fan speed (%). fan_name: "<sensor name>/<fan label>" of a manually selected fan, auto-detection otherwise
    virtual double fan_percent(const std::optional<std::string> &fan_name = std::nullopt) = 0;
};

class Gpu
{
public:
    struct Stats
    {
        double load;               // %
        double memory_percentage;  // %
        double memory_used_mb;     // MB
        double memory_total_mb;    // MB
        double temperature;        // °C
    };

    virtual ~Gpu() = default;

    virtual Stats stats() = 0;

    // Frames per second, -1 if not supported
    virtual int fps() = 0;

    // Fan speed (%)
    virtual double fan_percent() = 0;

    // Current frequency (MHz)
    virtual double frequency() = 0;

    virtual bool is_available() = 0;
};

class Memory
{
public:
    virtual ~Memory() = default;

    virtual double swap_percent() = 0;
    virtual double virtual_percent() = 0;
    virtual int64_t virtual_used() = 0;  // In bytes
    virtual int64_t virtual_free() = 0;  // In bytes
};

class Disk
{
public:
    virtual ~Disk() = default;

    virtual double disk_usage_percent() = 0;
    virtual int64_t disk_used() = 0;  // In bytes
    virtual int64_t disk_free() = 0;  // In bytes
};

class Net
{
public:
    struct Stats
    {
        double upload_rate;    // B/s
        int64_t uploaded;      // B
        double download_rate;  // B/s
        int64_t downloaded;    // B
    };

    virtual ~Net() = default;

    // Network interface statistics. interval: time (s) since the previous call, to compute the rates
    virtual Stats stats(const std::string &if_name, std::optional<double> interval) = 0;
};

// A set of sensors (Python: a sensors module selected by HW_SENSORS in config.yaml)
struct Sensors
{
    std::unique_ptr<Cpu> cpu;
    std::unique_ptr<Gpu> gpu;
    std::unique_ptr<Memory> memory;
    std::unique_ptr<Disk> disk;
    std::unique_ptr<Net> net;
};

}  // namespace sensors
