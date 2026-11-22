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

// C++ port of library/display.py

#include "library/display.h"

#include <cstdlib>
#include <map>
#include <optional>
#include <string>

#include "library/config.h"
#include "library/lcd/lcd_simulated.h"
#include "library/log.h"

namespace {

std::optional<std::string> get_full_path(const std::string &path, const std::string &name)
{
    if (!name.empty()) {
        return path + name;
    }
    return std::nullopt;
}

}  // namespace

Orientation get_theme_orientation()
{
    const YAML::Node &theme = config::THEME_DATA;
    const YAML::Node &cfg = config::CONFIG_DATA;
    const std::string orientation = config::get(theme["display"], "DISPLAY_ORIENTATION", "");
    const bool reverse = config::get(cfg["display"], "DISPLAY_REVERSE", false);
    if (orientation == "portrait") {
        return reverse ? Orientation::REVERSE_PORTRAIT : Orientation::PORTRAIT;
    }
    if (orientation == "landscape") {
        return reverse ? Orientation::REVERSE_LANDSCAPE : Orientation::LANDSCAPE;
    }
    logger.warning("Orientation '{}' unknown, using portrait", orientation);
    return Orientation::PORTRAIT;
}

std::pair<int, int> get_theme_size()
{
    static const std::map<std::string, std::pair<int, int>> sizes = {
        {"0.96\"", {80, 160}},
        {"2.1\"", {480, 480}},
        {"2.8\"", {480, 480}},
        {"3.5\"", {320, 480}},
        {"4.6\"", {320, 960}},
        {"5\"", {480, 800}},
        {"5.2\"", {720, 1280}},
        {"8\"", {800, 1280}},
        {"8.8\"", {480, 1920}},
        {"9.2\"", {480, 1920}},  // 9.2" displays are 1920x462 but using 1920x480 to be compatible with 8.8" themes
        {"12.3\"", {720, 1920}},
    };
    const YAML::Node &theme = config::THEME_DATA;
    const auto it = sizes.find(config::get(theme["display"], "DISPLAY_SIZE", ""));
    if (it != sizes.end()) {
        return it->second;
    }
    logger.warning("Cannot find valid DISPLAY_SIZE property in selected theme {}, defaulting to 3.5\"",
                   config::get(config::CONFIG_DATA["config"], "THEME", ""));
    return {320, 480};
}

Display::Display()
{
    const auto [width, height] = get_theme_size();
    const YAML::Node &cfg = config::CONFIG_DATA;
    const std::string revision = config::get(cfg["display"], "REVISION", "");

    if (revision == "SIMU") {
        // Simulated display: always set width/height from theme
        lcd = std::make_unique<LcdSimulated>("AUTO", width, height);
    } else if (revision == "A" || revision == "B" || revision == "C" || revision == "D" || revision == "TUR_USB" ||
               revision == "WEACT_A" || revision == "WEACT_B") {
        // TODO(C++ port, phase 3): hardware drivers
        logger.error("Display revision '{}' is not supported yet by the C++ version, use SIMU", revision);
        std::_Exit(1);
    } else {
        logger.error("Unknown display revision '{}'", revision);
        std::_Exit(1);
    }
}

void Display::initialize_display()
{
    // Reset screen in case it was in an unstable state (screen is also cleared)
    // Can be disabled by config. option. Assume true if key not present in config.yaml
    const YAML::Node &cfg = config::CONFIG_DATA;
    if (config::get(cfg["display"], "RESET_ON_STARTUP", true)) {
        lcd->Reset();
    } else {
        logger.debug("RESET_ON_STARTUP is false: display will not be reset");
    }

    // Send initialization commands
    lcd->InitializeComm();

    // Turn on display, set brightness and LEDs for supported HW
    turn_on();

    // Set orientation
    lcd->SetOrientation(get_theme_orientation());
}

void Display::turn_on()
{
    const YAML::Node &cfg = config::CONFIG_DATA;
    const YAML::Node &theme = config::THEME_DATA;

    // Turn screen on in case it was turned off previously
    lcd->ScreenOn();

    // Set brightness
    lcd->SetBrightness(cfg["display"]["BRIGHTNESS"].as<int>());

    // Set backplate RGB LED color (for supported HW only)
    lcd->SetBackplateLedColor(config::get_color(theme["display"], "DISPLAY_RGB_LED", {255, 255, 255}));
}

void Display::turn_off()
{
    // Turn screen off
    lcd->ScreenOff();

    // Turn off backplate RGB LED
    lcd->SetBackplateLedColor({0, 0, 0});
}

void Display::display_static_images()
{
    const YAML::Node &theme = config::THEME_DATA;
    const YAML::Node images = theme["static_images"];
    if (!images.IsDefined() || !images.IsMap()) {
        return;
    }
    const std::string theme_path = theme["PATH"].as<std::string>();
    for (const auto &item: images) {
        const std::string name = item.first.as<std::string>();
        const YAML::Node &image = item.second;
        logger.debug("Drawing Image: {}", name);
        lcd->DisplayBitmap(theme_path + config::get(image, "PATH", ""),
                           config::get(image, "X", 0),
                           config::get(image, "Y", 0),
                           config::get(image, "WIDTH", 0),
                           config::get(image, "HEIGHT", 0));
    }
}

void Display::display_static_text()
{
    const YAML::Node &theme = config::THEME_DATA;
    const YAML::Node texts = theme["static_text"];
    if (!texts.IsDefined() || !texts.IsMap()) {
        return;
    }
    const std::string theme_path = theme["PATH"].as<std::string>();
    for (const auto &item: texts) {
        const std::string name = item.first.as<std::string>();
        const YAML::Node &text = item.second;
        logger.debug("Drawing Text: {}", name);

        lcd->DisplayText({
            .text = config::get(text, "TEXT", ""),
            .x = config::get(text, "X", 0),
            .y = config::get(text, "Y", 0),
            .width = config::get(text, "WIDTH", 0),
            .height = config::get(text, "HEIGHT", 0),
            .font = config::FONTS_DIR + config::get(text, "FONT", "roboto-mono/RobotoMono-Regular.ttf"),
            .font_size = config::get(text, "FONT_SIZE", 10),
            .font_color = config::get_color(text, "FONT_COLOR", {0, 0, 0}),
            .background_color = config::get_color(text, "BACKGROUND_COLOR", {255, 255, 255}),
            .background_image = get_full_path(theme_path, config::get(text, "BACKGROUND_IMAGE", "")),
            .align = config::get(text, "ALIGN", "left"),
            .anchor = config::get(text, "ANCHOR", "lt"),
        });
    }
}

Display &display()
{
    static Display instance;
    return instance;
}
