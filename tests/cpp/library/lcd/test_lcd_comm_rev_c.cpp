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

// C++ port of tests/library/lcd/test_lcd_comm_rev_c.py: data sent to the screen compared with the Python driver
//
// The rev. C golden files of the Python tests are outdated (recorded with an older protocol: the Python tests fail).
// The expected data here is the output of the current Python driver (480x800 screen, ROM version 87, image counter
// 0), stored as FNV-1a 64-bit hashes of the recorded calls to avoid adding big files to the repository.

#include <functional>
#include <map>
#include <memory>

#include <gtest/gtest.h>

#include "library/lcd/lcd_comm_rev_c.h"
#include "serial_mock.h"

namespace {

struct Expected
{
    uint64_t hash;
    size_t size;
};

const std::map<std::string, Expected> EXPECTED = {
    {"set_brightness", {0xcc3e9c5dc7aeb54dULL, 507}},
    {"display_pil_image_portrait", {0x2fddf832821e1a52ULL, 3087062}},
    {"display_pil_image_patch_portrait", {0x09c8df1bbc0496f3ULL, 123038}},
    {"display_pil_image_landscape", {0x71e5193a6cacfed6ULL, 3087062}},
    {"display_pil_image_patch_landscape", {0xdf6df55b79d5c046ULL, 124038}},
    {"display_pil_image_reverse_portrait", {0x661da709c70baa1eULL, 3087062}},
    {"display_pil_image_patch_reverse_portrait", {0x9a1e6cba27545819ULL, 123038}},
    {"display_pil_image_reverse_landscape", {0xd368d13bbc54fc72ULL, 3087062}},
    {"display_pil_image_patch_reverse_landscape", {0xd91a55cfe09029a3ULL, 124038}},
};

// 2.1" screen (480x480), ROM version 87
const std::map<std::string, Expected> EXPECTED_2INCH = {
    {"display_pil_image_portrait", {0xd3759c40c43b1049ULL, 1853562}},
    {"display_pil_image_patch_portrait", {0xc72fb7ed885ee151ULL, 123038}},
    {"display_pil_image_landscape", {0x0ed39d887959bfcdULL, 1853562}},
    {"display_pil_image_patch_landscape", {0x4e245d783760d30bULL, 124038}},
    {"display_pil_image_reverse_portrait", {0x7d735b14a6dda4f1ULL, 1853562}},
    {"display_pil_image_patch_reverse_portrait", {0x2c3da3d6d39ef63fULL, 123038}},
    {"display_pil_image_reverse_landscape", {0xb99c7957bdd618bdULL, 1853562}},
    {"display_pil_image_patch_reverse_landscape", {0x21f7de9b20543fa5ULL, 124038}},
};

// 8.8" screen (480x1920), ROM version 90 (BGRA pixels for partial updates)
const std::map<std::string, Expected> EXPECTED_8INCH = {
    {"display_pil_image_portrait", {0x11ec6dc716e5fa8cULL, 7405062}},
    {"display_pil_image_patch_portrait", {0x4ce5298aa1cf562bULL, 164538}},
    {"display_pil_image_landscape", {0xfa0e17d863e87818ULL, 7405062}},
    {"display_pil_image_patch_landscape", {0xb68fad00416d32c6ULL, 163538}},
    {"display_pil_image_reverse_portrait", {0xa00d4368ec268684ULL, 7405062}},
    {"display_pil_image_patch_reverse_portrait", {0x7fb2b092041b95ebULL, 164538}},
    {"display_pil_image_reverse_landscape", {0xc0412be736e02268ULL, 7405062}},
    {"display_pil_image_patch_reverse_landscape", {0xa2e49aa5989d91a1ULL, 163538}},
};

std::function<std::unique_ptr<LcdCommRevC>()> create(int width, int height, int rom_version)
{
    return [=] {
        auto lcd = std::make_unique<LcdCommRevC>("AUTO", width, height);
        lcd->rom_version = rom_version;
        return lcd;
    };
}

}  // namespace

class TestLcdCommRevC : public ::testing::TestWithParam<std::string>
{
};

TEST_P(TestLcdCommRevC, MatchesPythonDriver)
{
    const std::string calls = run_case<LcdCommRevC>(GetParam(), 480, 800);
    const Expected &expected = EXPECTED.at(GetParam());
    ASSERT_EQ(calls.size(), expected.size);
    EXPECT_EQ(fnv1a(calls), expected.hash) << "Data sent to the screen differs from the Python driver";
}

INSTANTIATE_TEST_SUITE_P(Python, TestLcdCommRevC, ::testing::ValuesIn(TEST_CASES));

class TestLcdCommRevCSizes : public ::testing::TestWithParam<std::string>
{
};

TEST_P(TestLcdCommRevCSizes, Screen2Inch)
{
    const std::string calls = run_case<LcdCommRevC>(GetParam(), 480, 480, {}, create(480, 480, 87));
    const Expected &expected = EXPECTED_2INCH.at(GetParam());
    ASSERT_EQ(calls.size(), expected.size);
    EXPECT_EQ(fnv1a(calls), expected.hash) << "Data sent to the screen differs from the Python driver";
}

TEST_P(TestLcdCommRevCSizes, Screen8Inch)
{
    const std::string calls = run_case<LcdCommRevC>(GetParam(), 480, 1920, {}, create(480, 1920, 90));
    const Expected &expected = EXPECTED_8INCH.at(GetParam());
    ASSERT_EQ(calls.size(), expected.size);
    EXPECT_EQ(fnv1a(calls), expected.hash) << "Data sent to the screen differs from the Python driver";
}

INSTANTIATE_TEST_SUITE_P(Python, TestLcdCommRevCSizes,
                         ::testing::ValuesIn(std::vector<std::string>(TEST_CASES.begin() + 1, TEST_CASES.end())));

// The requests going through the update queue (as in the system monitor) send the same data, reads included
TEST(TestLcdCommRevCQueue, QueuedRequestsMatchPythonDriver)
{
    SerialMockScope mock;
    UpdateQueue queue;
    LcdCommRevC lcd("AUTO", 480, 800, &queue);
    LcdCommRevC::count_start = 0;
    lcd.SetOrientation(Orientation::PORTRAIT);
    lcd.DisplayPILImage(generate_sample_image(480, 800), 10, 20, 100, 200);
    while (const auto request = queue.get(std::chrono::milliseconds(0))) {
        (*request)();
    }
    const Expected &expected = EXPECTED.at("display_pil_image_patch_portrait");
    ASSERT_EQ(mock.last->calls.size(), expected.size);
    EXPECT_EQ(fnv1a(mock.last->calls), expected.hash);
}
