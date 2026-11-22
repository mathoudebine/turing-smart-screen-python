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

// C++ port of library/lcd/lcd_comm_rev_c.py

#include "library/lcd/lcd_comm_rev_c.h"

#include <cctype>
#include <chrono>
#include <map>
#include <stdexcept>
#include <thread>

#include "library/log.h"

using namespace rev_c;

namespace rev_c {

const Bytes &command_value(Command cmd)
{
    static const std::map<Command, Bytes> values = {
        {Command::HELLO, {0x01, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0xc5, 0xd3}},
        {Command::OPTIONS, {0x7d, 0xef, 0x69, 0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x2d}},
        {Command::RESTART, {0x84, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01}},
        {Command::TURNOFF, {0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01}},
        {Command::TURNON, {0x83, 0xef, 0x69, 0x00, 0x00, 0x00, 0x00}},
        {Command::SET_BRIGHTNESS, {0x7b, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00}},
        {Command::STOP_VIDEO, {0x79, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01}},
        {Command::STOP_MEDIA, {0x96, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01}},
        {Command::QUERY_STATUS, {0xcf, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01}},
        {Command::START_DISPLAY_BITMAP, {0x2c}},
        {Command::PRE_UPDATE_BITMAP, {0x86, 0xef, 0x69, 0x00, 0x00, 0x00, 0x01}},
        {Command::UPDATE_BITMAP, {0xcc, 0xef, 0x69, 0x00}},
        {Command::DISPLAY_BITMAP_2INCH, {0xc8, 0xef, 0x69, 0x00, 0x0E, 0x10}},
        {Command::DISPLAY_BITMAP_5INCH, {0xc8, 0xef, 0x69, 0x00, 0x17, 0x70}},
        {Command::DISPLAY_BITMAP_8INCH, {0xc8, 0xef, 0x69, 0x00, 0x38, 0x40}},
        {Command::STARTMODE_DEFAULT, {0x00}},
        {Command::STARTMODE_IMAGE, {0x01}},
        {Command::STARTMODE_VIDEO, {0x02}},
        {Command::FLIP_180, {0x01}},
        {Command::NO_FLIP, {0x00}},
        {Command::SEND_PAYLOAD, {0xFF}},
    };
    return values.at(cmd);
}

}  // namespace rev_c

namespace {

const char *sub_revision_name(SubRevision sub_revision)
{
    switch (sub_revision) {
        case SubRevision::REV_2INCH: return "SubRevision.REV_2INCH";
        case SubRevision::REV_5INCH: return "SubRevision.REV_5INCH";
        case SubRevision::REV_8INCH: return "SubRevision.REV_8INCH";
        default: return "SubRevision.UNKNOWN";
    }
}

void append_big_endian(Bytes &data, uint64_t value, int size)
{
    for (int i = size - 1; i >= 0; i--) {
        data.push_back(static_cast<uint8_t>((value >> (8 * i)) & 0xFF));
    }
}

// Join the chunks of data with a 0x00 byte between them
Bytes join_chunks(const Bytes &data, size_t chunk_size)
{
    Bytes result;
    result.reserve(data.size() + data.size() / chunk_size + 1);
    bool first = true;
    for (const auto &chunk: chunked(data, chunk_size)) {
        if (!first) {
            result.push_back(0x00);
        }
        result.insert(result.end(), chunk.begin(), chunk.end());
        first = false;
    }
    return result;
}

// HELLO answer from the serial bytes: printable ASCII characters only
std::string printable(const Bytes &data)
{
    std::string result;
    for (uint8_t c: data) {
        if (c < 0x80 && (std::isprint(c) || std::isspace(c))) {
            result.push_back(static_cast<char>(c));
        }
    }
    return result;
}

}  // namespace

LcdCommRevC::LcdCommRevC(const std::string &com_port, int display_width, int display_height,
                         UpdateQueue *update_queue)
    : LcdComm(com_port, display_width, display_height, update_queue)
{
    logger.debug("HW revision: C");
    openSerial();
    // Sub-revision from the resolution, until the screen answers to HELLO (fixes Python version where the
    // sub-revision is undefined before InitializeComm())
    _detect_sub_revision();
}

LcdCommRevC::~LcdCommRevC()
{
    closeSerial();
}

std::optional<std::string> LcdCommRevC::auto_detect_com_port()
{
    // If sleeping device is detected through serial number or vid/pid, try to wake it up
    for (const auto &com_port: comports()) {
        if (com_port.serial_number == "USB7INCH" || com_port.serial_number == "CT21INCH" ||
            com_port.serial_number == "CT88INCH") {
            _wake_up_device(com_port);
        } else if (com_port.vid == 0x1a86 && com_port.pid == 0xca21) {
            _wake_up_device(com_port);
        }
    }

    return _get_awake_com_port(comports());
}

