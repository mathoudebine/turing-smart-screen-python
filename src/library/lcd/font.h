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

// TrueType font rendering with FreeType, replacing the subset of Pillow (PIL.ImageFont, ImageDraw.text/textbbox)
// used by the Python code. No Python counterpart: this file replaces a Python dependency.
//
// Text anchors follow Pillow (https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html), 2 characters:
// - horizontal: 'l' left, 'm' middle, 'r' right
// - vertical: 'a' ascender, 't' top, 'm' middle, 's' baseline, 'b' bottom, 'd' descender
// Only single-line text is supported (like the themes).

#pragma once

#include <mutex>
#include <string>
#include <vector>

#include "library/lcd/image.h"

struct TextBox
{
    double left;
    double top;
    double right;
    double bottom;
};

class Font
{
public:
    // Load a TrueType/OpenType font with the given size in pixels (like ImageFont.truetype(path, size)).
    // Throws std::runtime_error if the font cannot be loaded.
    Font(const std::string &path, int size);
    ~Font();

    Font(const Font &) = delete;
    Font &operator=(const Font &) = delete;

    // Bounding box of the text drawn at (x, y) with the given anchor (like ImageDraw.textbbox)
    TextBox textbbox(double x, double y, const std::string &text, const std::string &anchor = "la") const;

    // Bounding box of the text drawn at (0, 0) with the left-ascender anchor (like ImageFont.getbbox)
    TextBox getbbox(const std::string &text) const { return textbbox(0, 0, text, "la"); }

    // Draw the text at (x, y) with the given anchor (like ImageDraw.text)
    void draw(Image &image, double x, double y, const std::string &text, RGBColor fill,
              const std::string &anchor = "la") const;

private:
    struct GlyphPosition
    {
        unsigned int index;
        long pen_x;  // 26.6 fixed point
    };

    struct Layout
    {
        std::vector<GlyphPosition> glyphs;
        long advance = 0;  // total advance width, 26.6
        long ink_x_min = 0, ink_x_max = 0, ink_y_min = 0, ink_y_max = 0;  // ink extents, 26.6, y axis going up
        bool has_ink = false;
    };

    Layout layout(const std::string &text) const;

    // Anchor point coordinates relative to the text origin (left of the baseline), 26.6, y axis going up
    void anchor_offset(const Layout &layout, const std::string &anchor, long &x_anchor, long &y_anchor) const;

    void *face = nullptr;  // FT_Face
    mutable std::mutex mutex;
};
