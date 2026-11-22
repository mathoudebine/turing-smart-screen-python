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

// Tests of library/lcd/lcd_comm_turing_usb protocol functions (the USB device itself cannot be tested without screen)

#include <string>

#include <gtest/gtest.h>

#include "library/lcd/lcd_comm_turing_usb.h"
#include "serial_mock.h"

namespace {
std::string to_hex(const Bytes &data)
{
    static const char *hex = "0123456789abcdef";
    std::string result;
    for (uint8_t b: data) {
        result.push_back(hex[b >> 4]);
        result.push_back(hex[b & 0xF]);
    }
    return result;
}
}  // namespace

TEST(TuringUSB, DesTestVector)
{
    // FIPS 81 / NBS test vector (ECB = CBC on one block with a zero IV): key 133457799BBCDFF1,
    // plaintext 0123456789ABCDEF -> ciphertext 85E813540F0AB405. CBC with IV = key: XOR the IV first.
    const Bytes key = {0x13, 0x34, 0x57, 0x79, 0x9B, 0xBC, 0xDF, 0xF1};
    Bytes plaintext = {0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF};
    for (int i = 0; i < 8; i++) {
        plaintext[i] ^= key[i];
    }
    EXPECT_EQ(to_hex(turing_usb::encrypt_with_des(key, plaintext)), "85e813540f0ab405");
}

TEST(TuringUSB, EncryptCommandPacket)
{
    // Same output as the Python encrypt_command_packet() (pycryptodome DES) for this data
    Bytes data(500);
    for (int i = 0; i < 500; i++) {
        data[i] = static_cast<uint8_t>(i * 7 + 3);
    }
    const Bytes packet = turing_usb::encrypt_command_packet(data);
    ASSERT_EQ(packet.size(), 512u);
    EXPECT_EQ(packet[510], 161);
    EXPECT_EQ(packet[511], 26);
    EXPECT_EQ(fnv1a(to_hex(packet)), 0x91bbe7435ec87d53ULL);
}

TEST(TuringUSB, CommandPacketHeader)
{
    const Bytes packet = turing_usb::build_command_packet_header(14);
    ASSERT_EQ(packet.size(), 500u);
    EXPECT_EQ(packet[0], 14);
    EXPECT_EQ(packet[2], 0x1A);
    EXPECT_EQ(packet[3], 0x6D);
    const uint32_t timestamp = packet[4] | (packet[5] << 8) | (packet[6] << 16) | (static_cast<uint32_t>(packet[7]) << 24);
    EXPECT_LT(timestamp, 24u * 3600 * 1000);  // milliseconds since midnight
}

TEST(TuringUSB, JpegUnderLimit)
{
    const Image image = generate_sample_image(480, 800);
    const Bytes jpeg = turing_usb::encode_jpeg_under_limit(image, 20000);
    EXPECT_LE(jpeg.size(), 20000u);
    ASSERT_GE(jpeg.size(), 2u);
    EXPECT_EQ(jpeg[0], 0xFF);  // JPEG signature
    EXPECT_EQ(jpeg[1], 0xD8);
    EXPECT_THROW(turing_usb::encode_jpeg_under_limit(image, 10), std::runtime_error);
}
