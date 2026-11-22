// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
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

// Unit tests of library/sensors (C++ port of library/sensors/*.py)

#include <cmath>

#include <gtest/gtest.h>

#include "library/sensors/sensors_custom.h"
#include "library/sensors/sensors_python.h"
#include "library/sensors/sensors_stub_random.h"
#include "library/sensors/sensors_stub_static.h"

TEST(SensorsStubStatic, Values)
{
    auto s = sensors_stub_static::create();
    EXPECT_EQ(s.cpu->percentage(std::nullopt), 50.0);
    EXPECT_EQ(s.cpu->frequency(), 2400.0);
    EXPECT_EQ(s.gpu->stats().memory_used_mb, 16384.0);
    EXPECT_EQ(s.memory->virtual_used(), 32000000000);
    EXPECT_EQ(s.disk->disk_free(), 500000000000);
    EXPECT_EQ(s.net->stats("eth0", 1).uploaded, 1061000000);
}

TEST(SensorsStubRandom, Ranges)
{
    auto s = sensors_stub_random::create();
    for (int i = 0; i < 100; i++) {
        const double percentage = s.cpu->percentage(std::nullopt);
        EXPECT_GE(percentage, 0);
        EXPECT_LE(percentage, 100);
        const int fps = s.gpu->fps();
        EXPECT_GE(fps, 20);
        EXPECT_LE(fps, 120);
    }
}

TEST(SensorsPython, LinuxValues)
{
    auto s = sensors_python::create();

    s.cpu->percentage(std::nullopt);
    const double percentage = s.cpu->percentage(0.1);
    EXPECT_GE(percentage, 0);
    EXPECT_LE(percentage, 100);
    EXPECT_FALSE(std::isnan(s.cpu->load()[0]));

    EXPECT_GT(s.memory->virtual_used(), 0);
    EXPECT_GT(s.memory->virtual_free(), 0);
    const double memory_percent = s.memory->virtual_percent();
    EXPECT_GT(memory_percent, 0);
    EXPECT_LT(memory_percent, 100);

    EXPECT_GT(s.disk->disk_used(), 0);
    EXPECT_GE(s.disk->disk_usage_percent(), 0);

    // Loopback interface: rates are computed from the second call
    const auto first = s.net->stats("lo", 1.0);
    EXPECT_EQ(first.uploaded, 0);
    const auto second = s.net->stats("lo", 1.0);
    EXPECT_GE(second.uploaded, 0);
    EXPECT_GE(second.upload_rate, 0);
    // Unknown interface: zeros
    EXPECT_EQ(s.net->stats("does-not-exist", 1.0).uploaded, 0);
}

TEST(SensorsPython, CpuFanDetection)
{
    EXPECT_TRUE(sensors_python::is_cpu_fan("CPU Fan"));
    EXPECT_TRUE(sensors_python::is_cpu_fan("processor"));
    EXPECT_FALSE(sensors_python::is_cpu_fan("fan2"));
}

TEST(SensorsCustom, Examples)
{
    auto &sources = sensors_custom::custom_data_sources();
    auto &numeric = sources.at("ExampleCustomNumericData");
    EXPECT_EQ(numeric->as_numeric(), 75.845);
    EXPECT_EQ(numeric->as_string(), " 75.8%");
    const auto last_values = numeric->last_values();
    ASSERT_TRUE(last_values.has_value());
    EXPECT_EQ(last_values->size(), 10u);
    EXPECT_EQ(last_values->back(), 75.845);

    auto &text = sources.at("ExampleCustomTextOnlyData");
    EXPECT_FALSE(text->as_numeric().has_value());
    EXPECT_TRUE(text->as_string().has_value());
    EXPECT_FALSE(text->last_values().has_value());
}
