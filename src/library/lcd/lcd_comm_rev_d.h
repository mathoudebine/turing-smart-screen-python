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

// C++ port of library/lcd/lcd_comm_rev_d.py
// This class is for Kipye Qiye Smart Display 3.5"

#pragma once

#include "library/lcd/lcd_comm.h"
#include "library/lcd/serialize.h"

namespace rev_d {

enum class Command
{
    GETINFO,      // 71 00 00 00
    SETORG,       // Set portrait orientation
    SET180,       // Set reverse portrait orientation
    SETHF,        // Set portrait orientation with horizontal mirroring
    SETVF,        // Set reverse portrait orientation with horizontal mirroring
    SETBL,        // Brightness setting
    DISPCOLOR,    // Display RGB565 color on whole screen
    BLOCKWRITE,   // Send bitmap size
    INTOPICMODE,  // Start bitmap transmission
    OUTPICMODE,   // End bitmap transmission
};

const Bytes &command_value(Command cmd);

}  // namespace rev_d

class LcdCommRevD : public LcdComm
{
public:
    LcdCommRevD(const std::string &com_port = "AUTO", int display_width = 320, int display_height = 480,
                UpdateQueue *update_queue = nullptr);
    ~LcdCommRevD() override;

    std::optional<std::string> auto_detect_com_port() override;

    // Empty the input buffer after each write: we don't process acknowledgements the screen sends back
    void WriteDataAndFlush(const Bytes &byteBuffer);

    void SendCommand(rev_d::Command cmd, const Bytes &payload = {}, bool bypass_queue = false);

    void InitializeComm() override;
    void Reset() override;
    void Clear() override;
    void ScreenOff() override;
    void ScreenOn() override;
    void SetBrightness(int level = 25) override;
    void SetOrientation(Orientation orientation = Orientation::PORTRAIT) override;
    void DisplayPILImage(const Image &image, int x = 0, int y = 0, int image_width = 0, int image_height = 0) override;
};
