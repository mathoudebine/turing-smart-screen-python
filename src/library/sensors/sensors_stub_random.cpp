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

// C++ port of library/sensors/sensors_stub_random.py

#include "library/sensors/sensors_stub_random.h"

#include <mutex>
#include <random>

namespace sensors_stub_random {

namespace {

// Random generator shared by all sensors (called from several threads), with a fixed seed like Python
std::mutex random_mutex;
std::mt19937_64 generator(10);

double uniform(double a, double b)
{
    std::lock_guard lock(random_mutex);
    return std::uniform_real_distribution<double>(a, b)(generator);
}

int64_t randint(int64_t a, int64_t b)
{
    std::lock_guard lock(random_mutex);
    return std::uniform_int_distribution<int64_t>(a, b)(generator);
}

}  // namespace

double Cpu::percentage(std::optional<double>) { return uniform(0, 100); }

double Cpu::frequency() { return uniform(800, 3400); }

std::array<double, 3> Cpu::load() { return {uniform(0, 100), uniform(0, 100), uniform(0, 100)}; }

double Cpu::temperature() { return uniform(30, 90); }

double Cpu::fan_percent(const std::optional<std::string> &) { return uniform(0, 100); }

sensors::Gpu::Stats Gpu::stats()
{
    return {uniform(0, 100), uniform(0, 100), uniform(300, 16000), 16000.0, uniform(30, 90)};
}

int Gpu::fps() { return static_cast<int>(randint(20, 120)); }

double Gpu::fan_percent() { return uniform(0, 100); }

double Gpu::frequency() { return uniform(800, 3400); }

bool Gpu::is_available() { return true; }

double Memory::swap_percent() { return uniform(0, 100); }

double Memory::virtual_percent() { return uniform(0, 100); }

int64_t Memory::virtual_used() { return randint(300000000, 16000000000); }

int64_t Memory::virtual_free() { return randint(300000000, 16000000000); }

double Disk::disk_usage_percent() { return uniform(0, 100); }

int64_t Disk::disk_used() { return randint(1000000000, 2000000000000); }

int64_t Disk::disk_free() { return randint(1000000000, 2000000000000); }

sensors::Net::Stats Net::stats(const std::string &, std::optional<double>)
{
    return {static_cast<double>(randint(1000000, 999000000)), randint(1000000, 999000000),
            static_cast<double>(randint(1000000, 999000000)), randint(1000000, 999000000)};
}

sensors::Sensors create()
{
    return {std::make_unique<Cpu>(), std::make_unique<Gpu>(), std::make_unique<Memory>(), std::make_unique<Disk>(),
            std::make_unique<Net>()};
}

}  // namespace sensors_stub_random
