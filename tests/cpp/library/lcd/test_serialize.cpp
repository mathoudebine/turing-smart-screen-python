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

// Unit tests of library/lcd/serialize (C++ port of library/lcd/serialize.py) and of the image rotations

#include <gtest/gtest.h>

#include "library/lcd/serialize.h"

TEST(Serialize, Chunked)
{
    const auto chunks = chunked({1, 2, 3, 4, 5}, 2);
    ASSERT_EQ(chunks.size(), 3u);
    EXPECT_EQ(chunks[2], Bytes({5}));
}

TEST(Serialize, PixelFormats)
{
    Image image(2, 1);
    image.putpixel(0, 0, {255, 0, 0});
    image.putpixel(1, 0, {0x12, 0x34, 0x56});
    EXPECT_EQ(image_to_RGB565(image, "big"), Bytes({0xF8, 0x00, 0x11, 0xAA}));
    EXPECT_EQ(image_to_RGB565(image, "little"), Bytes({0x00, 0xF8, 0xAA, 0x11}));
    EXPECT_EQ(image_to_BGR(image).first, Bytes({0, 0, 255, 0x56, 0x34, 0x12}));
    EXPECT_EQ(image_to_BGRA(image).first, Bytes({0, 0, 255, 255, 0x56, 0x34, 0x12, 255}));
    EXPECT_EQ(image_to_BGRA(image).second, 4);
}

TEST(Image, Rotations)
{
    // 2x1 image: red, green
    Image image(2, 1);
    image.putpixel(0, 0, {255, 0, 0});
    image.putpixel(1, 0, {0, 255, 0});
    // 90 degrees counter-clockwise: green on top
    const Image r90 = image.rotate(90);
    EXPECT_EQ(r90.size(), std::make_pair(1, 2));
    EXPECT_EQ(r90.getpixel(0, 0), (RGBColor{0, 255, 0}));
    // 270 degrees counter-clockwise: red on top
    EXPECT_EQ(image.rotate(270).getpixel(0, 0), (RGBColor{255, 0, 0}));
    EXPECT_EQ(image.rotate(180).getpixel(0, 0), (RGBColor{0, 255, 0}));
    EXPECT_THROW(image.rotate(45), std::invalid_argument);
}
