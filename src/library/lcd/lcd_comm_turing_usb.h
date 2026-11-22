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

// C++ port of library/lcd/lcd_comm_turing_usb.py
// This class is for Turing Smart Screen newer models (4.6" / 5.2" / 8" / 8.8" HW rev 1.x / 9.2" / 12.3")
// These models are not detected as serial ports but as USB devices (libusb).
//
// Not ported: the H.264 video streaming and file upload helpers of the Python file, which are not used by the
// programs of this project.

#pragma once

#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <utility>

#include "library/lcd/lcd_comm.h"
#include "library/lcd/serialize.h"

namespace turing_usb {

constexpr uint16_t VENDOR_ID = 0x1cbe;

// Map of display supported product IDs and their respective resolution in portrait mode
const std::vector<std::pair<uint16_t, std::pair<int, int>>> &product_ids();

constexpr size_t MAX_CHUNK_BYTES = 1024 * 1024;  // Data sent to screen cannot exceed 1MB or there will be a timeout

// Command IDs used by the vendor protocol (subset)
constexpr uint8_t CMD_UPLOAD_JPEG = 101;
constexpr uint8_t CMD_UPLOAD_PNG = 102;

// Default max payload for frame uploads (device/transport limit)
constexpr size_t MAX_IMAGE_PAYLOAD_DEFAULT = MAX_CHUNK_BYTES;

// DES-CBC encryption (IV = key) of zero-padded data, like pycryptodome DES.new(key, DES.MODE_CBC, key)
Bytes encrypt_with_des(const Bytes &key, const Bytes &data);

// Command packet: 500 bytes, command ID in byte 0, timestamp (ms since local midnight) in bytes 4-7
Bytes build_command_packet_header(uint8_t a0);

// Encrypted command packet: 512 bytes
Bytes encrypt_command_packet(const Bytes &data);

// USB device opened with libusb, with the bulk endpoints of interface 0
class UsbDevice
{
public:
    // Opens the first supported Turing USB screen. Throws std::runtime_error if not found.
    UsbDevice();
    ~UsbDevice();

    UsbDevice(const UsbDevice &) = delete;
    UsbDevice &operator=(const UsbDevice &) = delete;

    uint16_t pid() const { return product_id; }

    // Write data then read the response (512 bytes max), std::nullopt on error
    std::optional<Bytes> write_to_device(const Bytes &data, unsigned int timeout_ms = 2000);

private:
    // Flush the IN endpoint by reading available data until timeout or max attempts reached
    void read_flush(int max_attempts = 5);

    void *context = nullptr;  // libusb_context
    void *handle = nullptr;   // libusb_device_handle
    uint16_t product_id = 0;
    unsigned char ep_out = 0, ep_in = 0;
    bool interrupt_out = false, interrupt_in = false;
};

std::optional<Bytes> send_sync_command(UsbDevice &dev);
std::optional<Bytes> send_brightness_command(UsbDevice &dev, int brightness);
std::optional<Bytes> send_image(UsbDevice &dev, const Bytes &png_data);
std::optional<Bytes> send_jpeg(UsbDevice &dev, const Bytes &jpeg_data);
std::optional<Bytes> clear_image(UsbDevice &dev);

// JPEG data under max_bytes, lowering the quality if needed. Throws std::runtime_error if not possible.
// subsampling: -1 (try 4:2:0, 4:2:2 then 4:4:4), or 0, 1, 2
Bytes encode_jpeg_under_limit(const Image &image, size_t max_bytes, int quality = 95, int subsampling = -1);

// Send the image as PNG, or JPEG if the PNG data is over the limit
void send_pil_image_auto(UsbDevice &dev, const Image &image, size_t max_bytes = MAX_IMAGE_PAYLOAD_DEFAULT);

}  // namespace turing_usb

class LcdCommTuringUSB : public LcdComm
{
public:
    LcdCommTuringUSB(const std::string &com_port = "AUTO", int display_width = 480, int display_height = 1920,
                     UpdateQueue *update_queue = nullptr);
    ~LcdCommTuringUSB() override;

    void InitializeComm() override;
    void Reset() override;
    void Clear() override;
    void ScreenOff() override;
    void ScreenOn() override;
    void SetBrightness(int level = 25) override;
    void SetOrientation(Orientation orientation = Orientation::PORTRAIT) override;
    void DisplayPILImage(const Image &image, int x = 0, int y = 0, int image_width = 0, int image_height = 0) override;

private:
    std::unique_ptr<turing_usb::UsbDevice> dev;
    // Current screen state as an image that will be continuously updated and sent
    Image current_state;
};
