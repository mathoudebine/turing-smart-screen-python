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

// C++ port of library/lcd/lcd_simulated.py: simulated display, writing to a file (screencap.png) instead of a serial
// port.

#include "library/lcd/lcd_simulated.h"

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <stdexcept>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include "library/log.h"

namespace {

constexpr const char *TMP_FILE = "tmp";

void send_all(int fd, const std::string &data)
{
    size_t sent = 0;
    while (sent < data.size()) {
        const ssize_t n = ::send(fd, data.data() + sent, data.size() - sent, MSG_NOSIGNAL);
        if (n <= 0) {
            return;
        }
        sent += static_cast<size_t>(n);
    }
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// SimulatedLcdWebServer

SimulatedLcdWebServer::SimulatedLcdWebServer(const std::string &host, int port)
{
    server_fd = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (server_fd < 0) {
        throw std::runtime_error(std::strerror(errno));
    }
    const int reuse = 1;
    ::setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<uint16_t>(port));
    ::inet_pton(AF_INET, host == "localhost" ? "127.0.0.1" : host.c_str(), &addr.sin_addr);
    if (::bind(server_fd, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) != 0 || ::listen(server_fd, 8) != 0) {
        const int err = errno;
        ::close(server_fd);
        server_fd = -1;
        throw std::runtime_error(std::strerror(err));
    }

    thread = std::thread(&SimulatedLcdWebServer::serve_forever, this);
}

SimulatedLcdWebServer::~SimulatedLcdWebServer()
{
    shutdown();
}

void SimulatedLcdWebServer::shutdown()
{
    stopping = true;
    if (thread.joinable()) {
        thread.join();
    }
    if (server_fd >= 0) {
        ::close(server_fd);
        server_fd = -1;
    }
}

void SimulatedLcdWebServer::serve_forever()
{
    while (!stopping) {
        // Wake up regularly to check if the server must stop
        pollfd pfd{server_fd, POLLIN, 0};
        if (::poll(&pfd, 1, 250) <= 0) {
            continue;
        }
        const int client_fd = ::accept4(server_fd, nullptr, nullptr, SOCK_CLOEXEC);
        if (client_fd < 0) {
            continue;
        }
        handle_client(client_fd);
        ::close(client_fd);
    }
}

void SimulatedLcdWebServer::handle_client(int client_fd)
{
    // Read the request line: "GET <path> HTTP/1.x"
    pollfd pfd{client_fd, POLLIN, 0};
    if (::poll(&pfd, 1, 1000) <= 0) {
        return;
    }
    char buffer[2048];
    const ssize_t n = ::recv(client_fd, buffer, sizeof(buffer) - 1, 0);
    if (n <= 0) {
        return;
    }
    buffer[n] = '\0';
    std::istringstream request(buffer);
    std::string method, path;
    request >> method >> path;

    if (path == "/") {
        const std::string screenshot = SCREENSHOT_FILE;
        const std::string body = "<img src=\"" + screenshot + "\" id=\"myImage\" />"
                                 "<script>"
                                 "setInterval(function() {"
                                 "    var myImageElement = document.getElementById('myImage');"
                                 "    myImageElement.src = '" + screenshot + "?rand=' + Math.random();"
                                 "}, 250);"
                                 "</script>";
        send_all(client_fd, "HTTP/1.0 200 OK\r\nContent-type: text/html\r\nContent-Length: " +
                            std::to_string(body.size()) + "\r\n\r\n" + body);
    } else if (path.rfind(std::string("/") + SCREENSHOT_FILE, 0) == 0) {
        std::ifstream file(SCREENSHOT_FILE, std::ios::binary);
        const std::string body((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        send_all(client_fd, "HTTP/1.0 200 OK\r\nContent-type: image/png\r\nContent-Length: " +
                            std::to_string(body.size()) + "\r\n\r\n" + body);
    } else {
        send_all(client_fd, "HTTP/1.0 404 Not Found\r\nContent-Length: 0\r\n\r\n");
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// LcdSimulated

LcdSimulated::LcdSimulated(const std::string &com_port, int display_width, int display_height,
                           UpdateQueue *update_queue)
    : LcdComm(com_port, display_width, display_height, update_queue)
{
    screen_image = Image(get_width(), get_height(), {255, 255, 255});
    save_screenshot();
    orientation = Orientation::PORTRAIT;

    try {
        webServer = std::make_unique<SimulatedLcdWebServer>("localhost", WEBSERVER_PORT);
        logger.debug("To see your simulated screen, open http://{}:{} in a browser", "localhost", WEBSERVER_PORT);
    } catch (const std::runtime_error &) {
        logger.error("Error starting webserver! An instance might already be running on port {}.", WEBSERVER_PORT);
    }
}

LcdSimulated::~LcdSimulated()
{
    LcdSimulated::closeSerial();
}

std::optional<std::string> LcdSimulated::auto_detect_com_port()
{
    return std::nullopt;
}

void LcdSimulated::closeSerial()
{
    if (webServer) {
        logger.debug("Shutting down web server");
        webServer->shutdown();
        webServer.reset();
    }
}

void LcdSimulated::InitializeComm()
{
}

void LcdSimulated::Reset()
{
}

void LcdSimulated::Clear()
{
    SetOrientation(orientation);
}

void LcdSimulated::ScreenOff()
{
}

void LcdSimulated::ScreenOn()
{
}

void LcdSimulated::SetBrightness(int)
{
}

void LcdSimulated::SetBackplateLedColor(RGBColor)
{
}

void LcdSimulated::SetOrientation(Orientation new_orientation)
{
    orientation = new_orientation;
    // Just draw the screen again with the new width/height based on orientation
    std::lock_guard lock(update_queue_mutex);
    screen_image = Image(get_width(), get_height(), {255, 255, 255});
    save_screenshot();
}

void LcdSimulated::DisplayPILImage(const Image &input, int x, int y, int image_width, int image_height)
{
    Image image = input;

    // If the image height/width isn't provided, use the native image size
    if (!image_height) {
        image_height = image.height();
    }
    if (!image_width) {
        image_width = image.width();
    }

    // If image is bigger than display, crop it
    if (image.height() > get_height()) {
        image_height = get_height();
    }
    if (image.width() > get_width()) {
        image_width = get_width();
    }

    if (image_width != image.width() || image_height != image.height()) {
        image = image.crop(0, 0, image_width, image_height);
    }

    if (x > get_width()) {
        throw std::invalid_argument("Image X coordinate must be <= display width");
    }
    if (y > get_height()) {
        throw std::invalid_argument("Image Y coordinate must be <= display height");
    }
    if (image_height <= 0) {
        throw std::invalid_argument("Image height must be > 0");
    }
    if (image_width <= 0) {
        throw std::invalid_argument("Image width must be > 0");
    }

    std::lock_guard lock(update_queue_mutex);
    screen_image.paste(image, x, y);
    save_screenshot();
}

void LcdSimulated::save_screenshot()
{
    screen_image.save(TMP_FILE);
    if (std::rename(TMP_FILE, SCREENSHOT_FILE) != 0) {
        logger.error("Cannot write {}: {}", SCREENSHOT_FILE, std::strerror(errno));
    }
}
