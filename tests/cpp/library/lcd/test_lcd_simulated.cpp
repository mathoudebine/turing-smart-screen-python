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

// Unit tests of library/lcd/lcd_simulated and of the rendering functions of library/lcd/lcd_comm

#include <cmath>

#include <gtest/gtest.h>

#include "library/lcd/lcd_simulated.h"

namespace {
const RGBColor black{0, 0, 0}, white{255, 255, 255}, red{255, 0, 0};
const std::string FONT = "res/fonts/roboto-mono/RobotoMono-Regular.ttf";
}

TEST(LcdSimulated, OrientationAndSize)
{
    LcdSimulated lcd("AUTO", 320, 480);
    EXPECT_EQ(lcd.screen_image.size(), std::make_pair(320, 480));
    lcd.SetOrientation(Orientation::LANDSCAPE);
    EXPECT_EQ(lcd.get_width(), 480);
    EXPECT_EQ(lcd.get_height(), 320);
    EXPECT_EQ(lcd.screen_image.size(), std::make_pair(480, 320));
    EXPECT_EQ(Image::open(SCREENSHOT_FILE).size(), std::make_pair(480, 320));
}

TEST(LcdSimulated, ProgressBar)
{
    LcdSimulated lcd("AUTO", 320, 480);
    // 25..75 bar at value 50: half filled
    lcd.DisplayProgressBar({.x = 10, .y = 10, .width = 100, .height = 10, .min_value = 25, .max_value = 75,
                            .value = 50, .bar_color = red, .bar_outline = false, .background_color = black});
    EXPECT_EQ(lcd.screen_image.getpixel(10, 15), red);
    EXPECT_EQ(lcd.screen_image.getpixel(55, 15), red);
    EXPECT_EQ(lcd.screen_image.getpixel(65, 15), black);
    EXPECT_EQ(lcd.screen_image.getpixel(115, 15), white);  // outside of the bar: untouched
}

TEST(LcdSimulated, TextGhostingPrevention)
{
    LcdSimulated lcd("AUTO", 320, 480);
    TextOptions text{.text = "88888", .x = 10, .y = 10, .font = FONT, .font_size = 20, .font_color = white,
                     .background_color = black, .anchor = "lt"};
    lcd.DisplayText(text);
    text.text = "1";
    lcd.DisplayText(text);
    // The area of the previous longer text has been repainted with the background color
    for (int x = 40; x < 70; x++) {
        for (int y = 12; y < 22; y++) {
            ASSERT_EQ(lcd.screen_image.getpixel(x, y), black) << x << "," << y;
        }
    }
}

TEST(LcdSimulated, InvalidParameters)
{
    LcdSimulated lcd("AUTO", 320, 480);
    EXPECT_THROW(lcd.DisplayText({.text = "", .font = FONT}), std::invalid_argument);
    EXPECT_THROW(lcd.DisplayText({.text = "x", .x = 400, .font = FONT}), std::invalid_argument);
    EXPECT_THROW(lcd.DisplayProgressBar({.x = 300, .y = 0, .width = 50, .height = 10}), std::invalid_argument);
    EXPECT_THROW(lcd.DisplayRadialProgressBar({.xc = 10, .yc = 100, .radius = 50, .bar_width = 5}),
                 std::invalid_argument);
}

TEST(LcdSimulated, RadialAndLineGraph)
{
    LcdSimulated lcd("AUTO", 320, 480);
    lcd.DisplayRadialProgressBar({.xc = 100, .yc = 100, .radius = 50, .bar_width = 10, .angle_start = 0,
                                  .angle_end = 360, .angle_sep = 0, .value = 100, .with_text = false,
                                  .bar_color = red, .background_color = black});
    EXPECT_EQ(lcd.screen_image.getpixel(145, 100), red);  // 3 o'clock, inside the bar
    EXPECT_EQ(lcd.screen_image.getpixel(100, 100), black);  // center

    lcd.DisplayLineGraph({.x = 0, .y = 200, .width = 100, .height = 50, .values = {NAN, 50, 50, 50},
                          .line_color = red, .line_width = 1, .graph_axis = false, .background_color = black});
    EXPECT_EQ(lcd.screen_image.getpixel(10, 225), red);  // value 50: middle of the graph
}