std::optional<std::string> LcdCommRevC::_get_awake_com_port(const std::vector<ListPortInfo> &com_ports)
{
    // Try to find awake device through serial number or vid/pid
    for (const auto &com_port: com_ports) {
        if (com_port.serial_number == "20080411") {
            return com_port.device;
        }
        if (com_port.vid == 0x0525 && com_port.pid == 0xa4a7) {
            return com_port.device;
        }
        if (com_port.vid == 0x1d6b && (com_port.pid == 0x0121 || com_port.pid == 0x0106)) {
            return com_port.device;
        }
    }
    return std::nullopt;
}

void LcdCommRevC::_wake_up_device(const ListPortInfo &com_port)
{
    // Connect to the device to wake it up
    logger.debug("Waiting for device {} to be turned ON...", com_port.device);

    for (int i = 0; i < WAKE_RETRIES; i++) {
        try {
            // Try to connect every second, since it takes sometimes multiple connect to wake up the device
            SerialPort port(com_port.device, 115200, 1.0, true);
        } catch (const SerialException &) {
        }

        if (_get_awake_com_port(comports())) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            logger.debug("Detected screen turned ON");
            return;
        }

        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    logger.error("Could not turn screen on after {} seconds, aborting.", WAKE_RETRIES);
}

void LcdCommRevC::_send_command(Command cmd, const Bytes &payload, Padding padding, bool bypass_queue,
                                std::optional<size_t> readsize)
{
    Bytes message;

    if (cmd != Command::SEND_PAYLOAD) {
        message = command_value(cmd);
    }

    message.insert(message.end(), payload.begin(), payload.end());

    const size_t msg_size = message.size();
    if (msg_size % 250 != 0) {
        const size_t pad_size = 250 * ((msg_size + 249) / 250) - msg_size;
        message.insert(message.end(), pad_size, padding);
    }

    // If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
    if (!update_queue || bypass_queue) {
        WriteData(message);
        if (readsize) {
            ReadData(*readsize);
        }
    } else {
        // Queue the request (mutex is locked by caller)
        update_queue->put([this, message] { WriteData(message); });
        if (readsize) {
            const size_t size = *readsize;
            update_queue->put([this, size] { ReadData(size); });
        }
    }
}

void LcdCommRevC::_detect_sub_revision()
{
    // Note: ID returned by display are not reliable for some models e.g. 2.1" displays return "chs_5inch"
    // Rely on width/height for sub-revision detection
    if (display_width == 480 && display_height == 480) {
        sub_revision = SubRevision::REV_2INCH;
    } else if (display_width == 480 && display_height == 800) {
        sub_revision = SubRevision::REV_5INCH;
    } else if (display_width == 480 && display_height == 1920) {
        sub_revision = SubRevision::REV_8INCH;
    } else {
        sub_revision = SubRevision::UNKNOWN;
        logger.error("Unsupported resolution {}x{} for revision C", display_width, display_height);
    }
}

void LcdCommRevC::_hello()
{
    // This command reads LCD answer on serial link, so it bypasses the queue
    sub_revision = SubRevision::UNKNOWN;
    serial_flush_input();
    _send_command(Command::HELLO, {}, NULL_PADDING, true);
    std::string response = printable(serial_read(23));
    serial_flush_input();
    logger.debug("Display ID returned: {}", response);
    while (!response.starts_with("chs_")) {
        logger.warning("Display returned invalid or unsupported ID, try again in 1 second");
        std::this_thread::sleep_for(std::chrono::seconds(1));
        _send_command(Command::HELLO, {}, NULL_PADDING, true);
        response = printable(serial_read(23));
        serial_flush_input();
        logger.debug("Display ID returned: {}", response);
    }

    _detect_sub_revision();

    // Detect ROM version: 3rd field of the ID, e.g. "chs_5inch.dev1_rom1.87"
    try {
        size_t pos = response.find('.');
        pos = response.find('.', pos + 1);
        if (pos == std::string::npos) {
            throw std::invalid_argument("no ROM version");
        }
        std::string version = response.substr(pos + 1);
        version = version.substr(0, version.find('.'));
        // Like Python int(): surrounding whitespace is allowed
        version.erase(0, version.find_first_not_of(" \t\r\n"));
        version.erase(version.find_last_not_of(" \t\r\n") + 1);
        size_t parsed = 0;
        rom_version = std::stoi(version, &parsed);
        if (parsed != version.size()) {
            throw std::invalid_argument("invalid ROM version");
        }
        if (rom_version < 80 || rom_version > 100) {
            logger.warning("ROM version {} may be invalid, use default ROM version 87", rom_version);
            rom_version = 87;
        }
    } catch (const std::exception &) {
        logger.warning("Display returned invalid or unsupported ID, use default ROM version 87");
        rom_version = 87;
    }

    logger.debug("HW sub-revision detected: {}, ROM version: {}", sub_revision_name(sub_revision), rom_version);
}

