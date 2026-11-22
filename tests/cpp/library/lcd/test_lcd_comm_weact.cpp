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

// Tests of library/lcd/lcd_comm_weact_a and lcd_comm_weact_b: data sent to the screen compared with the Python
// drivers (no Python tests exist for them). The expected data is the output of the Python drivers for the same test
// cases as the rev. A-D tests (patch images cropped to the patch size), stored as FNV-1a 64-bit hashes.

#include <map>

#include <gtest/gtest.h>

#include "library/lcd/lcd_comm_weact_a.h"
#include "library/lcd/lcd_comm_weact_b.h"
#include "serial_mock.h"

namespace {

struct Expected
{
    uint64_t hash;
    size_t size;
};

const std::map<std::string, Expected> EXPECTED_A = {
    {"set_brightness", {0xc08ffdfbe6d5b41bULL, 17}},
    {"display_pil_image_portrait", {0xc2c04e7f5a3a112cULL, 616120}},
    {"display_pil_image_patch_portrait", {0x107d24d41877de5aULL, 80264}},
    {"display_pil_image_landscape", {0xbd090a858fa05619ULL, 615560}},
    {"display_pil_image_patch_landscape", {0x54e73974369defccULL, 80187}},
    {"display_pil_image_reverse_portrait", {0xf4cb7dc032fadd8bULL, 616120}},
    {"display_pil_image_patch_reverse_portrait", {0x6d5dba0221c7a235ULL, 80264}},
    {"display_pil_image_reverse_landscape", {0x875c38b8c0a0cd56ULL, 615560}},
    {"display_pil_image_patch_reverse_landscape", {0x214cc0d9c0d13ee5ULL, 80187}},
};

const std::map<std::string, Expected> EXPECTED_B = {
    {"set_brightness", {0xc08ffdfbe6d5b41bULL, 17}},
    {"display_pil_image_portrait", {0xac7b3e2b39cb1150ULL, 51800}},
    {"display_pil_image_patch_portrait", {0x7b80ef3b073fb67bULL, 7324}},
    {"display_pil_image_landscape", {0x4256e673c1d2d2c4ULL, 51520}},
    {"display_pil_image_patch_landscape", {0x84b51ef26e90e6caULL, 7282}},
    {"display_pil_image_reverse_portrait", {0x0d73156caa2618f7ULL, 51800}},
    {"display_pil_image_patch_reverse_portrait", {0xbff1507950030148ULL, 7324}},
    {"display_pil_image_reverse_landscape", {0xd0a33c1c3f4d1553ULL, 51520}},
    {"display_pil_image_patch_reverse_landscape", {0xa05b96cd8d26b8b1ULL, 7282}},
};

}  // namespace

class TestLcdCommWeAct : public ::testing::TestWithParam<std::string>
{
};

TEST_P(TestLcdCommWeAct, WeActA)
{
    const std::string calls = run_case<LcdCommWeActA>(GetParam(), 320, 480, {10, 20, 100, 200, true});
    const Expected &expected = EXPECTED_A.at(GetParam());
    ASSERT_EQ(calls.size(), expected.size);
    EXPECT_EQ(fnv1a(calls), expected.hash) << "Data sent to the screen differs from the Python driver";
}

TEST_P(TestLcdCommWeAct, WeActB)
{
    const std::string calls = run_case<LcdCommWeActB>(GetParam(), 80, 160, {5, 10, 30, 60, true});
    const Expected &expected = EXPECTED_B.at(GetParam());
    ASSERT_EQ(calls.size(), expected.size);
    EXPECT_EQ(fnv1a(calls), expected.hash) << "Data sent to the screen differs from the Python driver";
}

INSTANTIATE_TEST_SUITE_P(Python, TestLcdCommWeAct, ::testing::ValuesIn(TEST_CASES));
