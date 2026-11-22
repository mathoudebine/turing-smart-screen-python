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

// C++ port of library/lcd/lcd_comm_weact_b.py

#include "library/lcd/lcd_comm_weact_b.h"

#include <format>
#include <stdexcept>

#include "library/log.h"

using namespace weact_b;

LcdCommWeActB::LcdCommWeActB(const std::string &com_port, int display_width, int display_height,
                             UpdateQueue *update_queue)
    : LcdComm(com_port, display_width, display_height, update_queue)
{
    openSerial();
}

LcdCommWeActB::~LcdCommWeActB()
{
    closeSerial();
}

std::optional<std::string> LcdCommWeActB::auto_detect_com_port()
{
    for (const auto &com_port: comports()) {
        if (com_port.vid == 0x1a86 && com_port.pid == 0xfe0c) {
            return com_port.device;
        }
        if (com_port.serial_number.starts_with("AD")) {
            return com_port.device;
        }
    }
    return std::nullopt;
}

void LcdCommWeActB::Send_Bitmap_xy_Command(int xs, int ys, int xe, int ye, bool bypass_queue)
{
    const Bytes byteBuffer = {
        CMD_SET_BITMAP,
        static_cast<uint8_t>(xs & 0xFF), static_cast<uint8_t>(xs >> 8 & 0xFF),
        static_cast<uint8_t>(ys & 0xFF), static_cast<uint8_t>(ys >> 8 & 0xFF),
        static_cast<uint8_t>(xe & 0xFF), static_cast<uint8_t>(xe >> 8 & 0xFF),
        static_cast<uint8_t>(ye & 0xFF), static_cast<uint8_t>(ye >> 8 & 0xFF),
        CMD_END,
    };
    SendCommand(byteBuffer, bypass_queue);
}

void LcdCommWeActB::SendCommand(const Bytes &byteBuffer, bool bypass_queue)
{
    // If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
    if (!update_queue || bypass_queue) {
        WriteData(byteBuffer);
    } else {
        // Lock queue mutex then queue the request
        std::lock_guard lock(update_queue_mutex);
        update_queue->put([this, byteBuffer] { WriteData(byteBuffer); });
    }
}

void LcdCommWeActB::InitializeComm()
{
    serial_readall();
    WriteData({CMD_SYSTEM_VERSION | CMD_READ, CMD_END});
    const Bytes response = serial_read(19);
    serial_flush_input();
    if (response.size() == 19) {
        std::string version_str(response.begin() + 1, response.begin() + 9);
        version_str.erase(version_str.find_last_not_of(" \t\r\n") + 1);
        version_str.erase(0, version_str.find_first_not_of(" \t\r\n"));
        logger.info("Device version: {}", version_str);
    } else {
        logger.info("Get version failed");
    }
}

void LcdCommWeActB::Reset()
{
}

void LcdCommWeActB::Clear()
{
    Full({0, 0, 0});
}

void LcdCommWeActB::Full(RGBColor color)
{
    // Color information is 0bRRRRRGGGGGGBBBBB, encoded in Little-Endian
    const uint16_t rgb = static_cast<uint16_t>(((color.r >> 3) << 11) | ((color.g >> 2) << 5) | (color.b >> 3));

    const int xe = get_width();
    const int ye = get_height();

    const Bytes byteBuffer = {
        CMD_FULL, 0, 0, 0, 0,
        static_cast<uint8_t>((xe - 1) & 0xff), static_cast<uint8_t>((xe >> 8) & 0xff),
        static_cast<uint8_t>((ye - 1) & 0xff), static_cast<uint8_t>((ye >> 8) & 0xff),
        static_cast<uint8_t>(rgb & 0xFF), static_cast<uint8_t>(rgb >> 8),
        CMD_END,
    };
    SendCommand(byteBuffer);
}

void LcdCommWeActB::ScreenOff()
{
    SetBrightness(0);
    Free();
}

void LcdCommWeActB::ScreenOn()
{
    SetBrightness(brightness);
}

void LcdCommWeActB::SetBrightness(int level)
{
    if (level < 0 || level > 100) {
        throw std::invalid_argument("Brightness level must be [0-100]");
    }
    const int converted_level = static_cast<int>((level / 100.0) * 255);
    const int brightness_ms = 1000;
    SendCommand({CMD_SET_BRIGHTNESS, static_cast<uint8_t>(converted_level & 0xFF),
                 static_cast<uint8_t>(brightness_ms & 0xFF), static_cast<uint8_t>(brightness_ms >> 8 & 0xFF),
                 CMD_END});
    brightness = level;
}

void LcdCommWeActB::SetOrientation(Orientation new_orientation)
{
    orientation = new_orientation;
    SendCommand({CMD_SET_ORIENTATION, static_cast<uint8_t>(orientation), CMD_END});
}

void LcdCommWeActB::Free()
{
    SendCommand({CMD_FREE, CMD_END});
}

void LcdCommWeActB::DisplayPILImage(const Image &image, int x, int y, int image_width, int image_height)
{
    // If the image height/width isn't provided, use the native image size
    if (!image_height) {
        image_height = image.height();
    }
    if (!image_width) {
        image_width = image.width();
    }

    // If our image is bigger than our display, resize it to fit our screen
    if (image.height() > get_height()) {
        image_height = get_height();
    }
    if (image.width() > get_width()) {
        image_width = get_width();
    }

    if (x > get_width()) {
        throw std::invalid_argument(
            std::format("Display Image X {} coordinate must be <= display width {}", x, get_width()));
    }
    if (y > get_height()) {
        throw std::invalid_argument(
            std::format("Display Image Y {} coordinate must be <= display height {}", y, get_height()));
    }
    if (x < 0) throw std::invalid_argument(std::format("Display Image X {} coordinate must be >= 0", x));
    if (y < 0) throw std::invalid_argument(std::format("Display Image Y {} coordinate must be >= 0", y));
    if (image_height <= 0) throw std::invalid_argument("Image height must be > 0");
    if (image_width <= 0) throw std::invalid_argument("Image width must be > 0");
    if (x + image_width > get_width()) {
        throw std::invalid_argument(std::format("Display Bitmap width+x exceeds display width {}", get_width()));
    }
    if (y + image_height > get_height()) {
        throw std::invalid_argument(std::format("Display Bitmap height+y exceeds display height {}", get_height()));
    }

    const int x0 = x, y0 = y;
    const int x1 = x + image_width - 1, y1 = y + image_height - 1;

    const Bytes byteBuffer = {
        CMD_SET_BITMAP,
        static_cast<uint8_t>(x0 & 0xFF), static_cast<uint8_t>(x0 >> 8 & 0xFF),
        static_cast<uint8_t>(y0 & 0xFF), static_cast<uint8_t>(y0 >> 8 & 0xFF),
        static_cast<uint8_t>(x1 & 0xFF), static_cast<uint8_t>(x1 >> 8 & 0xFF),
        static_cast<uint8_t>(y1 & 0xFF), static_cast<uint8_t>(y1 >> 8 & 0xFF),
        CMD_END,
    };

    const size_t line_to_send_size = static_cast<size_t>(get_width()) * 4;

    // The image is sent as is (not cropped to image_width/image_height, like the Python version)
    const Bytes rgb565le = image_to_RGB565(image, "little");

    // Lock queue mutex then queue all the requests for the image data
    std::lock_guard lock(update_queue_mutex);
    SendLine(byteBuffer);
    for (const auto &chunk: chunked(rgb565le, line_to_send_size)) {
        SendLine(chunk);
    }
}
