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

// C++ port of library/log.py: logging to the console and to the log.log text file.
//
// Usage: logger.info("Loading theme {} from {}", name, path);   (std::format syntax)

#pragma once

#include <format>
#include <fstream>
#include <mutex>
#include <string>
#include <string_view>

enum class LogLevel { DEBUG = 10, INFO = 20, WARNING = 30, ERROR = 40 };

class Logger
{
public:
    Logger();

    // Lowest level of the messages that are logged (DEBUG by default: print all messages)
    void setLevel(LogLevel level);

    void log(LogLevel level, std::string_view message);

    template<typename... Args>
    void debug(std::format_string<Args...> fmt, Args &&... args)
    {
        log(LogLevel::DEBUG, std::format(fmt, std::forward<Args>(args)...));
    }

    template<typename... Args>
    void info(std::format_string<Args...> fmt, Args &&... args)
    {
        log(LogLevel::INFO, std::format(fmt, std::forward<Args>(args)...));
    }

    template<typename... Args>
    void warning(std::format_string<Args...> fmt, Args &&... args)
    {
        log(LogLevel::WARNING, std::format(fmt, std::forward<Args>(args)...));
    }

    template<typename... Args>
    void error(std::format_string<Args...> fmt, Args &&... args)
    {
        log(LogLevel::ERROR, std::format(fmt, std::forward<Args>(args)...));
    }

private:
    std::mutex mutex;
    LogLevel level = LogLevel::DEBUG;
    std::ofstream file;
};

extern Logger logger;