void LcdCommRevC::InitializeComm()
{
    _hello();
}

void LcdCommRevC::Reset()
{
    logger.info("Display reset (COM port may change)...");
    // Reset command bypasses queue because it is run when queue threads are not yet started
    _send_command(Command::RESTART, {}, NULL_PADDING, true);
    closeSerial();
    // Wait for disconnection (max. 15 seconds)
    for (int i = 0; i < 15; i++) {
        if (_get_awake_com_port(comports())) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }
    // Wait for reconnection (max. 15 seconds)
    for (int i = 0; i < 15; i++) {
        if (!_get_awake_com_port(comports())) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }
    // Reconnect to device
    openSerial();
}

void LcdCommRevC::Clear()
{
    // This hardware does not implement a Clear command: display a blank image on the whole screen
    // Force an orientation in case the screen is currently configured with one different from the theme
    const Orientation backup_orientation = orientation;
    SetOrientation(Orientation::PORTRAIT);

    const Image blank(get_width(), get_height(), {255, 255, 255});
    DisplayPILImage(blank);

    // Restore orientation
    SetOrientation(backup_orientation);
}

void LcdCommRevC::ScreenOff()
{
    _send_command(Command::STOP_VIDEO);
    _send_command(Command::STOP_MEDIA, {}, NULL_PADDING, false, 1024);
    _send_command(Command::TURNOFF);
}

void LcdCommRevC::ScreenOn()
{
    _send_command(Command::STOP_VIDEO);
    _send_command(Command::STOP_MEDIA, {}, NULL_PADDING, false, 1024);
}

void LcdCommRevC::SetBrightness(int level)
{
    if (level < 0 || level > 100) {
        throw std::invalid_argument("Brightness level must be [0-100]");
    }

    // Brightness scales from 0 to 255, with 255 being the brightest and 0 being the darkest.
    // Convert our brightness % to an absolute value.
    const int converted_level = static_cast<int>((level / 100.0) * 255);

    _send_command(Command::SET_BRIGHTNESS, {static_cast<uint8_t>(converted_level)}, NULL_PADDING, true);
}

void LcdCommRevC::SetOrientation(Orientation new_orientation)
{
    orientation = new_orientation;
    // Reverse orientations are managed by software (FLIP_180 option not used)
    Bytes b = command_value(Command::STARTMODE_DEFAULT);
    b.push_back(NULL_PADDING);
    b.push_back(command_value(Command::NO_FLIP)[0]);
    b.push_back(OFF);
    _send_command(Command::OPTIONS, b);
}

void LcdCommRevC::DisplayPILImage(const Image &input, int x, int y, int image_width, int image_height)
{
    Image image = input;

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

    if (image_width != image.width() || image_height != image.height()) {
        image = image.crop(0, 0, image_width, image_height);
    }

    if (x > get_width()) throw std::invalid_argument("Image X coordinate must be <= display width");
    if (y > get_height()) throw std::invalid_argument("Image Y coordinate must be <= display height");
    if (image_height <= 0) throw std::invalid_argument("Image height must be > 0");
    if (image_width <= 0) throw std::invalid_argument("Image width must be > 0");

    if (x == 0 && y == 0 && image_width == get_width() && image_height == get_height()) {
        std::lock_guard lock(update_queue_mutex);
        _send_command(Command::PRE_UPDATE_BITMAP);
        _send_command(Command::START_DISPLAY_BITMAP, {}, START_DISPLAY_BITMAP_PADDING);

        Command display_bmp_cmd;
        if (sub_revision == SubRevision::REV_5INCH) {
            display_bmp_cmd = Command::DISPLAY_BITMAP_5INCH;
        } else if (sub_revision == SubRevision::REV_2INCH) {
            display_bmp_cmd = Command::DISPLAY_BITMAP_2INCH;
        } else if (sub_revision == SubRevision::REV_8INCH) {
            display_bmp_cmd = Command::DISPLAY_BITMAP_8INCH;
        } else {
            throw std::runtime_error("Unsupported display sub-revision for revision C");
        }

        Bytes size_payload;
        append_big_endian(size_payload, static_cast<uint64_t>(display_width * display_width / 64), 2);
        _send_command(display_bmp_cmd, size_payload);
        _send_command(Command::SEND_PAYLOAD, _generate_full_image(image), NULL_PADDING, false, 1024);
        _send_command(Command::QUERY_STATUS, {}, NULL_PADDING, false, 1024);
    } else {
        {
            std::lock_guard lock(update_queue_mutex);
            const auto [img, pyd] = _generate_update_image(image, x, y, count_start, Command::UPDATE_BITMAP);
            _send_command(Command::SEND_PAYLOAD, pyd);
            _send_command(Command::SEND_PAYLOAD, img);
            _send_command(Command::QUERY_STATUS, {}, NULL_PADDING, false, 1024);
        }
        count_start += 1;
    }
}

