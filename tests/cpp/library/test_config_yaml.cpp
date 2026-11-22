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

// Unit tests of the config.yaml update functions of library/config (replace ruamel.yaml of configure.py)

#include <gtest/gtest.h>

#include "library/config.h"

TEST(ConfigYaml, Scalar)
{
    EXPECT_EQ(config::yaml_scalar("AUTO"), "AUTO");
    EXPECT_EQ(config::yaml_scalar("Cyberpunk 2077"), "Cyberpunk 2077");
    EXPECT_EQ(config::yaml_scalar("/dev/ttyACM0"), "/dev/ttyACM0");
    EXPECT_EQ(config::yaml_scalar("8.8.8.8"), "8.8.8.8");
    EXPECT_EQ(config::yaml_scalar(""), "\"\"");
    EXPECT_EQ(config::yaml_scalar("true"), "\"true\"");
    EXPECT_EQ(config::yaml_scalar("a: b"), "\"a: b\"");
    EXPECT_EQ(config::yaml_scalar("say \"hi\""), "\"say \\\"hi\\\"\"");
    EXPECT_EQ(config::yaml_scalar("-x"), "\"-x\"");
}

TEST(ConfigYaml, UpdateKeepsComments)
{
    const std::string text = "---\n"
                             "config:\n"
                             "  # Comment about the port\n"
                             "  COM_PORT: \"AUTO\"\n"
                             "\n"
                             "  ETH: \"\" # Ethernet Card\n"
                             "  THEME: 3.5inchTheme2\n"
                             "\n"
                             "display:\n"
                             "  # Brightness\n"
                             "  BRIGHTNESS: 20\n";
    const std::string updated = config::update_yaml_text(text, {
        {"config", "COM_PORT", config::yaml_scalar("/dev/ttyACM0")},
        {"config", "ETH", config::yaml_scalar("eth0")},
        {"config", "CPU_FAN", config::yaml_scalar("AUTO")},  // missing key: added at the end of the section
        {"display", "BRIGHTNESS", "35"},
        {"display", "DISPLAY_REVERSE", "false"},
        {"newsection", "KEY", "1"},
    });
    EXPECT_EQ(updated, "---\n"
                       "config:\n"
                       "  # Comment about the port\n"
                       "  COM_PORT: /dev/ttyACM0\n"
                       "\n"
                       "  ETH: eth0 # Ethernet Card\n"
                       "  THEME: 3.5inchTheme2\n"
                       "  CPU_FAN: AUTO\n"
                       "\n"
                       "display:\n"
                       "  # Brightness\n"
                       "  BRIGHTNESS: 35\n"
                       "  DISPLAY_REVERSE: false\n"
                       "newsection:\n"
                       "  KEY: 1\n");

    // The updated text is valid YAML with the new values
    const YAML::Node node = YAML::Load(updated);
    EXPECT_EQ(node["config"]["ETH"].as<std::string>(), "eth0");
    EXPECT_EQ(node["display"]["BRIGHTNESS"].as<int>(), 35);
}

TEST(ConfigYaml, UpdateQuotedValueWithHash)
{
    const std::string updated = config::update_yaml_text("config:\n  KEY: \"a # b\" # comment\n",
                                                         {{"config", "KEY", config::yaml_scalar("c")}});
    EXPECT_EQ(updated, "config:\n  KEY: c # comment\n");
}
