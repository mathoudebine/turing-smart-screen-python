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

// C++ port of library/lcd/serialize.py

#include "library/lcd/serialize.h"

#include <algorithm>

std::vector<Bytes> chunked(const Bytes &data, size_t chunk_size)
{
    std::vector<Bytes> chunks;
    for (size_t i = 0; i < data.size(); i += chunk_size) {
        chunks.emplace_back(data.begin() + i, data.begin() + std::min(i + chunk_size, data.size()));
    }
    return chunks;
}

Bytes image_to_RGB565(const Image &image, const std::string &endianness)
{
    const bool big = endianness == "big";
    const size_t count = static_cast<size_t>(image.width()) * image.height();
    const uint8_t *rgb = image.data();
    Bytes result(count * 2);
    for (size_t i = 0; i < count; i++) {
        // construct RGB565
        const uint16_t r = rgb[i * 3] >> 3, g = rgb[i * 3 + 1] >> 2, b = rgb[i * 3 + 2] >> 3;
        const uint16_t rgb565 = static_cast<uint16_t>((r << 11) | (g << 5) | b);
        // serialize to the correct endianness
        result[i * 2] = static_cast<uint8_t>(big ? rgb565 >> 8 : rgb565 & 0xFF);
        result[i * 2 + 1] = static_cast<uint8_t>(big ? rgb565 & 0xFF : rgb565 >> 8);
    }
    return result;
}

std::pair<Bytes, int> image_to_BGR(const Image &image)
{
    const size_t count = static_cast<size_t>(image.width()) * image.height();
    const uint8_t *rgb = image.data();
    Bytes bgr(count * 3);
    for (size_t i = 0; i < count; i++) {
        bgr[i * 3] = rgb[i * 3 + 2];
        bgr[i * 3 + 1] = rgb[i * 3 + 1];
        bgr[i * 3 + 2] = rgb[i * 3];
    }
    return {bgr, 3};
}

std::pair<Bytes, int> image_to_BGRA(const Image &image)
{
    const size_t count = static_cast<size_t>(image.width()) * image.height();
    const uint8_t *rgb = image.data();
    Bytes bgra(count * 4);
    for (size_t i = 0; i < count; i++) {
        bgra[i * 4] = rgb[i * 3 + 2];
        bgra[i * 4 + 1] = rgb[i * 3 + 1];
        bgra[i * 4 + 2] = rgb[i * 3];
        bgra[i * 4 + 3] = 255;
    }
    return {bgra, 4};
}

std::pair<Bytes, int> image_to_compressed_BGRA(const Image &image)
{
    const size_t count = static_cast<size_t>(image.width()) * image.height();
    const uint8_t *rgb = image.data();
    Bytes compressed_bgra(count * 3);
    constexpr uint8_t a = 255 >> 4;  // images are opaque
    for (size_t i = 0; i < count; i++) {
        compressed_bgra[i * 3] = static_cast<uint8_t>((rgb[i * 3 + 2] & 0xFC) | (a >> 2));
        compressed_bgra[i * 3 + 1] = static_cast<uint8_t>((rgb[i * 3 + 1] & 0xFC) | (a & 2));
        compressed_bgra[i * 3 + 2] = rgb[i * 3];
    }
    return {compressed_bgra, 3};
}
