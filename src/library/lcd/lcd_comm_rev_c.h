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
// This class is for Turing Smart Screen 2.1" / 2.8" / 5" / 8" screens
//
// ORDER:
// SEND HELLO
// READ HELLO (23)
// SEND STOP_VIDEO
// SEND STOP_MEDIA
// READ STATUS (1024)
// SEND SET_BRIGHTNESS
// SEND SET_OPTIONS WITH ORIENTATION ?
// SEND PRE_UPDATE_BITMAP
// SEND START_DISPLAY_BITMAP
// SEND DISPLAY_BITMAP
// READ STATUS (1024)
// SEND QUERY_STATUS
// READ STATUS (1024)
// WHILE:
//   SEND UPDATE_BITMAP
//   SEND QUERY_STATUS
//   READ STATUS(1024)

#pragma once

#include <optional>
#include <utility>

#include "library/lcd/lcd_comm.h"
#include "library/lcd/serialize.h"

namespace rev_c {

enum class Command
{
    HELLO,
    OPTIONS,
    RESTART,
    TURNOFF,
    TURNON,
    SET_BRIGHTNESS,

    // STOP COMMANDS
    STOP_VIDEO,
    STOP_MEDIA,

    // IMAGE QUERY STATUS
    QUERY_STATUS,

    // STATIC IMAGE
    START_DISPLAY_BITMAP,
    PRE_UPDATE_BITMAP,
    UPDATE_BITMAP,
    DISPLAY_BITMAP_2INCH,
    DISPLAY_BITMAP_5INCH,
    DISPLAY_BITMAP_8INCH,

    STARTMODE_DEFAULT,
    STARTMODE_IMAGE,
    STARTMODE_VIDEO,
    FLIP_180,
    NO_FLIP,
    SEND_PAYLOAD,
};

// Bytes of a command
const Bytes &command_value(Command cmd);

enum Padding : uint8_t
{
    NULL_PADDING = 0x00,
    START_DISPLAY_BITMAP_PADDING = 0x2c,
};

enum SleepInterval : uint8_t
{
    OFF = 0x00, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN,
};

enum class SubRevision
{
    UNKNOWN = 0,
    REV_2INCH = 1,  // For 2.1" and 2.8" models
    REV_5INCH = 2,
    REV_8INCH = 3,
};

constexpr int WAKE_RETRIES = 15;

}  // namespace rev_c

class LcdCommRevC : public LcdComm
{
public:
    LcdCommRevC(const std::string &com_port = "AUTO", int display_width = 480, int display_height = 800,
                UpdateQueue *update_queue = nullptr);
    ~LcdCommRevC() override;

    std::optional<std::string> auto_detect_com_port() override;

    void InitializeComm() override;
    void Reset() override;
    void Clear() override;
    void ScreenOff() override;
    void ScreenOn() override;
    void SetBrightness(int level = 25) override;
    void SetOrientation(Orientation orientation = Orientation::PORTRAIT) override;
    void DisplayPILImage(const Image &image, int x = 0, int y = 0, int image_width = 0, int image_height = 0) override;

    // Number of partial screen updates sent (shared by all instances, like the Python Count class)
    static inline int count_start = 0;

    rev_c::SubRevision sub_revision = rev_c::SubRevision::UNKNOWN;
    int rom_version = 87;

private:
    static std::optional<std::string> _get_awake_com_port(const std::vector<ListPortInfo> &com_ports);
    static void _wake_up_device(const ListPortInfo &com_port);

    void _send_command(rev_c::Command cmd, const Bytes &payload = {},
                       rev_c::Padding padding = rev_c::NULL_PADDING, bool bypass_queue = false,
                       std::optional<size_t> readsize = std::nullopt);
    void _hello();
    void _detect_sub_revision();
    Bytes _generate_full_image(const Image &image) const;
    std::pair<Bytes, Bytes> _generate_update_image(const Image &image, int x, int y, int count,
                                                   std::optional<rev_c::Command> cmd = std::nullopt) const;
};
