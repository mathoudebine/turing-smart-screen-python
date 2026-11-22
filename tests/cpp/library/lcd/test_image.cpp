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

// Unit tests of library/lcd/image and library/lcd/font (replacement of Pillow)

#include <gtest/gtest.h>

#include "library/lcd/font.h"
#include "library/lcd/image.h"

namespace {
const RGBColor black{0, 0, 0}, white{255, 255, 255}, red{255, 0, 0};
const std::string FONT = "res/fonts/roboto-mono/RobotoMono-Regular.ttf";
}

TEST(Image, NewAndPixels)
{
    Image image(4, 3, red);
    EXPECT_EQ(image.size(), std::make_pair(4, 3));
    EXPECT_EQ(image.getpixel(3, 2), red);
    image.putpixel(1, 1, white);
    EXPECT_EQ(image.getpixel(1, 1), white);
    image.putpixel(10, 10, white);  // out of image: ignored
}

TEST(Image, CropOutsideIsBlack)
{
    const Image image(4, 4, white);
    const Image cropped = image.crop(2, 2, 6, 6);
    EXPECT_EQ(cropped.size(), std::make_pair(4, 4));
    EXPECT_EQ(cropped.getpixel(0, 0), white);
    EXPECT_EQ(cropped.getpixel(3, 3), black);
}

TEST(Image, Paste)
{
    Image image(4, 4, black);
    image.paste(Image(2, 2, red), 3, 3);  // partly out of image
    EXPECT_EQ(image.getpixel(3, 3), red);
    EXPECT_EQ(image.getpixel(2, 2), black);
}

TEST(Image, ResizeUniformColor)
{
    const Image image = Image(10, 6, red).resize(25, 3);
    EXPECT_EQ(image.size(), std::make_pair(25, 3));
    EXPECT_EQ(image.getpixel(0, 0), red);
    EXPECT_EQ(image.getpixel(24, 2), red);
}

TEST(Image, SaveAndOpenPng)
{
    Image image(5, 5, white);
    image.putpixel(2, 3, red);
    const std::string path = ::testing::TempDir() + "test_image.png";
    image.save(path);
    const Image loaded = Image::open(path);
    EXPECT_EQ(loaded.size(), std::make_pair(5, 5));
    EXPECT_EQ(loaded.getpixel(2, 3), red);
    EXPECT_EQ(loaded.getpixel(0, 0), white);
    EXPECT_THROW(Image::open(::testing::TempDir() + "does-not-exist.png"), std::runtime_error);
}

TEST(ImageDraw, RectangleCornersIncluded)
{
    Image image(10, 10, black);
    ImageDraw(image).rectangle(2, 2, 4, 4, red, std::nullopt);
    EXPECT_EQ(image.getpixel(2, 2), red);
    EXPECT_EQ(image.getpixel(4, 4), red);
    EXPECT_EQ(image.getpixel(5, 5), black);
}

TEST(ImageDraw, ArcStaysInBox)
{
    Image image(20, 20, black);
    ImageDraw(image).arc(0, 0, 19, 19, 0, 360, red, 3);
    EXPECT_EQ(image.getpixel(19, 10), red);  // 3 o'clock
    EXPECT_EQ(image.getpixel(10, 10), black);  // center
    Image half(20, 20, black);
    ImageDraw(half).arc(0, 0, 19, 19, 0, 180, red, 3);  // lower half (clockwise from 3 o'clock)
    EXPECT_EQ(half.getpixel(10, 19), red);
    EXPECT_EQ(half.getpixel(10, 0), black);
}

TEST(Font, AnchorsAndBoundingBox)
{
    const Font font(FONT, 20);
    const TextBox lt = font.textbbox(100, 50, "Hello", "lt");
    EXPECT_EQ(lt.left, 100);
    EXPECT_EQ(lt.top, 50);
    EXPECT_GT(lt.right, 140);
    EXPECT_GT(lt.bottom, 60);

    const TextBox rb = font.textbbox(100, 50, "Hello", "rb");
    EXPECT_EQ(rb.right, 100);
    EXPECT_EQ(rb.bottom, 50);

    const TextBox mm = font.textbbox(100, 50, "Hello", "mm");
    EXPECT_NEAR((mm.left + mm.right) / 2, 100, 1);

    EXPECT_THROW(font.textbbox(0, 0, "Hello", "xx"), std::invalid_argument);
    EXPECT_THROW(Font("does-not-exist.ttf", 10), std::runtime_error);
}

TEST(Font, DrawText)
{
    Image image(100, 40, black);
    const Font font(FONT, 20);
    font.draw(image, 10, 10, "Hi", white, "lt");
    bool drawn = false;
    for (int y = 0; y < 40; y++) {
        for (int x = 0; x < 100; x++) {
            drawn |= image.getpixel(x, y) != black;
        }
    }
    EXPECT_TRUE(drawn);
    EXPECT_EQ(image.getpixel(5, 5), black);
}
