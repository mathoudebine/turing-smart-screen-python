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

// C++ port of library/lcd/lcd_comm_rev_b.py

#include "library/lcd/lcd_comm_rev_b.h"

#include <chrono>
#include <format>
#include <stdexcept>
#include <thread>

#include "library/log.h"

using namespace rev_b;

LcdCommRevB::LcdCommRevB(const std::string &com_port, int display_width, int display_height,
                         UpdateQueue *update_queue)
    : LcdComm(com_port, display_width, display_height, update_queue)
{
    logger.debug("HW revision: B");
    openSerial();
}

LcdCommRevB::~LcdCommRevB()
{
    closeSerial();
}

bool LcdCommRevB::is_flagship() const
{
    return sub_revision == SubRevision::A02 || sub_revision == SubRevision::A12;
}

bool LcdCommRevB::is_brightness_range() const
{
    return sub_revision == SubRevision::A11 || sub_revision == SubRevision::A12;
}

std::optional<std::string> LcdCommRevB::auto_detect_com_port()
{
    for (const auto &com_port: comports()) {
        if (com_port.serial_number == "2017-2-25") {
            return com_port.device;
        }
        if (com_port.vid == 0x1a86 && com_port.pid == 0x5722) {
            return com_port.device;
        }
    }
    return std::nullopt;
}

void LcdCommRevB::SendCommand(Command cmd, const std::vector<uint8_t> &payload_in, bool bypass_queue)
{
    // New protocol (10 byte packets, framed with the command, 8 data bytes inside)
    std::vector<uint8_t> payload = payload_in;
    payload.resize(8, 0);

    Bytes byteBuffer(10);
    byteBuffer[0] = cmd;
    for (int i = 0; i < 8; i++) {
        byteBuffer[i + 1] = payload[i];
    }
    byteBuffer[9] = cmd;

    // If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
    if (!update_queue || bypass_queue) {
        WriteData(byteBuffer);
    } else {
        // Lock queue mutex then queue the request
        std::lock_guard lock(update_queue_mutex);
        update_queue->put([this, byteBuffer] { WriteData(byteBuffer); });
    }
}

void LcdCommRevB::_hello()
{
    const std::vector<uint8_t> hello = {'H', 'E', 'L', 'L', 'O'};

    // This command reads LCD answer on serial link, so it bypasses the queue
    SendCommand(HELLO, hello, true);
    const Bytes response = serial_read(10);
    serial_flush_input();

    if (response.size() != 10) {
        logger.warning("Device not recognised (short response to HELLO)");
    }
    if (response.empty()) {
        throw std::runtime_error("Device did not return anything");
    }
    if (response[0] != HELLO || response.back() != HELLO) {
        logger.warning("Device not recognised (bad framing)");
    }
    if (response.size() < 8 || !std::equal(hello.begin(), hello.end(), response.begin() + 1)) {
        logger.warning("Device not recognised (No HELLO)");
    }
    // The HELLO response here is followed by 2 bytes
    // This is the screen version (not like the revision which is B/flagship)
    // The version is used to determine what capabilities the screen offers (see SubRevision class above)
    if (response.size() >= 8 && response[6] == 0xA) {
        switch (response[7]) {
            case 0x01: sub_revision = SubRevision::A01; break;
            case 0x02: sub_revision = SubRevision::A02; break;
            case 0x11: sub_revision = SubRevision::A11; break;
            case 0x12: sub_revision = SubRevision::A12; break;
            default: logger.warning("Display returned unknown sub-revision on Hello answer");
        }
    }

    logger.debug("HW sub-revision: SubRevision.A{:02X}", static_cast<int>(sub_revision) & 0xFF);
}

void LcdCommRevB::InitializeComm()
{
    _hello();
}

void LcdCommRevB::Reset()
{
    // HW revision B does not implement a command to reset it: clear display instead
    Clear();
}

void LcdCommRevB::Clear()
{
    // HW revision B does not implement a Clear command: display a blank image on the whole screen
    // Force an orientation in case the screen is currently configured with one different from the theme
    const Orientation backup_orientation = orientation;
    SetOrientation(Orientation::PORTRAIT);

    const Image blank(get_width(), get_height(), {255, 255, 255});
    DisplayPILImage(blank);

    // Restore orientation
    SetOrientation(backup_orientation);
}

void LcdCommRevB::ScreenOff()
{
    // HW revision B does not implement a "ScreenOff" native command: using SetBrightness(0) instead
    SetBrightness(0);
}

