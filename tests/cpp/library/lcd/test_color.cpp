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

// Unit tests of library/lcd/color (C++ port of library/lcd/color.py)

#include <gtest/gtest.h>
#include <yaml-cpp/yaml.h>

#include "library/lcd/color.h"

TEST(ParseColor, ThemeFormat)
{
    EXPECT_EQ(parse_color("255, 0, 0"), (RGBColor{255, 0, 0}));
    EXPECT_EQ(parse_color("12,34,56"), (RGBColor{12, 34, 56}));
}

TEST(ParseColor, PilFormats)
{
    const RGBColor red{255, 0, 0};
    EXPECT_EQ(parse_color("#ff0000"), red);
    EXPECT_EQ(parse_color("#F00"), red);
    EXPECT_EQ(parse_color("#ff000080"), red);
    EXPECT_EQ(parse_color("red"), red);
    EXPECT_EQ(parse_color("Red"), red);
    EXPECT_EQ(parse_color("rgb(255, 0, 0)"), red);
    EXPECT_EQ(parse_color("rgb(100%, 0%, 0%)"), red);
    EXPECT_EQ(parse_color("hsl(0, 100%, 50%)"), red);
    EXPECT_EQ(parse_color("hsv(0, 100%, 100%)"), red);
    EXPECT_EQ(parse_color("hsl(120, 100%, 25%)"), (RGBColor{0, 128, 0}));
}

TEST(ParseColor, Yaml)
{
    EXPECT_EQ(parse_color(YAML::Load("[1, 2, 3]")), (RGBColor{1, 2, 3}));
    EXPECT_EQ(parse_color(YAML::Load("\"10, 20, 30\"")), (RGBColor{10, 20, 30}));
    EXPECT_THROW(parse_color(YAML::Load("[1, 2]")), std::invalid_argument);
}

TEST(ParseColor, Invalid)
{
    EXPECT_THROW(parse_color("not a color"), std::invalid_argument);
    EXPECT_THROW(parse_color("#12345"), std::invalid_argument);
    EXPECT_THROW(parse_color("1, 2, x"), std::invalid_argument);
}
