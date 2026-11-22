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

// C++ port of library/sensors/sensors_stub_static.py
// This file will use static data instead of real hardware sensors. Useful for theme editor.

#pragma once

#include "library/sensors/sensors.h"

namespace sensors_stub_static {

// Define here global static values that will be applied to all sensors of the same type
constexpr double PERCENTAGE_SENSOR_VALUE = 50.0;
constexpr double TEMPERATURE_SENSOR_VALUE = 67.3;

// Define other sensors
constexpr double CPU_FREQ_MHZ = 2400.0;
constexpr int64_t DISK_TOTAL_SIZE_GB = 1000;
constexpr int64_t MEMORY_TOTAL_SIZE_GB = 64;
constexpr int64_t GPU_MEM_TOTAL_SIZE_GB = 32;
constexpr int64_t NETWORK_SPEED_BYTES = 1061000000;
constexpr int GPU_FPS = 120;
constexpr double GPU_FREQ_MHZ = 1500.0;

class Cpu : public sensors::Cpu
{
public:
    double percentage(std::optional<double> interval) override;
    double frequency() override;
    std::array<double, 3> load() override;
    double temperature() override;
    double fan_percent(const std::optional<std::string> &fan_name = std::nullopt) override;
};

class Gpu : public sensors::Gpu
{
public:
    Stats stats() override;
    int fps() override;
    double fan_percent() override;
    double frequency() override;
    bool is_available() override;
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
};

sensors::Sensors create();

}  // namespace sensors_stub_static
