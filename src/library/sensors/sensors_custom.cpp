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

// C++ port of library/sensors/sensors_custom.py

#include "library/sensors/sensors_custom.h"

#include <format>

namespace sensors_custom {

std::optional<double> ExampleCustomNumericData::as_numeric()
{
    // Numeric value will be used for graph and radial progress bars
    // Here a function from another module can be called to get data
    // Example: value = get_rgb_led_brightness() / system_volume() ...
    value = 75.845;

    // Store the value to the history list that will be used for line graph
    last_val.push_back(value);
    // Also remove the oldest value from history list
    last_val.erase(last_val.begin());

    return value;
}

std::optional<std::string> ExampleCustomNumericData::as_string()
{
    // Text value will be used for text display and radial progress bar inner text.
    // Numeric value can be formatted here to be displayed as expected
    // It is also possible to return a text unrelated to the numeric value
    // Example here: format numeric value: add unit as a suffix, and keep 1 digit decimal precision
    return std::format("{:>5.1f}%", value);
    // Important note! If your numeric value can vary in size, be sure to display it with a default size.
    // E.g. if your value can range from 0 to 9999, you need to display it with at least 4 characters every time.
    // --> return std::format("{:>4}%", value);
    // Otherwise, part of the previous value can stay displayed ("ghosting") after a refresh
}

std::optional<std::vector<double>> ExampleCustomNumericData::last_values()
{
    // List of last numeric values will be used for plot graph
    return last_val;
}

std::optional<double> ExampleCustomTextOnlyData::as_numeric()
{
    // If there is no numeric value, return std::nullopt
    return std::nullopt;
}

std::optional<std::string> ExampleCustomTextOnlyData::as_string()
{
    // If a custom data class only has text values, it won't be possible to display graph or radial bars
    return std::format("C++: {}", __VERSION__);
}

std::optional<std::vector<double>> ExampleCustomTextOnlyData::last_values()
{
    // If a custom data class only has text values, it won't be possible to display line graph
    return std::nullopt;
}

std::map<std::string, std::unique_ptr<CustomDataSource>> &custom_data_sources()
{
    static std::map<std::string, std::unique_ptr<CustomDataSource>> sources = [] {
        std::map<std::string, std::unique_ptr<CustomDataSource>> s;
        // Register here the custom data sources, with the name used in the theme under STATS/CUSTOM
        s["ExampleCustomNumericData"] = std::make_unique<ExampleCustomNumericData>();
        s["ExampleCustomTextOnlyData"] = std::make_unique<ExampleCustomTextOnlyData>();
        return s;
    }();
    return sources;
}

}  // namespace sensors_custom
