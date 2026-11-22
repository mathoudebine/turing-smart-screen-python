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

// C++ port of library/display.py: creates the LCD driver selected by REVISION in config.yaml, and displays the
// static images and texts of the theme.

#pragma once

#include <memory>
#include <utility>

#include "library/lcd/lcd_comm.h"

class Display
{
public:
    // Exits the program if the display revision is unknown
    Display();

    void initialize_display();
    void turn_on();
    void turn_off();
    void display_static_images();
    void display_static_text();

    std::unique_ptr<LcdComm> lcd;
};

// Theme orientation, from the theme DISPLAY_ORIENTATION and config.yaml DISPLAY_REVERSE
Orientation get_theme_orientation();

// Display (width, height) in portrait orientation, from the theme DISPLAY_SIZE
std::pair<int, int> get_theme_size();

// The display, created on first use (config::init() must have been called before)
Display &display();
