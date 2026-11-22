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

#include "library/lcd/lcd_comm_rev_a.h"

#include <chrono>
#include <stdexcept>
#include <thread>

#include "library/lcd/serialize.h"
#include "library/log.h"

using namespace rev_a;

LcdCommRevA::LcdCommRevA(const std::string &com_port, int display_width, int display_height,
                         UpdateQueue *update_queue)
    : LcdComm(com_port, display_width, display_height, update_queue)
{
    logger.debug("HW revision: A");
    openSerial();
}

LcdCommRevA::~LcdCommRevA()
{
    closeSerial();
}

std::optional<std::string> LcdCommRevA::auto_detect_com_port()
{
    for (const auto &com_port: comports()) {
        if (com_port.serial_number == "USB35INCHIPSV2") {
            return com_port.device;
        }
        if (com_port.vid == 0x1a86 && com_port.pid == 0x5722) {
            return com_port.device;
        }
    }
    return std::nullopt;
}

void LcdCommRevA::SendCommand(Command cmd, int x, int y, int ex, int ey, bool bypass_queue)
{
    Bytes byteBuffer(6);
    byteBuffer[0] = static_cast<uint8_t>(x >> 2);
    byteBuffer[1] = static_cast<uint8_t>(((x & 3) << 6) + (y >> 4));
    byteBuffer[2] = static_cast<uint8_t>(((y & 15) << 4) + (ex >> 6));
    byteBuffer[3] = static_cast<uint8_t>(((ex & 63) << 2) + (ey >> 8));
    byteBuffer[4] = static_cast<uint8_t>(ey & 255);
    byteBuffer[5] = cmd;

    // If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
    if (!update_queue || bypass_queue) {
        WriteData(byteBuffer);
    } else {
        // Lock queue mutex then queue the request
        std::lock_guard lock(update_queue_mutex);
        update_queue->put([this, byteBuffer] { WriteData(byteBuffer); });
    }
}

void LcdCommRevA::_hello()
{
    const Bytes hello(6, HELLO);

    // This command reads LCD answer on serial link, so it bypasses the queue
    WriteData(hello);
    const Bytes response = serial_read(6);
    serial_flush_input();

    const char *name;
    if (response == Bytes(6, 0x01)) {
        sub_revision = SubRevision::USBMONITOR_3_5;
        name = "USBMONITOR_3_5";
        display_width = 320;
        display_height = 480;
    } else if (response == Bytes(6, 0x02)) {
        sub_revision = SubRevision::USBMONITOR_5;
        name = "USBMONITOR_5";
        display_width = 480;
        display_height = 800;
    } else if (response == Bytes(6, 0x03)) {
        sub_revision = SubRevision::USBMONITOR_7;
        name = "USBMONITOR_7";
        display_width = 600;
        display_height = 1024;
    } else {
        sub_revision = SubRevision::TURING_3_5;
        name = "TURING_3_5";
        display_width = 320;
        display_height = 480;
    }

    logger.debug("HW sub-revision: SubRevision.{}", name);
}

void LcdCommRevA::InitializeComm()
{
    _hello();
}

void LcdCommRevA::Reset()
{
    logger.info("Display reset (COM port may change)...");
    // Reset command bypasses queue because it is run when queue threads are not yet started
    SendCommand(RESET, 0, 0, 0, 0, true);
    closeSerial();
    // Wait for display reset then reconnect
    std::this_thread::sleep_for(std::chrono::seconds(5));
    openSerial();
}

void LcdCommRevA::Clear()
{
    SetOrientation(Orientation::PORTRAIT);  // Bug: orientation needs to be PORTRAIT before clearing
    SendCommand(CLEAR, 0, 0, 0, 0);
    SetOrientation();  // Restore default orientation
}

void LcdCommRevA::ScreenOff()
{
    SendCommand(SCREEN_OFF, 0, 0, 0, 0);
}

void LcdCommRevA::ScreenOn()
{
    SendCommand(SCREEN_ON, 0, 0, 0, 0);
}

void LcdCommRevA::SetBrightness(int level)
{
    if (level < 0 || level > 100) {
        throw std::invalid_argument("Brightness level must be [0-100]");
    }

    // Display scales from 0 to 255, with 0 being the brightest and 255 being the darkest.
    // Convert our brightness % to an absolute value.
    const int level_absolute = static_cast<int>(255 - ((level / 100.0) * 255));

    // Level : 0 (brightest) - 255 (darkest)
    SendCommand(SET_BRIGHTNESS, level_absolute, 0, 0, 0);
}

void LcdCommRevA::SetOrientation(Orientation new_orientation)
{
    orientation = new_orientation;
    const int width = get_width();
    const int height = get_height();
    const int x = 0, y = 0, ex = 0, ey = 0;
    Bytes byteBuffer(16);
    byteBuffer[0] = static_cast<uint8_t>(x >> 2);
    byteBuffer[1] = static_cast<uint8_t>(((x & 3) << 6) + (y >> 4));
    byteBuffer[2] = static_cast<uint8_t>(((y & 15) << 4) + (ex >> 6));
    byteBuffer[3] = static_cast<uint8_t>(((ex & 63) << 2) + (ey >> 8));
    byteBuffer[4] = static_cast<uint8_t>(ey & 255);
    byteBuffer[5] = SET_ORIENTATION;
    byteBuffer[6] = static_cast<uint8_t>(static_cast<int>(new_orientation) + 100);
    byteBuffer[7] = static_cast<uint8_t>(width >> 8);
    byteBuffer[8] = static_cast<uint8_t>(width & 255);
    byteBuffer[9] = static_cast<uint8_t>(height >> 8);
    byteBuffer[10] = static_cast<uint8_t>(height & 255);
    serial_write(byteBuffer);
}

void LcdCommRevA::DisplayPILImage(const Image &input, int x, int y, int image_width, int image_height)
{
    Image image = input;
    const int width = get_width(), height = get_height();

    // If the image height/width isn't provided, use the native image size
    if (!image_height) {
        image_height = image.height();
    }
    if (!image_width) {
        image_width = image.width();
    }

    // If our image size + the (x, y) position offsets are bigger than
    // our display, reduce the image size to fit our screen
    if (x + image_width > width) {
        image_width = width - x;
    }
    if (y + image_height > height) {
        image_height = height - y;
    }

    if (image_width != image.width() || image_height != image.height()) {
        image = image.crop(0, 0, image_width, image_height);
    }

    if (x > width) throw std::invalid_argument("Image X coordinate must be <= display width");
    if (y > height) throw std::invalid_argument("Image Y coordinate must be <= display height");
    if (image_height <= 0) throw std::invalid_argument("Image height must be > 0");
    if (image_width <= 0) throw std::invalid_argument("Image width must be > 0");

    const int x0 = x, y0 = y;
    const int x1 = x + image_width - 1, y1 = y + image_height - 1;

    const Bytes rgb565le = image_to_RGB565(image, "little");

    SendCommand(DISPLAY_BITMAP, x0, y0, x1, y1);

    // Lock queue mutex then queue all the requests for the image data
    std::lock_guard lock(update_queue_mutex);
    // Send image data by multiple of "display width" bytes
    for (const auto &chunk: chunked(rgb565le, static_cast<size_t>(width) * 8)) {
        SendLine(chunk);
    }
}