Bytes LcdCommRevC::_generate_full_image(const Image &input) const
{
    Image image = input;
    if (sub_revision == SubRevision::REV_8INCH) {
        // Switch landscape/portrait mode for 8"
        if (orientation == Orientation::LANDSCAPE) {
            image = image.rotate(270);
        } else if (orientation == Orientation::REVERSE_LANDSCAPE) {
            image = image.rotate(90);
        } else if (orientation == Orientation::PORTRAIT) {
            image = image.rotate(180);
        }
    } else {
        if (orientation == Orientation::PORTRAIT) {
            image = image.rotate(90);
        } else if (orientation == Orientation::REVERSE_PORTRAIT) {
            image = image.rotate(270);
        } else if (orientation == Orientation::REVERSE_LANDSCAPE) {
            image = image.rotate(180);
        }
    }

    const auto [bgra_data, pixel_size] = image_to_BGRA(image);
    return join_chunks(bgra_data, 249);
}

std::pair<Bytes, Bytes> LcdCommRevC::_generate_update_image(const Image &input, int x, int y, int count,
                                                            std::optional<Command> cmd) const
{
    Image image = input;
    int x0 = x, y0 = y;
    if (sub_revision == SubRevision::REV_8INCH) {
        // Switch landscape/portrait mode for 8"
        if (orientation == Orientation::LANDSCAPE) {
            image = image.rotate(270);
            y0 = get_height() - y - image.width();
        } else if (orientation == Orientation::REVERSE_LANDSCAPE) {
            image = image.rotate(90);
            x0 = get_width() - x - image.height();
        } else if (orientation == Orientation::PORTRAIT) {
            image = image.rotate(180);
            x0 = get_height() - y - image.height();
            y0 = get_height() - x - image.width();
        } else if (orientation == Orientation::REVERSE_PORTRAIT) {
            x0 = y;
            y0 = x;
        }
    } else {
        if (orientation == Orientation::PORTRAIT) {
            image = image.rotate(90);
            x0 = get_width() - x - image.height();
        } else if (orientation == Orientation::REVERSE_PORTRAIT) {
            image = image.rotate(270);
            y0 = get_height() - y - image.width();
        } else if (orientation == Orientation::REVERSE_LANDSCAPE) {
            image = image.rotate(180);
            y0 = get_width() - x - image.width();
            x0 = get_height() - y - image.height();
        } else if (orientation == Orientation::LANDSCAPE) {
            x0 = y;
            y0 = x;
        }
    }

    // Some screens require different RGBA encoding
    Bytes img_data;
    int pixel_size;
    if (sub_revision != SubRevision::REV_2INCH && rom_version > 88) {
        // BGRA mode on 4 bytes : [B, G, R, A]
        std::tie(img_data, pixel_size) = image_to_BGRA(image);
    } else {
        // BGRA mode on 3 bytes: [6-bit B + 2-bit A, 6-bit G + 2-bit A, 8-bit R]
        // For now use simple BGR that is more optimized, because this program does not support transparent background
        std::tie(img_data, pixel_size) = image_to_BGR(image);
    }

    Bytes img_raw_data;
    int h = 0;
    for (const auto &line: chunked(img_data, static_cast<size_t>(image.width()) * pixel_size)) {
        if (sub_revision == SubRevision::REV_8INCH) {
            // Switch landscape/portrait mode for 8"
            append_big_endian(img_raw_data, static_cast<uint64_t>(((x0 + h) * display_width) + y0), 3);
        } else {
            append_big_endian(img_raw_data, static_cast<uint64_t>(((x0 + h) * display_height) + y0), 3);
        }
        append_big_endian(img_raw_data, static_cast<uint64_t>(image.width()), 2);
        img_raw_data.insert(img_raw_data.end(), line.begin(), line.end());
        h++;
    }

    Bytes payload;
    if (cmd) {
        const Bytes &value = command_value(*cmd);
        payload.insert(payload.end(), value.begin(), value.end());
    }
    // The +2 is for the "ef69" that will be added later.
    append_big_endian(payload, img_raw_data.size() + 2, 3);
    payload.insert(payload.end(), 3, NULL_PADDING);
    append_big_endian(payload, static_cast<uint64_t>(count), 4);

    if (img_raw_data.size() > 250) {
        img_raw_data = join_chunks(img_raw_data, 249);
    }
    img_raw_data.push_back(0xef);
    img_raw_data.push_back(0x69);

    return {img_raw_data, payload};
}
