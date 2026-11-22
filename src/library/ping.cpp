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

// ICMP echo ("ping"), replacing the ping3 Python library used by the Python code.

#include "library/ping.h"

#include <atomic>
#include <chrono>
#include <cstring>

#include <netdb.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/ip_icmp.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include "library/log.h"

namespace {

uint16_t checksum(const uint8_t *data, size_t size)
{
    uint32_t sum = 0;
    for (size_t i = 0; i + 1 < size; i += 2) {
        sum += static_cast<uint32_t>(data[i] << 8 | data[i + 1]);
    }
    if (size % 2) {
        sum += static_cast<uint32_t>(data[size - 1] << 8);
    }
    while (sum >> 16) {
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    return static_cast<uint16_t>(~sum);
}

std::atomic<uint16_t> sequence = 0;

}  // namespace

std::optional<double> ping(const std::string &dest_addr, double timeout_s)
{
    addrinfo hints{};
    hints.ai_family = AF_INET;
    addrinfo *res = nullptr;
    if (getaddrinfo(dest_addr.c_str(), nullptr, &hints, &res) != 0 || !res) {
        logger.debug("Ping: cannot resolve host {}", dest_addr);
        return std::nullopt;
    }
    sockaddr_in addr{};
    std::memcpy(&addr, res->ai_addr, sizeof(addr));
    freeaddrinfo(res);

    // Unprivileged ICMP socket first, raw socket otherwise
    bool raw = false;
    int fd = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, IPPROTO_ICMP);
    if (fd < 0) {
        fd = ::socket(AF_INET, SOCK_RAW | SOCK_CLOEXEC, IPPROTO_ICMP);
        raw = true;
    }
    if (fd < 0) {
        logger.debug("Ping: cannot create ICMP socket: {}", std::strerror(errno));
        return std::nullopt;
    }

    const uint16_t id = static_cast<uint16_t>(::getpid());
    const uint16_t seq = sequence++;
    uint8_t packet[sizeof(icmphdr) + 32] = {};
    auto *header = reinterpret_cast<icmphdr *>(packet);
    header->type = ICMP_ECHO;
    header->code = 0;
    header->un.echo.id = htons(id);
    header->un.echo.sequence = htons(seq);
    for (size_t i = sizeof(icmphdr); i < sizeof(packet); i++) {
        packet[i] = static_cast<uint8_t>('Q');
    }
    header->checksum = htons(checksum(packet, sizeof(packet)));

    const auto start = std::chrono::steady_clock::now();
    const auto deadline = start + std::chrono::duration<double>(timeout_s);
    std::optional<double> result;
    if (::sendto(fd, packet, sizeof(packet), 0, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0) {
        logger.debug("Ping: cannot send to {}: {}", dest_addr, std::strerror(errno));
        ::close(fd);
        return std::nullopt;
    }

    while (true) {
        const auto remaining =
            std::chrono::duration_cast<std::chrono::milliseconds>(deadline - std::chrono::steady_clock::now());
        if (remaining.count() <= 0) {
            break;  // timeout
        }
        pollfd pfd{fd, POLLIN, 0};
        if (::poll(&pfd, 1, static_cast<int>(remaining.count())) <= 0) {
            continue;
        }
        uint8_t buffer[1500];
        const ssize_t n = ::recv(fd, buffer, sizeof(buffer), 0);
        if (n <= 0) {
            continue;
        }
        size_t offset = 0;
        if (raw) {
            // Raw sockets receive the IP header
            offset = static_cast<size_t>((buffer[0] & 0x0F) * 4);
        }
        if (static_cast<size_t>(n) < offset + sizeof(icmphdr)) {
            continue;
        }
        const auto *reply = reinterpret_cast<const icmphdr *>(buffer + offset);
        // For unprivileged ICMP sockets, the kernel sets the identifier: only check the sequence number
        if (reply->type == ICMP_ECHOREPLY && ntohs(reply->un.echo.sequence) == seq &&
            (!raw || ntohs(reply->un.echo.id) == id)) {
            result = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
            break;
        }
    }
    ::close(fd);
    return result;
}
