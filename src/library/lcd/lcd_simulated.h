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

// C++ port of library/lcd/lcd_simulated.py: simulated display, writing to a file (screencap.png) instead of a serial
// port. A web server displays the simulated screen with auto-refresh at http://localhost:5678

#pragma once

#include <atomic>
#include <string>
#include <thread>

#include "library/lcd/lcd_comm.h"

constexpr const char *SCREENSHOT_FILE = "screencap.png";
constexpr int WEBSERVER_PORT = 5678;

// This webserver offer a blank page displaying simulated screen with auto-refresh
class SimulatedLcdWebServer
{
public:
    // Throws std::runtime_error if the server cannot listen on the port
    SimulatedLcdWebServer(const std::string &host, int port);
    ~SimulatedLcdWebServer();

    void shutdown();

private:
    void serve_forever();
    void handle_client(int client_fd);

    int server_fd = -1;
    std::atomic<bool> stopping = false;
    std::thread thread;
};

// Simulated display: write on a file instead of serial port
class LcdSimulated : public LcdComm
{
public:
    LcdSimulated(const std::string &com_port = "AUTO", int display_width = 320, int display_height = 480,
                 UpdateQueue *update_queue = nullptr);
    ~LcdSimulated() override;

    std::optional<std::string> auto_detect_com_port() override;
    void closeSerial() override;
    void InitializeComm() override;
    void Reset() override;
    void Clear() override;
    void ScreenOff() override;
    void ScreenOn() override;
    void SetBrightness(int level = 25) override;
    void SetBackplateLedColor(RGBColor led_color = {255, 255, 255}) override;
    void SetOrientation(Orientation orientation = Orientation::PORTRAIT) override;
    void DisplayPILImage(const Image &image, int x = 0, int y = 0, int image_width = 0, int image_height = 0) override;

    // Current content of the simulated screen
    Image screen_image;

private:
    // Save the screen image to SCREENSHOT_FILE (through a temporary file, so that readers never get a partial file)
    void save_screenshot();

    std::unique_ptr<SimulatedLcdWebServer> webServer;
};
