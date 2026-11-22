// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
//
// Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
// Copyright (C) 2022 Rollbacke
// Copyright (C) 2022 Ebag333
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

// C++ port of library/stats.py: collects the metrics (CPU/GPU/RAM/disk/net/date/uptime/custom/weather/ping) and
// displays them with the styles of the theme.
//
// In Python, the sensors are selected when the module is imported: in C++, stats::init() must be called once, after
// config::init() and before using the other functions.

#pragma once

#include <optional>
#include <string>
#include <vector>

#include <yaml-cpp/yaml.h>

namespace stats {

constexpr int DEFAULT_HISTORY_SIZE = 10;

// Select the sensors from HW_SENSORS in config.yaml. Exits the program if the value is not supported.
void init();

// Full path of a file of the theme, std::nullopt if no name
std::optional<std::string> get_theme_file_path(const std::string &name);

void display_themed_value(const YAML::Node &theme_data, const std::optional<std::string> &value, int min_size = 0,
                          const std::string &unit = "");
void display_themed_percent_value(const YAML::Node &theme_data, double value);
void display_themed_temperature_value(const YAML::Node &theme_data, double value);
void display_themed_progress_bar(const YAML::Node &theme_data, double value);

// value: numeric value of the bar, value_text: value as text, displayed in the center of the bar if SHOW_TEXT
// (custom_text replaces value_text + unit if provided)
void display_themed_radial_bar(const YAML::Node &theme_data, double value, const std::string &value_text,
                               int min_size = 0, const std::string &unit = "",
                               const std::optional<std::string> &custom_text = std::nullopt);
void display_themed_percent_radial_bar(const YAML::Node &theme_data, double value);
void display_themed_temperature_radial_bar(const YAML::Node &theme_data, double value);
void display_themed_line_graph(const YAML::Node &theme_data, const std::vector<double> &values);

// Store the value in the list of last values (oldest value removed), used for line graphs
void save_last_value(double value, std::vector<double> &last_values, int history_size);
std::vector<double> last_values_list(int size);

// Same as psutil bytes2human(): human-readable size, e.g. 1.2K, with the given std::format format for the value
std::string bytes2human(double n, const std::string &value_format = "{:.1f}", const std::string &suffix = "");

class CPU
{
public:
    static void percentage();
    static void frequency();
    static void load();
    static void temperature();
    static void fan_speed();
};

class Gpu
{
public:
    static void stats();
    static bool is_available();
};

class Memory
{
public:
    static void stats();
};

class Disk
{
public:
    static void stats();
};

class Net
{
public:
    static void stats();
};

class Date
{
public:
    static void stats();
};

class SystemUptime
{
public:
    static void stats();
};

class Custom
{
public:
    static void stats();
};

class Weather
{
public:
    static void stats();
};

class Ping
{
public:
    static void stats();
};

}  // namespace stats
