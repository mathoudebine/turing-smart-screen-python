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

#include "library/lcd/lcd_comm_rev_d.h"

#include <map>
#include <stdexcept>

#include "library/log.h"

using namespace rev_d;

namespace rev_d {

const Bytes &command_value(Command cmd)
{
    static const std::map<Command, Bytes> values = {
        {Command::GETINFO, {71, 0, 0, 0}},
        {Command::SETORG, {67, 72, 0, 0}},
        {Command::SET180, {67, 71, 0, 0}},
        {Command::SETHF, {67, 68, 0, 0}},
        {Command::SETVF, {67, 70, 0, 0}},
        {Command::SETBL, {67, 67}},
        {Command::DISPCOLOR, {67, 66}},
        {Command::BLOCKWRITE, {67, 65}},
        {Command::INTOPICMODE, {68, 0, 0, 0}},
        {Command::OUTPICMODE, {65, 0, 0, 0}},
    };
    return values.at(cmd);
}

}  // namespace rev_d

LcdCommRevD::LcdCommRevD(const std::string &com_port, int display_width, int display_height,
                         UpdateQueue *update_queue)
    : LcdComm(com_port, display_width, display_height, update_queue)
{
    logger.debug("HW revision: D");
    openSerial();
}

LcdCommRevD::~LcdCommRevD()
{
    closeSerial();
}

std::optional<std::string> LcdCommRevD::auto_detect_com_port()
{
    for (const auto &com_port: comports()) {
        if (com_port.vid == 0x454d && com_port.pid == 0x4e41) {
            return com_port.device;
        }
    }
    return std::nullopt;
}

void LcdCommRevD::WriteDataAndFlush(const Bytes &byteBuffer)
{
    WriteData(byteBuffer);

    // Empty the input buffer after each write: we don't process acknowledgements the screen sends back
    serial_flush_input();
}

void LcdCommRevD::SendCommand(Command cmd, const Bytes &payload, bool bypass_queue)
{
    Bytes message = command_value(cmd);
    message.insert(message.end(), payload.begin(), payload.end());

    // If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
    if (!update_queue || bypass_queue) {
        WriteDataAndFlush(message);
    } else {
        // Lock queue mutex then queue the request
        std::lock_guard lock(update_queue_mutex);
        update_queue->put([this, message] { WriteDataAndFlush(message); });
    }
}

void LcdCommRevD::InitializeComm()
{
}

void LcdCommRevD::Reset()
{
    // HW revision D does not implement a command to reset it: clear display instead
    Clear();
}

void LcdCommRevD::Clear()
{
    // HW revision D does not implement a Clear command: display a blank image on the whole screen
    // RGB565 White color
    SendCommand(Command::DISPCOLOR, {0xFF, 0xFF});
}

void LcdCommRevD::ScreenOff()
{
    // HW revision D does not implement a "ScreenOff" native command: using SetBrightness(0) instead
    SetBrightness(0);
}

void LcdCommRevD::ScreenOn()
{
    // HW revision D does not implement a "ScreenOn" native command: using SetBrightness() instead
    SetBrightness();
}

void LcdCommRevD::SetBrightness(int level)
{
    if (level < 0 || level > 100) {
        throw std::invalid_argument("Brightness level must be [0-100]");
    }

    // Brightness scales from 0 to 500, with 500 being the brightest and 0 being the darkest.
    // Convert our brightness % to an absolute value.
    const int converted_level = level * 5;
    const Bytes level_bytes = {static_cast<uint8_t>(converted_level >> 8), static_cast<uint8_t>(converted_level & 0xFF)};

    // Send the command twice because sometimes it is not applied...
    SendCommand(Command::SETBL, level_bytes);
    SendCommand(Command::SETBL, level_bytes);
}

void LcdCommRevD::SetOrientation(Orientation new_orientation)
{
    // In revision D, reverse orientations (reverse portrait / reverse landscape) are managed by the display
    // Basic orientations (portrait / landscape) are software-managed because screen commands only support portrait
    orientation = new_orientation;

    if (orientation == Orientation::REVERSE_LANDSCAPE || orientation == Orientation::REVERSE_PORTRAIT) {
        SendCommand(Command::SET180);
    } else {
        SendCommand(Command::SETORG);
    }
}

void LcdCommRevD::DisplayPILImage(const Image &input, int x, int y, int image_width, int image_height)
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

    if (x > width) throw std::invalid_argument("Image X coordinate must be <= display width");
    if (y > height) throw std::invalid_argument("Image Y coordinate must be <= display height");
    if (image_height <= 0) throw std::invalid_argument("Image height must be > 0");
    if (image_width <= 0) throw std::invalid_argument("Image width must be > 0");

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

    int x0, y0, x1, y1;
    if (orientation == Orientation::PORTRAIT || orientation == Orientation::REVERSE_PORTRAIT) {
        x0 = x;
        y0 = y;
        x1 = x + image_width - 1;
        y1 = y + image_height - 1;
    } else {
        // Landscape / reverse landscape orientations are software managed: rotate image -90° and get new coordinates
        image = image.rotate(270);
        x0 = display_width - y - image_height;
        y0 = x;
        x1 = display_width - y - 1;
        y1 = x + image_width - 1;
        std::swap(image_width, image_height);
    }

    // Send bitmap size
    Bytes image_data;
    for (int v: {x0, x1, y0, y1}) {
        image_data.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
        image_data.push_back(static_cast<uint8_t>(v & 0xFF));
    }
    SendCommand(Command::BLOCKWRITE, image_data);

    // Prepare bitmap data transmission
    SendCommand(Command::INTOPICMODE);

    const Bytes rgb565be = image_to_RGB565(image, "big");

    {
        // Lock queue mutex then queue all the requests for the image data
        std::lock_guard lock(update_queue_mutex);
        for (const auto &chunk: chunked(rgb565be, 63)) {
            Bytes line;
            line.reserve(chunk.size() + 1);
            line.push_back(0x50);
            line.insert(line.end(), chunk.begin(), chunk.end());
            SendLine(line);
        }
    }

    // Indicate the complete bitmap has been transmitted
    SendCommand(Command::OUTPICMODE);
}
