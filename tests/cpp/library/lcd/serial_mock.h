// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
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

// C++ port of tests/library/lcd/serial_mock.py and tests/library/lcd/sample_image.py:
// serial port double recording the data written/read by the drivers, compared with golden files.

#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <type_traits>
#include <vector>

#include "library/lcd/image.h"
#include "library/lcd/lcd_comm.h"
#include "library/lcd/lcd_comm_rev_c.h"

// Golden files recorded by the Python tests
constexpr const char *GOLDEN_DIR = "tests/library/lcd/golden/";

// Serial port that records the calls as text lines: "write <hex data>" / "read <size>"
class MockSerial : public SerialPort
{
public:
    MockSerial() = default;

    void close() override {}
    bool is_open() const override { return true; }
    void write(const std::vector<uint8_t> &data) override;
    std::vector<uint8_t> read(size_t size) override;
    std::vector<uint8_t> readall() override { return {}; }
    void flush() override {}
    void reset_input_buffer() override {}
    size_t in_waiting() override { return 0; }

    std::string calls;
};

// While this object exists, the drivers use a MockSerial instead of a real serial port
class SerialMockScope
{
public:
    SerialMockScope();
    ~SerialMockScope();

    // Serial port of the last driver created
    MockSerial *last = nullptr;
};

// Generates a sample image that has red, green, blue and black in each corner and the other pixels interpolated
// linearly
Image generate_sample_image(int width, int height);

// Content of a golden file, without empty lines
std::string read_golden(const std::string &name);

// FNV-1a 64-bit hash
uint64_t fnv1a(const std::string &text);

// Area of the "patch" test cases
struct Patch
{
    int x = 10, y = 20, width = 100, height = 200;
    // Crop the image to the patch size before displaying it (otherwise the full image is given with the patch size)
    bool crop = false;
};

// Run a test case of the Python driver tests, returns the recorded serial calls.
// Cases: "set_brightness", "display_pil_image_<orientation>", "display_pil_image_patch_<orientation>"
// create: creates the driver (default constructor if not provided)
template<typename Lcd>
std::string run_case(const std::string &name, int portrait_width, int portrait_height, const Patch &p = {},
                     const std::function<std::unique_ptr<Lcd>()> &create = nullptr)
{
    SerialMockScope mock;
    const std::unique_ptr<Lcd> lcd_ptr = create ? create() : std::make_unique<Lcd>();
    Lcd &lcd = *lcd_ptr;
    if constexpr (std::is_same_v<Lcd, LcdCommRevC>) {
        LcdCommRevC::count_start = 0;
    }

    if (name == "set_brightness") {
        lcd.SetBrightness(25);
    } else {
        const bool patch = name.find("_patch_") != std::string::npos;
        const std::string orientation_name = name.substr(name.rfind(patch ? "patch_" : "image_") + 6);
        Orientation orientation = Orientation::PORTRAIT;
        if (orientation_name == "landscape") orientation = Orientation::LANDSCAPE;
        if (orientation_name == "reverse_portrait") orientation = Orientation::REVERSE_PORTRAIT;
        if (orientation_name == "reverse_landscape") orientation = Orientation::REVERSE_LANDSCAPE;
        const bool portrait = orientation_name.find("portrait") != std::string::npos;
        const Image image = portrait ? generate_sample_image(portrait_width, portrait_height)
                                     : generate_sample_image(portrait_height, portrait_width);
        lcd.SetOrientation(orientation);
        if (patch) {
            lcd.DisplayPILImage(p.crop ? image.crop(0, 0, p.width, p.height) : image, p.x, p.y, p.width, p.height);
        } else {
            lcd.DisplayPILImage(image);
        }
    }
    return mock.last->calls;
}

// All test cases, in the same order as the Python tests
inline const std::vector<std::string> TEST_CASES = {
    "set_brightness",
    "display_pil_image_portrait", "display_pil_image_landscape",
    "display_pil_image_reverse_portrait", "display_pil_image_reverse_landscape",
    "display_pil_image_patch_portrait", "display_pil_image_patch_landscape",
    "display_pil_image_patch_reverse_portrait", "display_pil_image_patch_reverse_landscape",
};
