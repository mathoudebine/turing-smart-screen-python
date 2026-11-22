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

// C++ port of library/config.py

#include "library/config.h"

#include <cstdlib>

#include "library/log.h"

namespace fs = std::filesystem;

namespace config {

fs::path MAIN_DIRECTORY;
std::string FONTS_DIR;
YAML::Node CONFIG_DATA;
YAML::Node THEME_DEFAULT;
YAML::Node THEME_DATA;
UpdateQueue update_queue;

namespace {

bool is_main_directory(const fs::path &dir)
{
    std::error_code ec;
    return fs::is_regular_file(dir / "config.yaml", ec) && fs::is_directory(dir / "res" / "themes", ec);
}

// The programs are built into build/bin/: look for config.yaml and res/ in the executable directory and its parents,
// then in the current directory
fs::path find_main_directory()
{
    std::error_code ec;
    const fs::path exe = fs::read_symlink("/proc/self/exe", ec);
    if (!ec) {
        for (fs::path dir = exe.parent_path(); !dir.empty(); dir = dir.parent_path()) {
            if (is_main_directory(dir)) {
                return dir;
            }
            if (dir == dir.root_path()) {
                break;
            }
        }
    }
    return fs::current_path();
}

}  // namespace

YAML::Node load_yaml(const fs::path &configfile)
{
    return YAML::LoadFile(configfile.string());
}

void copy_default(const YAML::Node &default_values, YAML::Node theme)
{
    for (const auto &item: default_values) {
        const std::string key = item.first.as<std::string>();
        const YAML::Node &value = item.second;
        YAML::Node theme_value = theme[key];
        if (!theme_value.IsDefined() || theme_value.IsNull()) {
            theme[key] = YAML::Clone(value);
        } else if (value.IsMap() && theme_value.IsMap()) {
            copy_default(value, theme_value);
        }
    }
}

void load_theme()
{
    try {
        const std::string theme_name = CONFIG_DATA["config"]["THEME"].as<std::string>();
        const fs::path theme_path = fs::path("res/themes") / theme_name;
        logger.info("Loading theme {} from {}", theme_name, (theme_path / "theme.yaml").string());
        THEME_DATA = load_yaml(MAIN_DIRECTORY / theme_path / "theme.yaml");
        if (!THEME_DATA.IsMap()) {
            throw std::runtime_error("theme.yaml is not a map");
        }
        THEME_DATA["PATH"] = (MAIN_DIRECTORY / theme_path).string() + "/";
    } catch (const std::exception &e) {
        logger.error("Theme not found or contains errors! ({})", e.what());
        std::_Exit(1);
    }

    copy_default(THEME_DEFAULT, THEME_DATA);
}

void check_theme_compatible(const std::string &display_size)
{
    // Check if theme is compatible with hardware revision
    if (display_size != get(THEME_DATA["display"], "DISPLAY_SIZE", "3.5\"")) {
        logger.error("The selected theme {} is not compatible with your display revision {}",
                     CONFIG_DATA["config"]["THEME"].as<std::string>(),
                     CONFIG_DATA["display"]["REVISION"].as<std::string>());
        std::_Exit(1);
    }
}

RGBColor get_color(const YAML::Node &node, const std::string &key, RGBColor default_value)
{
    if (!node.IsDefined() || !node.IsMap()) {
        return default_value;
    }
    const YAML::Node value = node[key];
    if (!value.IsDefined() || value.IsNull()) {
        return default_value;
    }
    return parse_color(value);
}

void init()
{
    MAIN_DIRECTORY = find_main_directory();
    FONTS_DIR = (MAIN_DIRECTORY / "res" / "fonts").string() + "/";

    try {
        CONFIG_DATA = load_yaml(MAIN_DIRECTORY / "config.yaml");
        THEME_DEFAULT = load_yaml(MAIN_DIRECTORY / "res/themes/default.yaml");
    } catch (const std::exception &e) {
        logger.error("Cannot load configuration from {}: {}", MAIN_DIRECTORY.string(), e.what());
        std::_Exit(1);
    }

    // Load theme
    load_theme();
}

}  // namespace config
