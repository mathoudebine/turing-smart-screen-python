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

#include "library/lcd/serial_port.h"

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>

#include <fcntl.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>

namespace fs = std::filesystem;

namespace {

speed_t to_speed(int baudrate)
{
    switch (baudrate) {
        case 9600: return B9600;
        case 19200: return B19200;
        case 38400: return B38400;
        case 57600: return B57600;
        case 115200: return B115200;
        case 230400: return B230400;
        case 460800: return B460800;
        case 921600: return B921600;
        case 1000000: return B1000000;
        case 2000000: return B2000000;
        default: throw SerialException("Unsupported baudrate " + std::to_string(baudrate));
    }
}

std::string read_sysfs(const fs::path &path)
{
    std::ifstream file(path);
    std::string value;
    std::getline(file, value);
    return value;
}

}  // namespace

SerialPort::SerialPort(const std::string &port, int baudrate, double timeout_s, bool rtscts)
    : port_name(port.find('/') == std::string::npos ? "/dev/" + port : port), timeout(timeout_s)
{
    // A port name without directory (e.g. "ttyACM0", as written by the Python configuration program) is in /dev
    fd = ::open(port_name.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        throw SerialException("could not open port " + port + ": " + std::strerror(errno));
    }

    // Exclusive access, like pyserial does on POSIX
    if (::ioctl(fd, TIOCEXCL) != 0) {
        const int err = errno;
        ::close(fd);
        fd = -1;
        throw SerialException("could not lock port " + port + ": " + std::strerror(err));
    }

    termios tty{};
    if (::tcgetattr(fd, &tty) != 0) {
        const int err = errno;
        ::close(fd);
        fd = -1;
        throw SerialException("could not configure port " + port + ": " + std::strerror(err));
    }
    ::cfmakeraw(&tty);
    tty.c_cflag |= CLOCAL | CREAD;
    tty.c_cflag &= ~(CSTOPB | PARENB);
    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;
    if (rtscts) {
        tty.c_cflag |= CRTSCTS;
    } else {
        tty.c_cflag &= ~CRTSCTS;
    }
    tty.c_cc[VMIN] = 0;
    tty.c_cc[VTIME] = 0;
    const speed_t speed = to_speed(baudrate);
    ::cfsetispeed(&tty, speed);
    ::cfsetospeed(&tty, speed);
    if (::tcsetattr(fd, TCSANOW, &tty) != 0) {
        const int err = errno;
        ::close(fd);
        fd = -1;
        throw SerialException("could not configure port " + port + ": " + std::strerror(err));
    }
    ::tcflush(fd, TCIFLUSH);
}

SerialPort::~SerialPort()
{
    close();
}

void SerialPort::close()
{
    if (fd >= 0) {
        ::close(fd);
        fd = -1;
    }
}

bool SerialPort::wait(bool for_write, double timeout_s)
{
    pollfd pfd{fd, static_cast<short>(for_write ? POLLOUT : POLLIN), 0};
    const int ret = ::poll(&pfd, 1, static_cast<int>(timeout_s * 1000));
    if (ret < 0) {
        if (errno == EINTR) {
            return false;
        }
        throw SerialException(std::string("poll failed: ") + std::strerror(errno));
    }
    if (ret > 0 && (pfd.revents & (POLLERR | POLLHUP | POLLNVAL))) {
        throw SerialException("device reports readiness to " + std::string(for_write ? "write" : "read") +
                              " but returned no data (device disconnected or multiple access on port?)");
    }
    return ret > 0;
}

void SerialPort::write(const std::vector<uint8_t> &buffer)
{
    const uint8_t *data = buffer.data();
    const size_t size = buffer.size();
    if (fd < 0) {
        throw SerialException("Attempting to use a port that is not open");
    }
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(timeout);
    size_t written = 0;
    while (written < size) {
        const ssize_t n = ::write(fd, data + written, size - written);
        if (n > 0) {
            written += static_cast<size_t>(n);
            continue;
        }
        if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
            throw SerialException(std::string("write failed: ") + std::strerror(errno));
        }
        const double remaining = std::chrono::duration<double>(deadline - std::chrono::steady_clock::now()).count();
        if (remaining <= 0 || !wait(true, remaining)) {
            if (std::chrono::steady_clock::now() >= deadline) {
                throw SerialTimeoutException("Write timeout");
            }
        }
    }
}

