// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
//
// Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
// Copyright (C) 2022 Rollbacke
// Copyright (C) 2022 Ebag333
// Copyright (C) 2022 w1ld3r
// Copyright (C) 2022 Charles Ferguson (gerph)
// Copyright (C) 2022 Russ Nelson (RussNelson)
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

// C++ port of main.py: the system monitor main program, displaying HW sensors on the screen using themes.
// Phase 1: the display is initialized and the static images/texts of the theme are displayed, the system monitoring
// itself is not implemented yet.

#include <exception>

#include "library/config.h"
#include "library/display.h"
#include "library/log.h"

int main()
{
    try {
        // Load config.yaml and the theme
        config::init();

        // Initialize the display
        logger.info("Initialize display");
        display().initialize_display();

        // Create all static images
        display().display_static_images();

        // Create all static texts
        display().display_static_text();

        logger.info("System monitoring is not implemented yet in the C++ version: program will now exit");
    } catch (const std::exception &e) {
        logger.error("{}", e.what());
        return 1;
    }
    return 0;
}
