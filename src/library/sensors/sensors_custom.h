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
// This file allows to add custom data source as sensors and display them in System Monitor themes.
// There is no limitation on how much custom data source classes can be added to this file.
// See CustomDataExample theme for the theme implementation part.
//
// To add a custom data source:
// 1. declare a class inheriting CustomDataSource below and implement its 3 methods in sensors_custom.cpp,
// 2. register it in sensors_custom.cpp (custom_data_sources()) with the name used in the theme, under STATS/CUSTOM,
// 3. rebuild the program with make.

#pragma once

#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace sensors_custom {

// Custom data classes must be implemented in this file, inherit the CustomDataSource and implement its 3 methods
class CustomDataSource
{
public:
    virtual ~CustomDataSource() = default;

    // Numeric value will be used for graph and radial progress bars
    // If there is no numeric value, return std::nullopt
    virtual std::optional<double> as_numeric() = 0;

    // Text value will be used for text display and radial progress bar inner text
    // Numeric value can be formatted here to be displayed as expected
    // It is also possible to return a text unrelated to the numeric value
    // If this function returns std::nullopt, the numeric value will be used as string without formatting
    virtual std::optional<std::string> as_string() = 0;

    // List of last numeric values will be used for plot graph
    // If you do not want to draw a line graph or if your custom data has no numeric values, return std::nullopt
    virtual std::optional<std::vector<double>> last_values() = 0;
};

// Example for a custom data class that has numeric and text values
class ExampleCustomNumericData : public CustomDataSource
{
public:
    std::optional<double> as_numeric() override;
    std::optional<std::string> as_string() override;
    std::optional<std::vector<double>> last_values() override;

private:
    double value = 0;
    // This list is used to store the last 10 values to display a line graph
    // By default, it is filled with NaN values to indicate there is no data stored
    std::vector<double> last_val = std::vector<double>(10, std::numeric_limits<double>::quiet_NaN());
};

// Example for a custom data class that only has text values
class ExampleCustomTextOnlyData : public CustomDataSource
{
public:
    std::optional<double> as_numeric() override;
    std::optional<std::string> as_string() override;
    std::optional<std::vector<double>> last_values() override;
};

// All custom data sources, by the name used in the themes. Created once, so that they can keep data between calls.
std::map<std::string, std::unique_ptr<CustomDataSource>> &custom_data_sources();

}  // namespace sensors_custom
