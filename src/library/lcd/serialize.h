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

// C++ port of library/lcd/serialize.py: conversion of images to the pixel formats of the screens

#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "library/lcd/image.h"

using Bytes = std::vector<uint8_t>;

// Split data in chunks of chunk_size bytes (the last one can be smaller)
std::vector<Bytes> chunked(const Bytes &data, size_t chunk_size);

// RGB565 pixels, endianness: "big" or "little"
Bytes image_to_RGB565(const Image &image, const std::string &endianness);

// BGR pixels (3 bytes per pixel). Returns (data, pixel size)
std::pair<Bytes, int> image_to_BGR(const Image &image);

// BGRA pixels (4 bytes per pixel, opaque). Returns (data, pixel size)
std::pair<Bytes, int> image_to_BGRA(const Image &image);

// Compressed BGRA pixels: [6-bit B + 2-bit A, 6-bit G + 2-bit A, 8-bit R] (opaque). Returns (data, pixel size)
std::pair<Bytes, int> image_to_compressed_BGRA(const Image &image);
