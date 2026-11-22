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

#include "library/log.h"

#include <clocale>
#include <ctime>
#include <iostream>

namespace {
// Log in text file, max 1MB: the file is truncated when it gets bigger
constexpr std::streamoff LOG_FILE_MAX_BYTES = 1000000;
constexpr const char *LOG_FILE = "log.log";

const char *level_name(LogLevel level)
{
    switch (level) {
        case LogLevel::DEBUG: return "DEBUG";
        case LogLevel::INFO: return "INFO";
        case LogLevel::WARNING: return "WARNING";
        case LogLevel::ERROR: return "ERROR";
    }
    return "?";
}
}

Logger logger;

Logger::Logger()
{
    // Use current locale for date/time formatting in logs. Numbers keep the "C" locale, so that number
    // parsing/formatting in the program does not depend on the user locale.
    std::setlocale(LC_ALL, "");
    std::setlocale(LC_NUMERIC, "C");

    file.open(LOG_FILE, std::ios::app);
}

void Logger::setLevel(LogLevel new_level)
{
    std::lock_guard lock(mutex);
    level = new_level;
}

void Logger::log(LogLevel msg_level, std::string_view message)
{
    std::lock_guard lock(mutex);
    if (msg_level < level) {
        return;
    }

    // Same format as Python: "%(asctime)s [%(levelname)s] %(message)s" with datefmt '%x %X'
    char date[64];
    const std::time_t now = std::time(nullptr);
    std::tm tm{};
    localtime_r(&now, &tm);
    std::strftime(date, sizeof(date), "%x %X", &tm);

    const std::string line = std::format("{} [{}] {}\n", date, level_name(msg_level), message);

    // Log also in console
    std::cerr << line << std::flush;

    if (file.is_open()) {
        if (file.tellp() > LOG_FILE_MAX_BYTES) {
            file.close();
            file.open(LOG_FILE, std::ios::trunc);
        }
        file << line << std::flush;
    }
}
