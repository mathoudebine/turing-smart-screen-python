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

// C++ port of library/sensors/sensors_python.py (HW_SENSORS: PYTHON, or AUTO)
// The Python version uses Python libraries (psutil, GPUtil, pyamdgpuinfo): this version reads the same information
// directly from Linux: /proc, /sys (hwmon, drm), statvfs, and the NVIDIA NVML library (loaded at runtime if present).

#pragma once

#include <map>
#include <mutex>
#include <string>
#include <vector>

#include "library/sensors/sensors.h"

namespace sensors_python {

struct FanInfo
{
    std::string label;
    int current;  // RPM
    int percent;
};

// Hardware fans info (for CPU and other peripherals): hwmon sensor name -> fans, in sysfs order.
// Inspired of psutil sensors_fans(), adapted to also get fan speed percentage instead of raw value.
std::vector<std::pair<std::string, std::vector<FanInfo>>> sensors_fans();

bool is_cpu_fan(const std::string &label);

enum class GpuType { UNSUPPORTED, AMD, NVIDIA };

class Cpu : public sensors::Cpu
{
public:
    double percentage(std::optional<double> interval) override;
    double frequency() override;
    std::array<double, 3> load() override;
    double temperature() override;
    double fan_percent(const std::optional<std::string> &fan_name = std::nullopt) override;

private:
    std::mutex mutex;
    bool has_last_times = false;
    double last_total = 0, last_busy = 0;
};

class GpuNvidia : public sensors::Gpu
{
public:
    Stats stats() override;
    int fps() override;
    double fan_percent() override;
    double frequency() override;
    bool is_available() override;
};

class GpuAmd : public sensors::Gpu
{
public:
    Stats stats() override;
    int fps() override;
    double fan_percent() override;
    double frequency() override;
    bool is_available() override;
};

class Gpu : public sensors::Gpu
{
public:
    Stats stats() override;
    int fps() override;
    double fan_percent() override;
    double frequency() override;
    // Detects the GPU: must be called once before the other functions
    bool is_available() override;

private:
    GpuType detected_gpu = GpuType::UNSUPPORTED;
    GpuNvidia nvidia;
    GpuAmd amd;
};

class Memory : public sensors::Memory
{
public:
    double swap_percent() override;
    double virtual_percent() override;
    int64_t virtual_used() override;
    int64_t virtual_free() override;
};

class Disk : public sensors::Disk
{
public:
    double disk_usage_percent() override;
    int64_t disk_used() override;
    int64_t disk_free() override;
};

class Net : public sensors::Net
{
public:
    Stats stats(const std::string &if_name, std::optional<double> interval) override;

private:
    struct Counters
    {
        int64_t bytes_sent;
        int64_t bytes_recv;
    };

    std::mutex mutex;
    std::map<std::string, Counters> pnic_before;
};

sensors::Sensors create();

}  // namespace sensors_python
