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

// C++ port of library/lcd/lcd_comm_rev_a.py
// This class is for Turing Smart Screen (rev. A) 3.5" and UsbMonitor screens (all sizes)

#pragma once

#include "library/lcd/lcd_comm.h"

namespace rev_a {

enum Command : uint8_t
{
    RESET = 101,  // Resets the display
    CLEAR = 102,  // Clears the display to a white screen
    TO_BLACK = 103,  // Makes the screen go black. NOT TESTED
    SCREEN_OFF = 108,  // Turns the screen off
    SCREEN_ON = 109,  // Turns the screen on
    SET_BRIGHTNESS = 110,  // Sets the screen brightness
    SET_ORIENTATION = 121,  // Sets the screen orientation
    DISPLAY_BITMAP = 197,  // Displays an image on the screen

    // Commands below are only supported by next generation Turing Smart screens
    LCD_28 = 40,  // ?
    LCD_29 = 41,  // ?
    HELLO = 69,  // Asks the screen for its model: 3.5", 5" or 7"
    SET_MIRROR = 122,  // Mirrors the rendering on the screen
    DISPLAY_PIXELS = 195,  // Displays a list of pixels than can be non-contiguous in one command, useful for line charts
};

enum class SubRevision
{
    TURING_3_5,  // Official Turing 3.5 do not answer to HELLO command
    USBMONITOR_3_5,  // Answers 01 01 01 01 01 01 to HELLO
    USBMONITOR_5,  // Answers 02 02 02 02 02 02 to HELLO
    USBMONITOR_7,  // Answers 03 03 03 03 03 03 to HELLO
};

}  // namespace rev_a

class LcdCommRevA : public LcdComm
{
public:
    LcdCommRevA(const std::string &com_port = "AUTO", int display_width = 320, int display_height = 480,
                UpdateQueue *update_queue = nullptr);
    ~LcdCommRevA() override;

    std::optional<std::string> auto_detect_com_port() override;

    void SendCommand(rev_a::Command cmd, int x, int y, int ex, int ey, bool bypass_queue = false);

    void InitializeComm() override;
    void Reset() override;
    void Clear() override;
    void ScreenOff() override;
    void ScreenOn() override;
    void SetBrightness(int level = 25) override;
    void SetOrientation(Orientation orientation = Orientation::PORTRAIT) override;
    void DisplayPILImage(const Image &image, int x = 0, int y = 0, int image_width = 0, int image_height = 0) override;

    rev_a::SubRevision sub_revision = rev_a::SubRevision::TURING_3_5;

private:
    void _hello();
};