std::vector<uint8_t> SerialPort::read(size_t size)
{
    if (fd < 0) {
        throw SerialException("Attempting to use a port that is not open");
    }
    std::vector<uint8_t> result;
    result.reserve(size);
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(timeout);
    while (result.size() < size) {
        const double remaining = std::chrono::duration<double>(deadline - std::chrono::steady_clock::now()).count();
        if (remaining <= 0 || !wait(false, remaining)) {
            break;
        }
        uint8_t buffer[4096];
        const ssize_t n = ::read(fd, buffer, std::min(sizeof(buffer), size - result.size()));
        if (n > 0) {
            result.insert(result.end(), buffer, buffer + n);
        } else if (n == 0) {
            throw SerialException("device reports readiness to read but returned no data "
                                  "(device disconnected or multiple access on port?)");
        } else if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
            throw SerialException(std::string("read failed: ") + std::strerror(errno));
        }
    }
    return result;
}

std::vector<uint8_t> SerialPort::readall()
{
    std::vector<uint8_t> result;
    while (true) {
        const auto chunk = read(4096);
        if (chunk.empty()) {
            break;
        }
        result.insert(result.end(), chunk.begin(), chunk.end());
    }
    return result;
}

void SerialPort::flush()
{
    if (fd >= 0) {
        ::tcdrain(fd);
    }
}

size_t SerialPort::in_waiting()
{
    int count = 0;
    if (fd < 0 || ::ioctl(fd, FIONREAD, &count) != 0) {
        return 0;
    }
    return static_cast<size_t>(count);
}

void SerialPort::reset_input_buffer()
{
    if (fd >= 0) {
        ::tcflush(fd, TCIFLUSH);
    }
}

std::vector<ListPortInfo> comports()
{
    std::vector<ListPortInfo> ports;
    const fs::path tty_class("/sys/class/tty");
    std::error_code ec;
    if (!fs::exists(tty_class, ec)) {
        return ports;
    }

    for (const auto &entry: fs::directory_iterator(tty_class, ec)) {
        const std::string name = entry.path().filename().string();
        // Same device name patterns as pyserial on Linux
        static const char *patterns[] = {"ttyS", "ttyUSB", "ttyXRUSB", "ttyACM", "ttyAMA", "rfcomm", "ttyAP",
                                         "ttyGS"};
        if (std::none_of(std::begin(patterns), std::end(patterns),
                         [&](const char *p) { return name.rfind(p, 0) == 0; })) {
            continue;
        }

        // Only keep devices with a driver (like pyserial: ignores ttyS* placeholders without hardware)
        const fs::path device_path = entry.path() / "device";
        if (!fs::exists(device_path, ec)) {
            continue;
        }

        ListPortInfo info;
        info.device = "/dev/" + name;
        info.name = name;

        // USB devices: walk up the sysfs tree to the USB device holding idVendor/idProduct
        fs::path p = fs::canonical(device_path, ec);
        for (int depth = 0; !ec && depth < 6 && p.has_parent_path() && p != p.root_path(); depth++) {
            if (fs::exists(p / "idVendor", ec) && fs::exists(p / "idProduct", ec)) {
                try {
                    info.vid = static_cast<uint16_t>(std::stoi(read_sysfs(p / "idVendor"), nullptr, 16));
                    info.pid = static_cast<uint16_t>(std::stoi(read_sysfs(p / "idProduct"), nullptr, 16));
                } catch (const std::exception &) {
                    info.vid.reset();
                    info.pid.reset();
                }
                info.serial_number = read_sysfs(p / "serial");
                break;
            }
            p = p.parent_path();
        }

        ports.push_back(info);
    }

    std::sort(ports.begin(), ports.end(), [](const auto &a, const auto &b) { return a.device < b.device; });
    return ports;
}
