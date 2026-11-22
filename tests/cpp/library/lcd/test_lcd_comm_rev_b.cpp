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

// C++ port of tests/library/lcd/test_lcd_comm_rev_b.py: data sent to the screen compared with the golden files

#include <gtest/gtest.h>

#include "library/lcd/lcd_comm_rev_b.h"
#include "serial_mock.h"

class TestLcdCommRevB : public ::testing::TestWithParam<std::string>
{
};

TEST_P(TestLcdCommRevB, Golden)
{
    const std::string calls = run_case<LcdCommRevB>(GetParam(), 320, 480);
    const std::string expected = read_golden("rev_b_" + GetParam());
    // Compare sizes first: the full data is too big to be printed on failure
    ASSERT_EQ(calls.size(), expected.size());
    EXPECT_TRUE(calls == expected) << "Data sent to the screen differs from golden file";
}

INSTANTIATE_TEST_SUITE_P(Python, TestLcdCommRevB, ::testing::ValuesIn(TEST_CASES));
