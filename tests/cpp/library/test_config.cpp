// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
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

// Unit tests of library/config (C++ port of library/config.py)

#include <gtest/gtest.h>

#include "library/config.h"

TEST(Config, CopyDefault)
{
    const YAML::Node defaults = YAML::Load(R"(
STATS:
  CPU:
    INTERVAL: 0
    TEXT:
      SHOW: False
      X: 0
  GPU:
    INTERVAL: 0
)");
    YAML::Node theme = YAML::Load(R"(
STATS:
  CPU:
    TEXT:
      SHOW: True
  GPU:
)");
    config::copy_default(defaults, theme);
    EXPECT_TRUE(theme["STATS"]["CPU"]["TEXT"]["SHOW"].as<bool>());  // theme value kept
    EXPECT_EQ(theme["STATS"]["CPU"]["TEXT"]["X"].as<int>(), 0);  // default value added
    EXPECT_EQ(theme["STATS"]["CPU"]["INTERVAL"].as<int>(), 0);
    EXPECT_EQ(theme["STATS"]["GPU"]["INTERVAL"].as<int>(), 0);  // empty section filled with defaults

    // Default values are copied, not shared with the theme
    theme["STATS"]["GPU"]["INTERVAL"] = 5;
    EXPECT_EQ(defaults["STATS"]["GPU"]["INTERVAL"].as<int>(), 0);
}

TEST(Config, Get)
{
    const YAML::Node node = YAML::Load("{A: 12, B: text, C: , D: \"1, 2, 3\", E: True}");
    EXPECT_EQ(config::get(node, "A", 0), 12);
    EXPECT_EQ(config::get(node, "B", "x"), "text");
    EXPECT_EQ(config::get(node, "C", 7), 7);  // empty value: default
    EXPECT_EQ(config::get(node, "Z", 7), 7);  // missing key: default
    EXPECT_TRUE(config::get(node, "E", false));
    EXPECT_EQ(config::get_color(node, "D", {0, 0, 0}), (RGBColor{1, 2, 3}));
    EXPECT_EQ(config::get_color(node, "Z", {4, 5, 6}), (RGBColor{4, 5, 6}));
    EXPECT_THROW(config::get(node, "B", 0), std::runtime_error);
    EXPECT_EQ(config::get(node["missing"], "A", 3), 3);
}
