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

// Linux serial port (termios), replacing the subset of pyserial used by the Python code.
// No Python counterpart: this file replaces a Python dependency.

#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

// Error opening/reading/writing the serial port (like serial.SerialException)
class SerialException : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};

// Timeout writing to the serial port (like serial.SerialTimeoutException)
class SerialTimeoutException : public SerialException
{
public:
    using SerialException::SerialException;
};

class SerialPort
{
public:
    // Open the port in raw 8N1 mode. Throws SerialException on error.
    // timeout: read/write timeout in seconds; rtscts: hardware flow control
    SerialPort(const std::string &port, int baudrate, double timeout, bool rtscts);
    ~SerialPort();

    SerialPort(const SerialPort &) = delete;
    SerialPort &operator=(const SerialPort &) = delete;

    void close();

    bool is_open() const { return fd >= 0; }

    const std::string &port() const { return port_name; }

    // Write all data. Throws SerialTimeoutException / SerialException
    void write(const std::vector<uint8_t> &data);
    void write(const uint8_t *data, size_t size);

    // Read up to size bytes, returns less if the timeout expires
    std::vector<uint8_t> read(size_t size);

    // Read until the timeout expires
    std::vector<uint8_t> readall();

    // Wait until all data is written
    void flush();

    // Discard data received and not read yet
    void reset_input_buffer();

private:
    bool wait(bool for_write, double timeout_s);

    std::string port_name;
    double timeout;
    int fd = -1;
};

// Information about a serial port, like serial.tools.list_ports_common.ListPortInfo
struct ListPortInfo
{
    std::string device;         // e.g. "/dev/ttyACM0"
    std::string name;           // e.g. "ttyACM0"
    std::string serial_number;  // USB serial number, empty if unknown
    std::optional<uint16_t> vid;  // USB vendor ID, if USB device
    std::optional<uint16_t> pid;  // USB product ID, if USB device
};

// List the serial ports of the system (like serial.tools.list_ports.comports())
std::vector<ListPortInfo> comports();
