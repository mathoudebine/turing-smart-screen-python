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

#include "library/lcd/color.h"

#include <algorithm>
#include <cctype>
#include <charconv>
#include <cmath>
#include <map>
#include <stdexcept>
#include <vector>

#include <yaml-cpp/yaml.h>

namespace {

std::string trim(const std::string &s)
{
    const auto begin = s.find_first_not_of(" \t\r\n");
    if (begin == std::string::npos) {
        return "";
    }
    const auto end = s.find_last_not_of(" \t\r\n");
    return s.substr(begin, end - begin + 1);
}

std::string lower(std::string s)
{
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
    return s;
}

std::vector<std::string> split(const std::string &s, char sep)
{
    std::vector<std::string> parts;
    std::string::size_type start = 0, pos;
    while ((pos = s.find(sep, start)) != std::string::npos) {
        parts.push_back(s.substr(start, pos - start));
        start = pos + 1;
    }
    parts.push_back(s.substr(start));
    return parts;
}

// Strict integer parsing: the whole (trimmed) string must be an integer
bool to_int(const std::string &s, int &value)
{
    const std::string t = trim(s);
    if (t.empty()) {
        return false;
    }
    const char *begin = t.data();
    if (*begin == '+') {
        begin++;
    }
    const auto [ptr, ec] = std::from_chars(begin, t.data() + t.size(), value);
    return ec == std::errc() && ptr == t.data() + t.size();
}

bool to_double(const std::string &s, double &value)
{
    const std::string t = trim(s);
    if (t.empty()) {
        return false;
    }
    const auto [ptr, ec] = std::from_chars(t.data(), t.data() + t.size(), value);
    return ec == std::errc() && ptr == t.data() + t.size();
}

uint8_t clamp_channel(double v)
{
    return static_cast<uint8_t>(std::clamp(v, 0.0, 255.0));
}

// Parse "r, g, b" style arguments of rgb()/hsl()/hsv() functions, with optional '%' suffix
bool parse_function_args(const std::string &args, std::vector<double> &values, std::vector<bool> &percent)
{
    for (const auto &part: split(args, ',')) {
        std::string p = trim(part);
        bool is_percent = !p.empty() && p.back() == '%';
        if (is_percent) {
            p.pop_back();
        }
        double v;
        if (!to_double(p, v)) {
            return false;
        }
        values.push_back(v);
        percent.push_back(is_percent);
    }
    return true;
}

RGBColor hsl_to_rgb(double h, double s, double l)
{
    // Same algorithm as Python colorsys.hls_to_rgb, used by PIL
    auto v = [](double m1, double m2, double hue) {
        hue = std::fmod(hue, 1.0);
        if (hue < 0) hue += 1.0;
        if (hue < 1.0 / 6.0) return m1 + (m2 - m1) * hue * 6.0;
        if (hue < 0.5) return m2;
        if (hue < 2.0 / 3.0) return m1 + (m2 - m1) * (2.0 / 3.0 - hue) * 6.0;
        return m1;
    };
    double r, g, b;
    if (s == 0.0) {
        r = g = b = l;
    } else {
        const double m2 = l <= 0.5 ? l * (1.0 + s) : l + s - l * s;
        const double m1 = 2.0 * l - m2;
        r = v(m1, m2, h + 1.0 / 3.0);
        g = v(m1, m2, h);
        b = v(m1, m2, h - 1.0 / 3.0);
    }
    return {clamp_channel(r * 255.0 + 0.5), clamp_channel(g * 255.0 + 0.5), clamp_channel(b * 255.0 + 0.5)};
}

RGBColor hsv_to_rgb(double h, double s, double v)
{
    // Same algorithm as Python colorsys.hsv_to_rgb, used by PIL
    double r, g, b;
    if (s == 0.0) {
        r = g = b = v;
    } else {
        h = std::fmod(h, 1.0);
        if (h < 0) h += 1.0;
        const int i = static_cast<int>(h * 6.0);
        const double f = h * 6.0 - i;
        const double p = v * (1.0 - s), q = v * (1.0 - s * f), t = v * (1.0 - s * (1.0 - f));
        switch (i % 6) {
            case 0: r = v; g = t; b = p; break;
            case 1: r = q; g = v; b = p; break;
            case 2: r = p; g = v; b = t; break;
            case 3: r = p; g = q; b = v; break;
            case 4: r = t; g = p; b = v; break;
            default: r = v; g = p; b = q; break;
        }
    }
    return {clamp_channel(r * 255.0 + 0.5), clamp_channel(g * 255.0 + 0.5), clamp_channel(b * 255.0 + 0.5)};
}

const std::map<std::string, uint32_t> &color_names()
{
    // CSS color names, as supported by PIL ImageColor
    static const std::map<std::string, uint32_t> names = {
        {"aliceblue", 0xf0f8ff}, {"antiquewhite", 0xfaebd7}, {"aqua", 0x00ffff}, {"aquamarine", 0x7fffd4},
        {"azure", 0xf0ffff}, {"beige", 0xf5f5dc}, {"bisque", 0xffe4c4}, {"black", 0x000000},
        {"blanchedalmond", 0xffebcd}, {"blue", 0x0000ff}, {"blueviolet", 0x8a2be2}, {"brown", 0xa52a2a},
        {"burlywood", 0xdeb887}, {"cadetblue", 0x5f9ea0}, {"chartreuse", 0x7fff00}, {"chocolate", 0xd2691e},
        {"coral", 0xff7f50}, {"cornflowerblue", 0x6495ed}, {"cornsilk", 0xfff8dc}, {"crimson", 0xdc143c},
        {"cyan", 0x00ffff}, {"darkblue", 0x00008b}, {"darkcyan", 0x008b8b}, {"darkgoldenrod", 0xb8860b},
        {"darkgray", 0xa9a9a9}, {"darkgrey", 0xa9a9a9}, {"darkgreen", 0x006400}, {"darkkhaki", 0xbdb76b},
        {"darkmagenta", 0x8b008b}, {"darkolivegreen", 0x556b2f}, {"darkorange", 0xff8c00},
        {"darkorchid", 0x9932cc}, {"darkred", 0x8b0000}, {"darksalmon", 0xe9967a}, {"darkseagreen", 0x8fbc8f},
        {"darkslateblue", 0x483d8b}, {"darkslategray", 0x2f4f4f}, {"darkslategrey", 0x2f4f4f},
        {"darkturquoise", 0x00ced1}, {"darkviolet", 0x9400d3}, {"deeppink", 0xff1493},
        {"deepskyblue", 0x00bfff}, {"dimgray", 0x696969}, {"dimgrey", 0x696969}, {"dodgerblue", 0x1e90ff},
        {"firebrick", 0xb22222}, {"floralwhite", 0xfffaf0}, {"forestgreen", 0x228b22}, {"fuchsia", 0xff00ff},
        {"gainsboro", 0xdcdcdc}, {"ghostwhite", 0xf8f8ff}, {"gold", 0xffd700}, {"goldenrod", 0xdaa520},
        {"gray", 0x808080}, {"grey", 0x808080}, {"green", 0x008000}, {"greenyellow", 0xadff2f},
        {"honeydew", 0xf0fff0}, {"hotpink", 0xff69b4}, {"indianred", 0xcd5c5c}, {"indigo", 0x4b0082},
        {"ivory", 0xfffff0}, {"khaki", 0xf0e68c}, {"lavender", 0xe6e6fa}, {"lavenderblush", 0xfff0f5},
        {"lawngreen", 0x7cfc00}, {"lemonchiffon", 0xfffacd}, {"lightblue", 0xadd8e6}, {"lightcoral", 0xf08080},
        {"lightcyan", 0xe0ffff}, {"lightgoldenrodyellow", 0xfafad2}, {"lightgreen", 0x90ee90},
        {"lightgray", 0xd3d3d3}, {"lightgrey", 0xd3d3d3}, {"lightpink", 0xffb6c1}, {"lightsalmon", 0xffa07a},
        {"lightseagreen", 0x20b2aa}, {"lightskyblue", 0x87cefa}, {"lightslategray", 0x778899},
        {"lightslategrey", 0x778899}, {"lightsteelblue", 0xb0c4de}, {"lightyellow", 0xffffe0},
        {"lime", 0x00ff00}, {"limegreen", 0x32cd32}, {"linen", 0xfaf0e6}, {"magenta", 0xff00ff},
        {"maroon", 0x800000}, {"mediumaquamarine", 0x66cdaa}, {"mediumblue", 0x0000cd},
        {"mediumorchid", 0xba55d3}, {"mediumpurple", 0x9370db}, {"mediumseagreen", 0x3cb371},
        {"mediumslateblue", 0x7b68ee}, {"mediumspringgreen", 0x00fa9a}, {"mediumturquoise", 0x48d1cc},
        {"mediumvioletred", 0xc71585}, {"midnightblue", 0x191970}, {"mintcream", 0xf5fffa},
        {"mistyrose", 0xffe4e1}, {"moccasin", 0xffe4b5}, {"navajowhite", 0xffdead}, {"navy", 0x000080},
        {"oldlace", 0xfdf5e6}, {"olive", 0x808000}, {"olivedrab", 0x6b8e23}, {"orange", 0xffa500},
        {"orangered", 0xff4500}, {"orchid", 0xda70d6}, {"palegoldenrod", 0xeee8aa}, {"palegreen", 0x98fb98},
        {"paleturquoise", 0xafeeee}, {"palevioletred", 0xdb7093}, {"papayawhip", 0xffefd5},
        {"peachpuff", 0xffdab9}, {"peru", 0xcd853f}, {"pink", 0xffc0cb}, {"plum", 0xdda0dd},
        {"powderblue", 0xb0e0e6}, {"purple", 0x800080}, {"rebeccapurple", 0x663399}, {"red", 0xff0000},
        {"rosybrown", 0xbc8f8f}, {"royalblue", 0x4169e1}, {"saddlebrown", 0x8b4513}, {"salmon", 0xfa8072},
        {"sandybrown", 0xf4a460}, {"seagreen", 0x2e8b57}, {"seashell", 0xfff5ee}, {"sienna", 0xa0522d},
        {"silver", 0xc0c0c0}, {"skyblue", 0x87ceeb}, {"slateblue", 0x6a5acd}, {"slategray", 0x708090},
        {"slategrey", 0x708090}, {"snow", 0xfffafa}, {"springgreen", 0x00ff7f}, {"steelblue", 0x4682b4},
        {"tan", 0xd2b48c}, {"teal", 0x008080}, {"thistle", 0xd8bfd8}, {"tomato", 0xff6347},
        {"turquoise", 0x40e0d0}, {"violet", 0xee82ee}, {"wheat", 0xf5deb3}, {"white", 0xffffff},
        {"whitesmoke", 0xf5f5f5}, {"yellow", 0xffff00}, {"yellowgreen", 0x9acd32},
    };
    return names;
}

// Fallback: the color formats supported by PIL ImageColor.getrgb()
RGBColor pil_getrgb(const std::string &input)
{
    const std::string color = lower(trim(input));

    if (const auto it = color_names().find(color); it != color_names().end()) {
        return {uint8_t(it->second >> 16), uint8_t(it->second >> 8), uint8_t(it->second)};
    }

    if (!color.empty() && color[0] == '#') {
        const std::string hex = color.substr(1);
        if (!std::all_of(hex.begin(), hex.end(), [](unsigned char c) { return std::isxdigit(c); })) {
            throw std::invalid_argument("unknown color specifier: '" + input + "'");
        }
        auto h = [&](size_t pos, size_t len) { return static_cast<uint8_t>(std::stoi(hex.substr(pos, len), nullptr, 16)); };
        if (hex.size() == 3 || hex.size() == 4) {
            // #rgb or #rgba: each digit is duplicated
            return {uint8_t(h(0, 1) * 17), uint8_t(h(1, 1) * 17), uint8_t(h(2, 1) * 17)};
        }
        if (hex.size() == 6 || hex.size() == 8) {
            return {h(0, 2), h(2, 2), h(4, 2)};
        }
        throw std::invalid_argument("unknown color specifier: '" + input + "'");
    }

    const auto open = color.find('(');
    if (open != std::string::npos && color.back() == ')') {
        const std::string func = trim(color.substr(0, open));
        std::vector<double> v;
        std::vector<bool> pct;
        if (parse_function_args(color.substr(open + 1, color.size() - open - 2), v, pct)) {
            if ((func == "rgb" && v.size() == 3) || (func == "rgba" && v.size() == 4)) {
                auto channel = [&](size_t i) { return clamp_channel(pct[i] ? v[i] * 255.0 / 100.0 + 0.5 : v[i]); };
                return {channel(0), channel(1), channel(2)};
            }
            if (func == "hsl" && v.size() == 3) {
                return hsl_to_rgb(v[0] / 360.0, v[1] / 100.0, v[2] / 100.0);
            }
            if ((func == "hsv" || func == "hsb") && v.size() == 3) {
                return hsv_to_rgb(v[0] / 360.0, v[1] / 100.0, v[2] / 100.0);
            }
        }
    }

    throw std::invalid_argument("unknown color specifier: '" + input + "'");
}

}  // namespace

RGBColor parse_color(const std::string &color)
{
    // Try to parse it as our custom "r, g, b" format
    const auto rgb = split(color, ',');
    if (rgb.size() == 3) {
        int r, g, b;
        if (to_int(rgb[0], r) && to_int(rgb[1], g) && to_int(rgb[2], b)) {
            return {uint8_t(r), uint8_t(g), uint8_t(b)};
        }
        // at least one element can't be converted to int, we continue to try parsing as a PIL color
    }

    // fallback as a PIL color
    return pil_getrgb(color);
}

RGBColor parse_color(const YAML::Node &color)
{
    // even if undocumented, let's be nice and accept a list in lieu of a tuple
    if (color.IsSequence()) {
        if (color.size() != 3) {
            throw std::invalid_argument("RGB color must have 3 values");
        }
        return {uint8_t(color[0].as<int>()), uint8_t(color[1].as<int>()), uint8_t(color[2].as<int>())};
    }

    if (!color.IsScalar()) {
        throw std::invalid_argument("Color must be either an RGB tuple or a string");
    }

    return parse_color(color.as<std::string>());
}
