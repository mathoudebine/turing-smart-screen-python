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

// C++ port of library/config.py: loads config.yaml, then the theme res/themes/<THEME>/theme.yaml with fallback to
// the default values of res/themes/default.yaml.
//
// In Python, the configuration and theme are loaded when the module is imported: in C++, config::init() must be
// called once at program start, before using anything else from the library.

#pragma once

#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

#include <yaml-cpp/yaml.h>

#include "library/lcd/lcd_comm.h"

namespace config {

// Directory containing config.yaml and res/ (the repository root)
extern std::filesystem::path MAIN_DIRECTORY;
// Fonts directory, ending with '/'
extern std::string FONTS_DIR;
extern YAML::Node CONFIG_DATA;
extern YAML::Node THEME_DEFAULT;
extern YAML::Node THEME_DATA;

// Queue containing the serial requests to send to the screen
extern UpdateQueue update_queue;

// Directory containing config.yaml and res/: the executable directory or one of its parents (programs are built
// into build/bin/), otherwise the current directory
std::filesystem::path find_main_directory();

// Throws YAML::Exception if the file cannot be loaded or parsed
YAML::Node load_yaml(const std::filesystem::path &configfile);

// Recursively supply default values into a map of maps of maps ...
void copy_default(const YAML::Node &default_values, YAML::Node theme);

// A value to write in config.yaml: section ("config" or "display"), key, and value already formatted as YAML
// (use yaml_scalar() for strings)
struct YamlUpdate
{
    std::string section;
    std::string key;
    std::string value;
};

// String formatted as a YAML scalar: plain if possible, double-quoted otherwise (empty string, special characters,
// values that YAML would read as another type like "true" or "null")
std::string yaml_scalar(const std::string &value);

// Update the values in the YAML text of a configuration file, keeping everything else unchanged (comments, order,
// formatting), like ruamel.yaml does in Python. Missing keys are added at the end of their section, missing sections
// at the end of the text.
std::string update_yaml_text(const std::string &text, const std::vector<YamlUpdate> &updates);

// Same as update_yaml_text() on a file. Throws std::runtime_error if the file cannot be read or written.
void update_yaml_file(const std::filesystem::path &path, const std::vector<YamlUpdate> &updates);

// Load the theme selected in config.yaml into THEME_DATA. Exits the program if the theme cannot be loaded.
void load_theme();

// Check if theme is compatible with hardware revision. Exits the program if not.
void check_theme_compatible(const std::string &display_size);

// Load config.yaml, default.yaml and the theme. Exits the program on error.
void init();

// Value of node[key] converted to T, or default_value if the key is missing or empty (like Python dict.get()).
// Throws std::runtime_error if the value cannot be converted to T.
template<typename T>
T get(const YAML::Node &node, const std::string &key, const T &default_value)
{
    if (!node.IsDefined() || !node.IsMap()) {
        return default_value;
    }
    const YAML::Node value = node[key];
    if (!value.IsDefined() || value.IsNull()) {
        return default_value;
    }
    try {
        return value.as<T>();
    } catch (const YAML::Exception &) {
        throw std::runtime_error("Invalid value for '" + key + "': '" + YAML::Dump(value) + "'");
    }
}

// Color value of node[key] (see parse_color()), or default_value if the key is missing or empty.
// Throws std::invalid_argument if the color cannot be parsed.
RGBColor get_color(const YAML::Node &node, const std::string &key, RGBColor default_value);

// Overload so that string literals can be used as default value
inline std::string get(const YAML::Node &node, const std::string &key, const char *default_value)
{
    return get<std::string>(node, key, std::string(default_value));
}

}  // namespace config
