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

// C++ port of tests/library/lcd/serial_mock.py and tests/library/lcd/sample_image.py

#include "serial_mock.h"

#include <fstream>
#include <stdexcept>

void MockSerial::write(const std::vector<uint8_t> &data)
{
    static const char *hex = "0123456789abcdef";
    std::string line = "write ";
    line.reserve(6 + data.size() * 2 + 1);
    for (uint8_t b: data) {
        line.push_back(hex[b >> 4]);
        line.push_back(hex[b & 0xF]);
    }
    line.push_back('\n');
    calls += line;
}

std::vector<uint8_t> MockSerial::read(size_t size)
{
    calls += "read " + std::to_string(size) + "\n";
    return {};
}

SerialMockScope::SerialMockScope()
{
    LcdComm::serial_factory = [this] {
        auto serial = std::make_unique<MockSerial>();
        last = serial.get();
        return serial;
    };
}

SerialMockScope::~SerialMockScope()
{
    LcdComm::serial_factory = nullptr;
}

Image generate_sample_image(int width, int height)
{
    Image img(width, height);
    for (int x = 0; x < width; x++) {
        for (int y = 0; y < height; y++) {
            // Calculate interpolation weights based on position
            const double wx = static_cast<double>(x) / (width - 1);  // Horizontal weight (0 to 1)
            const double wy = static_cast<double>(y) / (height - 1);  // Vertical weight (0 to 1)

            // Linear interpolation for each color channel
            const auto r = static_cast<uint8_t>((1 - wx) * (1 - wy) * 255);  // Top-left (Red)
            const auto g = static_cast<uint8_t>(wx * (1 - wy) * 255);  // Top-right (Green)
            const auto b = static_cast<uint8_t>(wy * (1 - wx) * 255);  // Bottom-left (Blue)

            img.putpixel(x, y, {r, g, b});
        }
    }
    return img;
}

std::string read_golden(const std::string &name)
{
    std::ifstream file(std::string(GOLDEN_DIR) + name + ".txt");
    if (!file) {
        throw std::runtime_error("Cannot open golden file " + name);
    }
    std::string result, line;
    while (std::getline(file, line)) {
        if (line.find_first_not_of(" \t\r") != std::string::npos) {
            result += line + "\n";
        }
    }
    return result;
}

uint64_t fnv1a(const std::string &text)
{
    uint64_t hash = 0xcbf29ce484222325ULL;
    for (unsigned char c: text) {
        hash ^= c;
        hash *= 0x100000001b3ULL;
    }
    return hash;
}
