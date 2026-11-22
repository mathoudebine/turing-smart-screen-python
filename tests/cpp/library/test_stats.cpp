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

// Unit tests of library/stats helpers (C++ port of library/stats.py)

#include <cmath>

#include <gtest/gtest.h>

#include "library/stats.h"

TEST(Stats, Bytes2Human)
{
    // Same results as psutil._common.bytes2human()
    EXPECT_EQ(stats::bytes2human(0), "0.0B");
    EXPECT_EQ(stats::bytes2human(1023), "1023.0B");
    EXPECT_EQ(stats::bytes2human(1024), "1.0K");
    EXPECT_EQ(stats::bytes2human(1061000000), "1011.8M");
    EXPECT_EQ(stats::bytes2human(1061000000, "{:.1f} ", "/s"), "1011.8 M/s");
    EXPECT_EQ(stats::bytes2human(5.5 * 1024 * 1024 * 1024 * 1024), "5.5T");
}

TEST(Stats, SaveLastValue)
{
    std::vector<double> values;
    stats::save_last_value(1, values, 3);
    ASSERT_EQ(values.size(), 3u);
    EXPECT_TRUE(std::isnan(values[0]));
    EXPECT_TRUE(std::isnan(values[1]));
    EXPECT_EQ(values[2], 1);
    stats::save_last_value(2, values, 3);
    stats::save_last_value(3, values, 3);
    stats::save_last_value(4, values, 3);
    EXPECT_EQ(values, (std::vector<double>{2, 3, 4}));
    // History size changed in theme: list is reset
    stats::save_last_value(5, values, 2);
    ASSERT_EQ(values.size(), 2u);
    EXPECT_EQ(values[1], 5);
}
