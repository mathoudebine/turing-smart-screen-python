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

#include "library/sensors/sensors_stub_static.h"

namespace sensors_stub_static {

double Cpu::percentage(std::optional<double>) { return PERCENTAGE_SENSOR_VALUE; }

double Cpu::frequency() { return CPU_FREQ_MHZ; }

std::array<double, 3> Cpu::load()
{
    return {PERCENTAGE_SENSOR_VALUE, PERCENTAGE_SENSOR_VALUE, PERCENTAGE_SENSOR_VALUE};
}

double Cpu::temperature() { return TEMPERATURE_SENSOR_VALUE; }

double Cpu::fan_percent(const std::optional<std::string> &) { return PERCENTAGE_SENSOR_VALUE; }

sensors::Gpu::Stats Gpu::stats()
{
    return {PERCENTAGE_SENSOR_VALUE,
            PERCENTAGE_SENSOR_VALUE,
            GPU_MEM_TOTAL_SIZE_GB / 100.0 * PERCENTAGE_SENSOR_VALUE * 1024,
            GPU_MEM_TOTAL_SIZE_GB * 1024.0,
            TEMPERATURE_SENSOR_VALUE};
}

int Gpu::fps() { return GPU_FPS; }

double Gpu::fan_percent() { return PERCENTAGE_SENSOR_VALUE; }

double Gpu::frequency() { return GPU_FREQ_MHZ; }

bool Gpu::is_available() { return true; }

double Memory::swap_percent() { return PERCENTAGE_SENSOR_VALUE; }

double Memory::virtual_percent() { return PERCENTAGE_SENSOR_VALUE; }

int64_t Memory::virtual_used()
{
    return static_cast<int64_t>(MEMORY_TOTAL_SIZE_GB / 100.0 * PERCENTAGE_SENSOR_VALUE) * 1000000000;
}

int64_t Memory::virtual_free()
{
    return static_cast<int64_t>(MEMORY_TOTAL_SIZE_GB / 100.0 * (100 - PERCENTAGE_SENSOR_VALUE)) * 1000000000;
}

double Disk::disk_usage_percent() { return PERCENTAGE_SENSOR_VALUE; }

int64_t Disk::disk_used()
{
    return static_cast<int64_t>(DISK_TOTAL_SIZE_GB / 100.0 * PERCENTAGE_SENSOR_VALUE) * 1000000000;
}

int64_t Disk::disk_free()
{
    return static_cast<int64_t>(DISK_TOTAL_SIZE_GB / 100.0 * (100 - PERCENTAGE_SENSOR_VALUE)) * 1000000000;
}

sensors::Net::Stats Net::stats(const std::string &, std::optional<double>)
{
    return {NETWORK_SPEED_BYTES, NETWORK_SPEED_BYTES, NETWORK_SPEED_BYTES, NETWORK_SPEED_BYTES};
}

sensors::Sensors create()
{
    return {std::make_unique<Cpu>(), std::make_unique<Gpu>(), std::make_unique<Memory>(), std::make_unique<Disk>(),
            std::make_unique<Net>()};
}

}  // namespace sensors_stub_static
