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

// C++ port of library/lcd/lcd_comm_weact_a.py
// This class is for WeAct Studio Display FS V1 3.5"

#pragma once

#include <utility>

#include "library/lcd/lcd_comm.h"
#include "library/lcd/serialize.h"

namespace weact_a {

enum Command : uint8_t
{
    CMD_WHO_AM_I = 0x81,  // Establish communication before driving the screen
    CMD_SET_ORIENTATION = 0x02,  // Sets the screen orientation
    CMD_SET_BRIGHTNESS = 0x03,  // Sets the screen brightness
    CMD_FULL = 0x04,  // Displays an image on the screen
    CMD_SET_BITMAP = 0x05,  // Displays an image on the screen
    CMD_SET_BITMAP_WITH_FASTLZ = 0x15,
    CMD_ENABLE_HUMITURE_REPORT = 0x06,
    CMD_FREE = 0x07,
    CMD_SYSTEM_VERSION = 0x42,
    CMD_END = 0x0A,  // Displays an image on the screen
    CMD_READ = 0x80,
};

}  // namespace weact_a

class LcdCommWeActA : public LcdComm
{
public:
    LcdCommWeActA(const std::string &com_port = "AUTO", int display_width = 320, int display_height = 480,
                  UpdateQueue *update_queue = nullptr);
    ~LcdCommWeActA() override;

    std::optional<std::string> auto_detect_com_port() override;

    void Send_Bitmap_xy_Command(int xs, int ys, int xe, int ye, bool bypass_queue = false);
    void SendCommand(const Bytes &byteBuffer, bool bypass_queue = false);

    void InitializeComm() override;
    void Reset() override;
    void Clear() override;
    void Full(RGBColor color = {0, 0, 0});
    void ScreenOff() override;
    void ScreenOn() override;
    void SetBrightness(int level = 0) override;
    void SetOrientation(Orientation orientation = Orientation::PORTRAIT) override;
    bool SetSensorReportTime(int time_ms);
    void Free();
    // Read the temperature (°C) and humidity (%) reported by the screen sensor
    std::pair<double, double> HandleSensorReport();
    void DisplayPILImage(const Image &image, int x = 0, int y = 0, int image_width = 0, int image_height = 0) override;

    int brightness = 0;
    double temperature = 0;
    double humidness = 0;
    bool support_fastlz = false;
};
