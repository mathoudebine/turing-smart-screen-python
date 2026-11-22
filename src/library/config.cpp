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

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <fstream>

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

}  // namespace

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

std::string yaml_scalar(const std::string &value)
{
    static const std::vector<std::string> special_words = {"true", "false", "yes", "no", "on", "off", "null", "~", "y",
                                                           "n"};
    std::string lower;
    for (unsigned char c: value) {
        lower.push_back(static_cast<char>(std::tolower(c)));
    }
    bool plain = !value.empty() && value.front() != ' ' && value.back() != ' ' &&
                 std::find(special_words.begin(), special_words.end(), lower) == special_words.end() &&
                 std::string("-?:,[]{}#&*!|>'\"%@`").find(value.front()) == std::string::npos &&
                 value.find(": ") == std::string::npos && value.find(" #") == std::string::npos;
    for (unsigned char c: value) {
        if (c < 0x20 || c == '"' || c == '\\') {
            plain = false;
        }
    }
    if (plain) {
        return value;
    }
    std::string quoted = "\"";
    for (char c: value) {
        if (c == '"' || c == '\\') {
            quoted.push_back('\\');
        }
        quoted.push_back(c);
    }
    return quoted + "\"";
}

namespace {

// Length of the YAML value at the start of text (up to the comment or the end of line)
size_t yaml_value_length(const std::string &text)
{
    if (!text.empty() && (text[0] == '"' || text[0] == '\'')) {
        const char quote = text[0];
        for (size_t i = 1; i < text.size(); i++) {
            if (text[i] == '\\' && quote == '"') {
                i++;
            } else if (text[i] == quote) {
                if (quote == '\'' && i + 1 < text.size() && text[i + 1] == '\'') {
                    i++;  // '' is an escaped quote in single-quoted strings
                } else {
                    return i + 1;
                }
            }
        }
        return text.size();
    }
    const size_t comment = text.find(" #");
    size_t length = comment == std::string::npos ? text.size() : comment;
    while (length > 0 && text[length - 1] == ' ') {
        length--;
    }
    return length;
}

}  // namespace

std::string update_yaml_text(const std::string &text, const std::vector<YamlUpdate> &updates)
{
    std::vector<std::string> lines;
    {
        size_t start = 0, end;
        while ((end = text.find('\n', start)) != std::string::npos) {
            lines.push_back(text.substr(start, end - start));
            start = end + 1;
        }
        if (start < text.size()) {
            lines.push_back(text.substr(start));
        }
    }

    auto indentation = [](const std::string &line) { return line.find_first_not_of(' '); };
    auto is_content = [&](const std::string &line) {
        const size_t indent = indentation(line);
        return indent != std::string::npos && line[indent] != '#';
    };

    for (const auto &update: updates) {
        // Section: top-level "section:" line
        size_t section_line = lines.size();
        for (size_t i = 0; i < lines.size(); i++) {
            if (lines[i].rfind(update.section + ":", 0) == 0) {
                section_line = i;
                break;
            }
        }
        if (section_line == lines.size()) {
            lines.push_back(update.section + ":");
            lines.push_back("  " + update.key + ": " + update.value);
            continue;
        }

        // Keys of the section: lines indented until the next top-level content line
        size_t section_end = section_line + 1;
        size_t last_content = section_line;
        bool found = false;
        for (; section_end < lines.size(); section_end++) {
            const std::string &line = lines[section_end];
            if (is_content(line) && indentation(line) == 0) {
                break;
            }
            if (!is_content(line)) {
                continue;
            }
            last_content = section_end;
            const size_t indent = indentation(line);
            if (line.compare(indent, update.key.size() + 1, update.key + ":") == 0) {
                // Replace the value, keep the comment
                size_t value_start = indent + update.key.size() + 1;
                while (value_start < line.size() && line[value_start] == ' ') {
                    value_start++;
                }
                const size_t value_length = yaml_value_length(line.substr(value_start));
                lines[section_end] = line.substr(0, indent) + update.key + ": " + update.value +
                                     line.substr(value_start + value_length);
                found = true;
                break;
            }
        }
        if (!found) {
            const std::string indent = last_content > section_line
                                           ? lines[last_content].substr(0, indentation(lines[last_content]))
                                           : "  ";
            lines.insert(lines.begin() + static_cast<long>(last_content) + 1, indent + update.key + ": " + update.value);
        }
    }

    std::string result;
    for (const auto &line: lines) {
        result += line + "\n";
    }
    return result;
}

void update_yaml_file(const fs::path &path, const std::vector<YamlUpdate> &updates)
{
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("Cannot read " + path.string());
    }
    const std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    in.close();
    const std::string updated = update_yaml_text(text, updates);
    std::ofstream out(path, std::ios::trunc);
    out << updated;
    if (!out) {
        throw std::runtime_error("Cannot write " + path.string());
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
