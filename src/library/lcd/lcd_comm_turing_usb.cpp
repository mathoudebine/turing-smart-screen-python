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

#include "library/lcd/lcd_comm_turing_usb.h"

#include <array>
#include <cerrno>
#include <chrono>
#include <ctime>
#include <format>
#include <stdexcept>

#include <libusb.h>

#include "library/log.h"

namespace turing_usb {

const std::vector<std::pair<uint16_t, std::pair<int, int>>> &product_ids()
{
    static const std::vector<std::pair<uint16_t, std::pair<int, int>>> ids = {
        {0x0028, {480, 480}},    // Turing 2.8" round (USB)
        {0x0046, {320, 960}},    // Turing 4.6"
        {0x0050, {720, 1280}},   // Turing 5.2"
        {0x0080, {800, 1280}},   // Turing 8.0"
        {0x0088, {480, 1920}},   // Turing 8.8"
        {0x0092, {462, 1920}},   // Turing 9.2"
        {0x0123, {720, 1920}},   // Turing 12.3"
    };
    return ids;
}

// ---------------------------------------------------------------------------------------------------------------------
// DES block cipher (FIPS 46-3), replacing pycryptodome

namespace {

constexpr uint8_t IP[64] = {58, 50, 42, 34, 26, 18, 10, 2, 60, 52, 44, 36, 28, 20, 12, 4,
                            62, 54, 46, 38, 30, 22, 14, 6, 64, 56, 48, 40, 32, 24, 16, 8,
                            57, 49, 41, 33, 25, 17, 9, 1, 59, 51, 43, 35, 27, 19, 11, 3,
                            61, 53, 45, 37, 29, 21, 13, 5, 63, 55, 47, 39, 31, 23, 15, 7};
constexpr uint8_t FP[64] = {40, 8, 48, 16, 56, 24, 64, 32, 39, 7, 47, 15, 55, 23, 63, 31,
                            38, 6, 46, 14, 54, 22, 62, 30, 37, 5, 45, 13, 53, 21, 61, 29,
                            36, 4, 44, 12, 52, 20, 60, 28, 35, 3, 43, 11, 51, 19, 59, 27,
                            34, 2, 42, 10, 50, 18, 58, 26, 33, 1, 41, 9, 49, 17, 57, 25};
constexpr uint8_t E[48] = {32, 1, 2, 3, 4, 5, 4, 5, 6, 7, 8, 9, 8, 9, 10, 11, 12, 13, 12, 13, 14, 15, 16, 17,
                           16, 17, 18, 19, 20, 21, 20, 21, 22, 23, 24, 25, 24, 25, 26, 27, 28, 29, 28, 29, 30, 31, 32, 1};
constexpr uint8_t P[32] = {16, 7, 20, 21, 29, 12, 28, 17, 1, 15, 23, 26, 5, 18, 31, 10,
                           2, 8, 24, 14, 32, 27, 3, 9, 19, 13, 30, 6, 22, 11, 4, 25};
constexpr uint8_t PC1[56] = {57, 49, 41, 33, 25, 17, 9, 1, 58, 50, 42, 34, 26, 18, 10, 2, 59, 51, 43, 35, 27, 19, 11, 3,
                             60, 52, 44, 36, 63, 55, 47, 39, 31, 23, 15, 7, 62, 54, 46, 38, 30, 22, 14, 6, 61, 53, 45, 37,
                             29, 21, 13, 5, 28, 20, 12, 4};
constexpr uint8_t PC2[48] = {14, 17, 11, 24, 1, 5, 3, 28, 15, 6, 21, 10, 23, 19, 12, 4, 26, 8, 16, 7, 27, 20, 13, 2,
                             41, 52, 31, 37, 47, 55, 30, 40, 51, 45, 33, 48, 44, 49, 39, 56, 34, 53, 46, 42, 50, 36, 29, 32};
constexpr uint8_t SHIFTS[16] = {1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1};
constexpr uint8_t SBOX[8][64] = {
    {14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7, 0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
     4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0, 15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13},
    {15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10, 3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
     0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15, 13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9},
    {10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8, 13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
     13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7, 1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12},
    {7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15, 13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
     10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4, 3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14},
    {2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9, 14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
     4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14, 11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3},
    {12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11, 10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
     9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6, 4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13},
    {4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1, 13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
     1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2, 6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12},
    {13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7, 1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
     7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8, 2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11},
};

// Bit permutation: output bit i (from the most significant) is input bit table[i] (1-based, from the most significant)
template<size_t N>
uint64_t permute(uint64_t input, int input_bits, const uint8_t (&table)[N])
{
    uint64_t output = 0;
    for (size_t i = 0; i < N; i++) {
        output = (output << 1) | ((input >> (input_bits - table[i])) & 1);
    }
    return output;
}

std::array<uint64_t, 16> des_subkeys(uint64_t key)
{
    std::array<uint64_t, 16> subkeys{};
    const uint64_t cd = permute(key, 64, PC1);
    uint32_t c = static_cast<uint32_t>(cd >> 28) & 0x0FFFFFFF;
    uint32_t d = static_cast<uint32_t>(cd) & 0x0FFFFFFF;
    for (int round = 0; round < 16; round++) {
        c = ((c << SHIFTS[round]) | (c >> (28 - SHIFTS[round]))) & 0x0FFFFFFF;
        d = ((d << SHIFTS[round]) | (d >> (28 - SHIFTS[round]))) & 0x0FFFFFFF;
        subkeys[round] = permute((static_cast<uint64_t>(c) << 28) | d, 56, PC2);
    }
    return subkeys;
}

uint64_t des_encrypt_block(uint64_t block, const std::array<uint64_t, 16> &subkeys)
{
    const uint64_t ip = permute(block, 64, IP);
    uint32_t left = static_cast<uint32_t>(ip >> 32);
    uint32_t right = static_cast<uint32_t>(ip);
    for (int round = 0; round < 16; round++) {
        const uint64_t expanded = permute(right, 32, E) ^ subkeys[round];
        uint32_t substituted = 0;
        for (int box = 0; box < 8; box++) {
            const auto six = static_cast<uint8_t>((expanded >> (42 - 6 * box)) & 0x3F);
            const int row = ((six & 0x20) >> 4) | (six & 0x01);
            const int col = (six >> 1) & 0x0F;
            substituted = (substituted << 4) | SBOX[box][row * 16 + col];
        }
        const uint32_t f = static_cast<uint32_t>(permute(substituted, 32, P));
        const uint32_t new_right = left ^ f;
        left = right;
        right = new_right;
    }
    return permute((static_cast<uint64_t>(right) << 32) | left, 64, FP);
}

uint64_t load_be64(const uint8_t *p)
{
    uint64_t v = 0;
    for (int i = 0; i < 8; i++) {
        v = (v << 8) | p[i];
    }
    return v;
}

void store_be64(uint64_t v, uint8_t *p)
{
    for (int i = 7; i >= 0; i--) {
        p[i] = static_cast<uint8_t>(v & 0xFF);
        v >>= 8;
    }
}

void put_size_be32(Bytes &packet, size_t size)
{
    packet[8] = static_cast<uint8_t>((size >> 24) & 0xFF);
    packet[9] = static_cast<uint8_t>((size >> 16) & 0xFF);
    packet[10] = static_cast<uint8_t>((size >> 8) & 0xFF);
    packet[11] = static_cast<uint8_t>(size & 0xFF);
}

Bytes concat(const Bytes &a, const Bytes &b)
{
    Bytes result = a;
    result.insert(result.end(), b.begin(), b.end());
    return result;
}

}  // namespace

Bytes encrypt_with_des(const Bytes &key, const Bytes &data)
{
    if (key.size() != 8) {
        throw std::invalid_argument("DES key must be 8 bytes");
    }
    const auto subkeys = des_subkeys(load_be64(key.data()));
    Bytes padded = data;
    padded.resize((data.size() + 7) / 8 * 8, 0x00);

    // CBC mode, IV = key
    uint64_t previous = load_be64(key.data());
    for (size_t i = 0; i < padded.size(); i += 8) {
        previous = des_encrypt_block(load_be64(&padded[i]) ^ previous, subkeys);
        store_be64(previous, &padded[i]);
    }
    return padded;
}

Bytes build_command_packet_header(uint8_t a0)
{
    Bytes packet(500, 0);
    packet[0] = a0;
    packet[2] = 0x1A;
    packet[3] = 0x6D;

    // Milliseconds since local midnight
    const auto now = std::chrono::system_clock::now();
    const std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    localtime_r(&t, &tm);
    tm.tm_hour = tm.tm_min = tm.tm_sec = 0;
    tm.tm_isdst = -1;
    const auto midnight = std::chrono::system_clock::from_time_t(std::mktime(&tm));
    const auto timestamp = static_cast<uint32_t>(
        std::chrono::duration_cast<std::chrono::milliseconds>(now - midnight).count());
    for (int i = 0; i < 4; i++) {
        packet[4 + i] = static_cast<uint8_t>((timestamp >> (8 * i)) & 0xFF);
    }
    return packet;
}

Bytes encrypt_command_packet(const Bytes &data)
{
    static const Bytes des_key = {'s', 'l', 'v', '3', 't', 'u', 'z', 'x'};
    const Bytes encrypted = encrypt_with_des(des_key, data);
    Bytes final_packet(512, 0);
    std::copy(encrypted.begin(), encrypted.begin() + std::min<size_t>(encrypted.size(), 512), final_packet.begin());
    final_packet[510] = 161;
    final_packet[511] = 26;
    return final_packet;
}

// ---------------------------------------------------------------------------------------------------------------------
// UsbDevice

UsbDevice::UsbDevice()
{
    libusb_context *ctx = nullptr;
    if (libusb_init(&ctx) != 0) {
        throw std::runtime_error("libusb could not be initialized");
    }
    context = ctx;

    libusb_device_handle *dev = nullptr;
    for (const auto &[pid, size]: product_ids()) {
        dev = libusb_open_device_with_vid_pid(ctx, VENDOR_ID, pid);
        if (dev) {
            product_id = pid;
            break;
        }
    }
    if (!dev) {
        libusb_exit(ctx);
        context = nullptr;
        throw std::runtime_error("USB device not found");
    }
    handle = dev;

    // Detach the kernel driver if needed, and select the configuration
    libusb_set_auto_detach_kernel_driver(dev, 1);
    libusb_config_descriptor *config = nullptr;
    if (libusb_get_config_descriptor(libusb_get_device(dev), 0, &config) == 0) {
        const int ret = libusb_set_configuration(dev, config->bConfigurationValue);
        if (ret != 0) {
            logger.warning("set_configuration() failed: {}", libusb_strerror(ret));
        }
        // Endpoints of interface 0
        for (int i = 0; i < config->bNumInterfaces; i++) {
            const libusb_interface &intf = config->interface[i];
            if (intf.num_altsetting < 1 || intf.altsetting[0].bInterfaceNumber != 0) {
                continue;
            }
            const libusb_interface_descriptor &alt = intf.altsetting[0];
            for (int e = 0; e < alt.bNumEndpoints; e++) {
                const libusb_endpoint_descriptor &ep = alt.endpoint[e];
                const bool interrupt = (ep.bmAttributes & 0x03) == LIBUSB_TRANSFER_TYPE_INTERRUPT;
                if ((ep.bEndpointAddress & LIBUSB_ENDPOINT_DIR_MASK) == LIBUSB_ENDPOINT_OUT && !ep_out) {
                    ep_out = ep.bEndpointAddress;
                    interrupt_out = interrupt;
                } else if ((ep.bEndpointAddress & LIBUSB_ENDPOINT_DIR_MASK) == LIBUSB_ENDPOINT_IN && !ep_in) {
                    ep_in = ep.bEndpointAddress;
                    interrupt_in = interrupt;
                }
            }
        }
        libusb_free_config_descriptor(config);
    }
    if (!ep_out || !ep_in) {
        throw std::runtime_error("Could not find USB endpoints");
    }
    const int ret = libusb_claim_interface(dev, 0);
    if (ret != 0) {
        throw std::runtime_error(std::string("Cannot claim USB interface 0: ") + libusb_strerror(ret));
    }
}

UsbDevice::~UsbDevice()
{
    if (handle) {
        libusb_release_interface(static_cast<libusb_device_handle *>(handle), 0);
        libusb_close(static_cast<libusb_device_handle *>(handle));
    }
    if (context) {
        libusb_exit(static_cast<libusb_context *>(context));
    }
}

std::optional<Bytes> UsbDevice::write_to_device(const Bytes &data, unsigned int timeout_ms)
{
    auto dev = static_cast<libusb_device_handle *>(handle);
    Bytes out = data;
    int transferred = 0;
    int ret = interrupt_out
                  ? libusb_interrupt_transfer(dev, ep_out, out.data(), static_cast<int>(out.size()), &transferred,
                                              timeout_ms)
                  : libusb_bulk_transfer(dev, ep_out, out.data(), static_cast<int>(out.size()), &transferred,
                                         timeout_ms);
    if (ret != 0) {
        logger.error("USB write error: {}", libusb_strerror(ret));
        return std::nullopt;
    }

    Bytes response(512);
    ret = interrupt_in ? libusb_interrupt_transfer(dev, ep_in, response.data(), 512, &transferred, timeout_ms)
                       : libusb_bulk_transfer(dev, ep_in, response.data(), 512, &transferred, timeout_ms);
    if (ret != 0) {
        logger.error("USB read error: {}", libusb_strerror(ret));
        return std::nullopt;
    }
    response.resize(static_cast<size_t>(transferred));
    read_flush();
    return response;
}

void UsbDevice::read_flush(int max_attempts)
{
    auto dev = static_cast<libusb_device_handle *>(handle);
    unsigned char buffer[512];
    for (int i = 0; i < max_attempts; i++) {
        int transferred = 0;
        const int ret = interrupt_in ? libusb_interrupt_transfer(dev, ep_in, buffer, 512, &transferred, 100)
                                     : libusb_bulk_transfer(dev, ep_in, buffer, 512, &transferred, 100);
        if (ret != 0) {
            break;  // timeout (nothing more to read) or error
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// Commands

std::optional<Bytes> send_sync_command(UsbDevice &dev)
{
    logger.debug("Sending Sync Command (ID 10)...");
    return dev.write_to_device(encrypt_command_packet(build_command_packet_header(10)));
}

std::optional<Bytes> send_brightness_command(UsbDevice &dev, int brightness)
{
    logger.debug("Sending Brightness Command (ID 14)... Brightness = {}", brightness);
    Bytes cmd_packet = build_command_packet_header(14);
    cmd_packet[8] = static_cast<uint8_t>(brightness);
    return dev.write_to_device(encrypt_command_packet(cmd_packet));
}

std::optional<Bytes> send_image(UsbDevice &dev, const Bytes &png_data)
{
    Bytes cmd_packet = build_command_packet_header(CMD_UPLOAD_PNG);
    put_size_be32(cmd_packet, png_data.size());
    return dev.write_to_device(concat(encrypt_command_packet(cmd_packet), png_data));
}

std::optional<Bytes> send_jpeg(UsbDevice &dev, const Bytes &jpeg_data)
{
    Bytes cmd_packet = build_command_packet_header(CMD_UPLOAD_JPEG);
    put_size_be32(cmd_packet, jpeg_data.size());
    return dev.write_to_device(concat(encrypt_command_packet(cmd_packet), jpeg_data));
}

std::optional<Bytes> clear_image(UsbDevice &dev)
{
    // Transparent 480x1920 PNG image
    Bytes img_data = {
        0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52, 0x00, 0x00,
        0x01, 0xe0, 0x00, 0x00, 0x07, 0x80, 0x08, 0x06, 0x00, 0x00, 0x00, 0x16, 0xf0, 0x84, 0xf5, 0x00, 0x00, 0x00,
        0x01, 0x73, 0x52, 0x47, 0x42, 0x00, 0xae, 0xce, 0x1c, 0xe9, 0x00, 0x00, 0x00, 0x04, 0x67, 0x41, 0x4d, 0x41,
        0x00, 0x00, 0xb1, 0x8f, 0x0b, 0xfc, 0x61, 0x05, 0x00, 0x00, 0x00, 0x09, 0x70, 0x48, 0x59, 0x73, 0x00, 0x00,
        0x0e, 0xc3, 0x00, 0x00, 0x0e, 0xc3, 0x01, 0xc7, 0x6f, 0xa8, 0x64, 0x00, 0x00, 0x0e, 0x0c, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x5e, 0xed, 0xc1, 0x01, 0x0d, 0x00, 0x00, 0x00, 0xc2, 0xa0, 0xf7, 0x4f, 0x6d, 0x0f, 0x07, 0x14,
        0x00, 0x00, 0x00, 0x00,
    };
    img_data.insert(img_data.end(), 3568, 0x00);
    const Bytes end = {0x00, 0xf0, 0x66, 0x4a, 0xc8, 0x00, 0x01, 0x11, 0x9d, 0x82, 0x0a, 0x00, 0x00, 0x00, 0x00, 0x49,
                       0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82};
    img_data.insert(img_data.end(), end.begin(), end.end());
    logger.debug("  Chunk Size: {} bytes", img_data.size());

    Bytes cmd_packet = build_command_packet_header(CMD_UPLOAD_PNG);
    put_size_be32(cmd_packet, img_data.size());
    return dev.write_to_device(concat(encrypt_command_packet(cmd_packet), img_data));
}

Bytes encode_jpeg_under_limit(const Image &image, size_t max_bytes, int quality, int subsampling)
{
    if (subsampling < -1 || subsampling > 2) {
        throw std::invalid_argument("subsampling must be one of: -1, 0, 1, 2");
    }
    const std::vector<int> subs = subsampling == -1 ? std::vector<int>{2, 1, 0} : std::vector<int>{subsampling};
    Bytes best;
    for (int sub: subs) {
        int q = quality;
        while (q >= 1) {
            Bytes data = image.encode_jpeg(q, sub);
            if (best.empty() || data.size() < best.size()) {
                best = data;
            }
            if (data.size() <= max_bytes) {
                return data;
            }
            q = q > 10 ? q - 5 : q - 1;
        }
    }
    throw std::runtime_error(std::format("Could not transcode JPEG under max_bytes: {} > {}", best.size(), max_bytes));
}

void send_pil_image_auto(UsbDevice &dev, const Image &image, size_t max_bytes)
{
    // First try PNG (preferred)
    const Bytes png = image.encode_png();
    if (png.size() <= max_bytes) {
        send_image(dev, png);
        return;
    }
    // Fallback to JPEG when over limit (default behavior)
    send_jpeg(dev, encode_jpeg_under_limit(image, max_bytes, 90, -1));
}

}  // namespace turing_usb

// ---------------------------------------------------------------------------------------------------------------------
// LcdCommTuringUSB

using namespace turing_usb;

LcdCommTuringUSB::LcdCommTuringUSB(const std::string &com_port, int display_width, int display_height,
                                   UpdateQueue *update_queue)
    : LcdComm(com_port, display_width, display_height, update_queue)
{
    dev = std::make_unique<UsbDevice>();
    for (const auto &[pid, size]: product_ids()) {
        if (pid == dev->pid()) {
            this->display_width = size.first;
            this->display_height = size.second;
        }
    }
    // Store the current screen state as an image that will be continuously updated and sent
    // (black instead of transparent: images are RGB)
    current_state = Image(get_width(), get_height(), {0, 0, 0});
}

LcdCommTuringUSB::~LcdCommTuringUSB() = default;

void LcdCommTuringUSB::InitializeComm()
{
    send_sync_command(*dev);
}

void LcdCommTuringUSB::Reset()
{
    // Do not enable the reset command for now on Turing USB models
}

void LcdCommTuringUSB::Clear()
{
    clear_image(*dev);
}

void LcdCommTuringUSB::ScreenOff()
{
    // Turing USB models do not implement a "screen off" command (that we know of): use SetBrightness(0) instead
    Clear();
    SetBrightness(0);
}

void LcdCommTuringUSB::ScreenOn()
{
    // Turing USB models do not implement a "screen off" command (that we know of): using SetBrightness() instead
    SetBrightness();
}

void LcdCommTuringUSB::SetBrightness(int level)
{
    if (level < 0 || level > 100) {
        throw std::invalid_argument("Brightness level must be [0-100]");
    }
    const int converted = static_cast<int>(level / 100.0 * 102);
    send_brightness_command(*dev, converted);
}

void LcdCommTuringUSB::SetOrientation(Orientation new_orientation)
{
    orientation = new_orientation;
    // Recreate new state with correct width/height now that screen orientation has changed
    current_state = Image(get_width(), get_height(), {0, 0, 0});
}

void LcdCommTuringUSB::DisplayPILImage(const Image &input, int x, int y, int image_width, int image_height)
{
    Image image = input;

    // If the image height/width isn't provided, use the native image size
    if (!image_height) {
        image_height = image.height();
    }
    if (!image_width) {
        image_width = image.width();
    }

    if (image.height() > get_height()) {
        image_height = get_height();
    }
    if (image.width() > get_width()) {
        image_width = get_width();
    }

    if (image_width != image.width() || image_height != image.height()) {
        image = image.crop(0, 0, image_width, image_height);
    }

    // The whole screen image is sent each time: serialize the updates (called from several threads without queue)
    std::lock_guard lock(update_queue_mutex);

    // Paste new image over existing screen state
    current_state.paste(image, x, y);

    // Rotate image before sending to screen: all images sent to the screen are in portrait mode
    Image base_image;
    if (orientation == Orientation::LANDSCAPE) {
        base_image = current_state.transpose(Image::Transpose::ROTATE_270);
    } else if (orientation == Orientation::REVERSE_LANDSCAPE) {
        base_image = current_state.transpose(Image::Transpose::ROTATE_90);
    } else if (orientation == Orientation::PORTRAIT) {
        base_image = current_state.transpose(Image::Transpose::ROTATE_180);
    } else {  // Orientation::REVERSE_PORTRAIT is initial screen orientation
        base_image = current_state;
    }

    // Send image data (auto JPEG fallback when payload exceeds device limit)
    send_pil_image_auto(*dev, base_image, MAX_IMAGE_PAYLOAD_DEFAULT);
}
