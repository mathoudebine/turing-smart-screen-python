// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
//
// Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
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

// C++ port of library/lcd/color.py
//
// A color can be given as an RGB triplet, or as a string in any of these formats:
// - "r, g, b" (e.g. "255, 0, 0"), as is found in the themes' yaml settings
// - the formats supported by PIL (https://pillow.readthedocs.io/en/stable/reference/ImageColor.html):
//   "#rgb", "#rgba", "#rrggbb", "#rrggbbaa", "rgb(r, g, b)", "rgb(r%, g%, b%)", "rgba(...)",
//   "hsl(h, s%, l%)", "hsv(h, s%, v%)" / "hsb(...)", and the CSS color names (e.g. "red")
//
// For example, here are multiple ways to write the pure red color:
// - {255, 0, 0}
// - "255, 0, 0"
// - "#ff0000"
// - "red"
// - "hsl(0, 100%, 50%)"

#pragma once

#include <cstdint>
#include <string>

namespace YAML { class Node; }

struct RGBColor
{
    uint8_t r = 0;
    uint8_t g = 0;
    uint8_t b = 0;

    bool operator==(const RGBColor &) const = default;
};

// Throws std::invalid_argument if the color cannot be parsed
RGBColor parse_color(const std::string &color);

// Color from a theme/config YAML value: a "r, g, b" string (or any format above), or a [r, g, b] sequence
RGBColor parse_color(const YAML::Node &color);
