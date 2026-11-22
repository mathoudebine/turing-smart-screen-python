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

// C++ port of tests/library/lcd/test_lcd_comm_rev_a.py: data sent to the screen compared with the golden files

#include <gtest/gtest.h>

#include "library/lcd/lcd_comm_rev_a.h"
#include "serial_mock.h"

class TestLcdCommRevA : public ::testing::TestWithParam<std::string>
{
};

TEST_P(TestLcdCommRevA, Golden)
{
    const std::string calls = run_case<LcdCommRevA>(GetParam(), 320, 480);
    const std::string expected = read_golden("rev_a_" + GetParam());
    // Compare sizes first: the full data is too big to be printed on failure
    ASSERT_EQ(calls.size(), expected.size());
    EXPECT_TRUE(calls == expected) << "Data sent to the screen differs from golden file";
}

INSTANTIATE_TEST_SUITE_P(Python, TestLcdCommRevA, ::testing::ValuesIn(TEST_CASES));

// The requests going through the update queue (as in the system monitor) send the same data
TEST(TestLcdCommRevAQueue, QueuedRequestsMatchGolden)
{
    SerialMockScope mock;
    UpdateQueue queue;
    LcdCommRevA lcd("AUTO", 320, 480, &queue);
    lcd.SetOrientation(Orientation::LANDSCAPE);
    lcd.DisplayPILImage(generate_sample_image(480, 320), 10, 20, 100, 200);
    EXPECT_EQ(mock.last->calls.size(), 16u * 2 + 7);  // only the orientation (not queued) is sent for now
    while (const auto request = queue.get(std::chrono::milliseconds(0))) {
        (*request)();
    }
    const std::string expected = read_golden("rev_a_display_pil_image_patch_landscape");
    ASSERT_EQ(mock.last->calls.size(), expected.size());
    EXPECT_TRUE(mock.last->calls == expected);
}