void LcdCommRevB::ScreenOn()
{
    // HW revision B does not implement a "ScreenOn" native command: using SetBrightness() instead
    SetBrightness();
}

void LcdCommRevB::SetBrightness(int level)
{
    if (level < 0 || level > 100) {
        throw std::invalid_argument("Brightness level must be [0-100]");
    }

    int converted_level;
    if (is_brightness_range()) {
        // Brightness scales from 0 to 255, with 255 being the brightest and 0 being the darkest.
        // Convert our brightness % to an absolute value.
        converted_level = static_cast<int>((level / 100.0) * 255);
    } else {
        // Brightness is 1 (off) or 0 (full brightness)
        logger.info("Your display does not support custom brightness level");
        converted_level = level == 0 ? 1 : 0;
    }

    SendCommand(SET_BRIGHTNESS, {static_cast<uint8_t>(converted_level)});
}

void LcdCommRevB::SetBackplateLedColor(RGBColor led_color)
{
    if (is_flagship()) {
        SendCommand(SET_LIGHTING, {led_color.r, led_color.g, led_color.b});
    } else {
        logger.info("Only HW revision 'flagship' supports backplate LED color setting");
    }
}

void LcdCommRevB::SetOrientation(Orientation new_orientation)
{
    // In revision B, basic orientations (portrait / landscape) are managed by the display
    // The reverse orientations (reverse portrait / reverse landscape) are software-managed
    orientation = new_orientation;
    if (orientation == Orientation::PORTRAIT || orientation == Orientation::REVERSE_PORTRAIT) {
        SendCommand(SET_ORIENTATION, {ORIENTATION_PORTRAIT});
    } else {
        SendCommand(SET_ORIENTATION, {ORIENTATION_LANDSCAPE});
    }
}

Bytes LcdCommRevB::serialize_image(const Image &input, int height, int width) const
{
    Image image = input;
    if (image.width() != width || image.height() != height) {
        image = image.crop(0, 0, width, height);
    }
    if (orientation == Orientation::REVERSE_PORTRAIT || orientation == Orientation::REVERSE_LANDSCAPE) {
        image = image.rotate(180);
    }
    return image_to_RGB565(image, "big");
}

void LcdCommRevB::DisplayPILImage(const Image &image, int x, int y, int image_width, int image_height)
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

    if (x > get_width()) throw std::invalid_argument("Image X coordinate must be <= display width");
    if (y > get_height()) throw std::invalid_argument("Image Y coordinate must be <= display height");
    if (image_height <= 0) throw std::invalid_argument("Image height must be > 0");
    if (image_width <= 0) throw std::invalid_argument("Image width must be > 0");

    int x0, y0, x1, y1;
    if (orientation == Orientation::PORTRAIT || orientation == Orientation::LANDSCAPE) {
        x0 = x;
        y0 = y;
        x1 = x + image_width - 1;
        y1 = y + image_height - 1;
    } else {
        // Reverse landscape/portrait orientations are software-managed: get new coordinates
        x0 = get_width() - x - image_width;
        y0 = get_height() - y - image_height;
        x1 = get_width() - x - 1;
        y1 = get_height() - y - 1;
    }

    SendCommand(DISPLAY_BITMAP, {static_cast<uint8_t>((x0 >> 8) & 255), static_cast<uint8_t>(x0 & 255),
                                 static_cast<uint8_t>((y0 >> 8) & 255), static_cast<uint8_t>(y0 & 255),
                                 static_cast<uint8_t>((x1 >> 8) & 255), static_cast<uint8_t>(x1 & 255),
                                 static_cast<uint8_t>((y1 >> 8) & 255), static_cast<uint8_t>(y1 & 255)});

    const Bytes rgb565be = serialize_image(image, image_height, image_width);

    // Lock queue mutex then queue all the requests for the image data
    std::lock_guard lock(update_queue_mutex);
    // Send image data by multiple of "display width" bytes
    for (const auto &chunk: chunked(rgb565be, static_cast<size_t>(get_width()) * 8)) {
        SendLine(chunk);
    }

    // Implement a cooldown between two bitmaps, because we are not listening to events coming from the display
    // Cooldown of 0.05 decreases "corrupted bitmap" significantly without slowing down too much
    if (update_queue) {
        update_queue->put([] { std::this_thread::sleep_for(std::chrono::milliseconds(50)); });
    } else {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
}
