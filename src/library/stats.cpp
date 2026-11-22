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

// C++ port of library/stats.py

#include "library/stats.h"

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <format>
#include <fstream>
#include <limits>
#include <map>
#include <memory>
#include <random>

#include <curl/curl.h>
#include <unicode/datefmt.h>
#include <unicode/smpdtfmt.h>
#include <unicode/uchar.h>
#include <unicode/unistr.h>

#include "library/config.h"
#include "library/display.h"
#include "library/log.h"
#include "library/ping.h"
#include "library/sensors/sensors_custom.h"
#include "library/sensors/sensors_python.h"
#include "library/sensors/sensors_stub_random.h"
#include "library/sensors/sensors_stub_static.h"

namespace stats {

namespace {

constexpr double NaN = std::numeric_limits<double>::quiet_NaN();

std::string ETH_CARD;
std::string WLO_CARD;
std::string HW_SENSORS;
std::string CPU_FAN;
std::string PING_DEST;

sensors::Sensors sensors;

// Theme data, read-only: const access never modifies the YAML tree (shared by all the threads)
const YAML::Node &theme_stats()
{
    static const YAML::Node &theme = config::THEME_DATA;
    return theme;
}

YAML::Node stats_node(const std::string &key)
{
    return theme_stats()["STATS"][key];
}

int history_size(const YAML::Node &line_graph_data)
{
    return config::get(line_graph_data, "HISTORY_SIZE", DEFAULT_HISTORY_SIZE);
}

bool is_shown(const YAML::Node &theme_data)
{
    return config::get(theme_data, "SHOW", false);
}

// Disable the display of a theme item (when its sensor is not supported)
void hide(YAML::Node theme_data)
{
    theme_data["SHOW"] = false;
}

// Python int(value): truncation. NaN (unsupported sensor) is displayed as 0.
int to_int(double value)
{
    return std::isnan(value) ? 0 : static_cast<int>(value);
}

// Python f"{value:>{min_size}}": right-aligned text, counting Unicode characters (not UTF-8 bytes)
std::string align_right(const std::string &text, int min_size)
{
    int length = 0;
    for (unsigned char c: text) {
        if ((c & 0xC0) != 0x80) {
            length++;
        }
    }
    return length < min_size ? std::string(min_size - length, ' ') + text : text;
}

size_t curl_write(char *ptr, size_t size, size_t nmemb, void *userdata)
{
    static_cast<std::string *>(userdata)->append(ptr, size * nmemb);
    return size * nmemb;
}

// Python str.capitalize(): first character upper case, the rest lower case
std::string capitalize(const std::string &text)
{
    icu::UnicodeString s = icu::UnicodeString::fromUTF8(text);
    s.toLower();
    if (s.length() > 0) {
        const UChar32 first = s.char32At(0);
        s.replace(0, U16_LENGTH(first), icu::UnicodeString(u_toupper(first)));
    }
    std::string result;
    s.toUTF8String(result);
    return result;
}

// Locale used for dates, like babel.dates.LC_TIME: from LC_TIME / LANGUAGE / LC_ALL / LC_CTYPE / LANG
std::string get_lc_time()
{
    for (const char *var: {"LC_TIME", "LANGUAGE", "LC_ALL", "LC_CTYPE", "LANG"}) {
        const char *value = std::getenv(var);
        if (!value || !*value) {
            continue;
        }
        std::string locale = value;
        if (const auto colon = locale.find(':'); colon != std::string::npos) {
            locale = locale.substr(0, colon);  // LANGUAGE can be a list
        }
        if (locale == "C" || locale == "POSIX") {
            return "en_US_POSIX";
        }
        locale = locale.substr(0, locale.find_first_of(".@"));
        if (!locale.empty()) {
            return locale;
        }
    }
    return "en_US";
}

// Format a date or time with a babel/CLDR format: 'short', 'medium', 'long', 'full', or a CLDR pattern
std::string format_datetime(std::time_t timestamp, const std::string &format, const std::string &locale_name,
                            bool is_time)
{
    const icu::Locale locale(locale_name.c_str());
    std::unique_ptr<icu::DateFormat> formatter;
    const std::map<std::string, icu::DateFormat::EStyle> styles = {
        {"short", icu::DateFormat::kShort},
        {"medium", icu::DateFormat::kMedium},
        {"long", icu::DateFormat::kLong},
        {"full", icu::DateFormat::kFull},
    };
    if (const auto it = styles.find(format); it != styles.end()) {
        formatter.reset(is_time ? icu::DateFormat::createTimeInstance(it->second, locale)
                                : icu::DateFormat::createDateInstance(it->second, locale));
    } else {
        UErrorCode status = U_ZERO_ERROR;
        formatter = std::make_unique<icu::SimpleDateFormat>(icu::UnicodeString::fromUTF8(format), locale, status);
        if (U_FAILURE(status)) {
            formatter.reset();
        }
    }
    if (!formatter) {
        throw std::runtime_error("Invalid date/time format '" + format + "'");
    }
    icu::UnicodeString text;
    formatter->format(static_cast<UDate>(timestamp) * 1000.0, text);
    std::string result;
    text.toUTF8String(result);
    return result;
}

}  // namespace

void init()
{
    const YAML::Node &cfg = config::CONFIG_DATA;
    ETH_CARD = config::get(cfg["config"], "ETH", "");
    WLO_CARD = config::get(cfg["config"], "WLO", "");
    HW_SENSORS = config::get(cfg["config"], "HW_SENSORS", "AUTO");
    CPU_FAN = config::get(cfg["config"], "CPU_FAN", "AUTO");
    PING_DEST = config::get(cfg["config"], "PING", "127.0.0.1");

    if (HW_SENSORS == "PYTHON" || HW_SENSORS == "AUTO") {
        sensors = sensors_python::create();
    } else if (HW_SENSORS == "LHM") {
        logger.error("LibreHardwareMonitor integration is only available on Windows");
        std::_Exit(1);
    } else if (HW_SENSORS == "STUB") {
        logger.warning("Stub sensors, not real HW sensors");
        sensors = sensors_stub_random::create();
    } else if (HW_SENSORS == "STATIC") {
        logger.warning("Stub sensors, not real HW sensors");
        sensors = sensors_stub_static::create();
    } else {
        logger.error("Unsupported HW_SENSORS value in config.yaml");
        std::_Exit(1);
    }

    curl_global_init(CURL_GLOBAL_DEFAULT);
}

std::optional<std::string> get_theme_file_path(const std::string &name)
{
    if (!name.empty()) {
        return theme_stats()["PATH"].as<std::string>() + name;
    }
    return std::nullopt;
}

void display_themed_value(const YAML::Node &theme_data, const std::optional<std::string> &value, int min_size,
                          const std::string &unit)
{
    if (!is_shown(theme_data)) {
        return;
    }

    if (!value) {
        return;
    }

    // overridable MIN_SIZE from theme with backward compatibility
    min_size = config::get(theme_data, "MIN_SIZE", min_size);

    std::string text = align_right(*value, min_size);
    if (config::get(theme_data, "SHOW_UNIT", true) && !unit.empty()) {
        text += unit;
    }

    display().lcd->DisplayText({
        .text = text,
        .x = config::get(theme_data, "X", 0),
        .y = config::get(theme_data, "Y", 0),
        .width = config::get(theme_data, "WIDTH", 0),
        .height = config::get(theme_data, "HEIGHT", 0),
        .font = config::FONTS_DIR + config::get(theme_data, "FONT", "roboto-mono/RobotoMono-Regular.ttf"),
        .font_size = config::get(theme_data, "FONT_SIZE", 10),
        .font_color = config::get_color(theme_data, "FONT_COLOR", {0, 0, 0}),
        .background_color = config::get_color(theme_data, "BACKGROUND_COLOR", {255, 255, 255}),
        .background_image = get_theme_file_path(config::get(theme_data, "BACKGROUND_IMAGE", "")),
        .align = config::get(theme_data, "ALIGN", "left"),
        .anchor = config::get(theme_data, "ANCHOR", "lt"),
    });
}

void display_themed_percent_value(const YAML::Node &theme_data, double value)
{
    display_themed_value(theme_data, std::to_string(to_int(value)), 3, "%");
}

void display_themed_temperature_value(const YAML::Node &theme_data, double value)
{
    display_themed_value(theme_data, std::to_string(to_int(value)), 3, "°C");
}

void display_themed_progress_bar(const YAML::Node &theme_data, double value)
{
    if (!is_shown(theme_data)) {
        return;
    }

    display().lcd->DisplayProgressBar({
        .x = config::get(theme_data, "X", 0),
        .y = config::get(theme_data, "Y", 0),
        .width = config::get(theme_data, "WIDTH", 0),
        .height = config::get(theme_data, "HEIGHT", 0),
        .min_value = config::get(theme_data, "MIN_VALUE", 0.0),
        .max_value = config::get(theme_data, "MAX_VALUE", 100.0),
        .value = static_cast<double>(to_int(value)),
        .bar_color = config::get_color(theme_data, "BAR_COLOR", {0, 0, 0}),
        .bar_outline = config::get(theme_data, "BAR_OUTLINE", false),
        .background_color = config::get_color(theme_data, "BACKGROUND_COLOR", {255, 255, 255}),
        .background_image = get_theme_file_path(config::get(theme_data, "BACKGROUND_IMAGE", "")),
        .reverse_direction = config::get(theme_data, "REVERSE_DIRECTION", false),
    });
}

void display_themed_radial_bar(const YAML::Node &theme_data, double value, const std::string &value_text,
                               int min_size, const std::string &unit, const std::optional<std::string> &custom_text)
{
    if (!is_shown(theme_data)) {
        return;
    }

    std::string text;
    if (config::get(theme_data, "SHOW_TEXT", false)) {
        if (custom_text) {
            text = *custom_text;
        } else {
            text = align_right(value_text, min_size);
            if (config::get(theme_data, "SHOW_UNIT", true) && !unit.empty()) {
                text += unit;
            }
        }
    }

    const YAML::Node custom_bbox = theme_data["CUSTOM_BBOX"];
    std::tuple<int, int, int, int> bbox = {0, 0, 0, 0};
    if (custom_bbox.IsDefined() && custom_bbox.IsSequence() && custom_bbox.size() == 4) {
        bbox = {custom_bbox[0].as<int>(), custom_bbox[1].as<int>(), custom_bbox[2].as<int>(),
                custom_bbox[3].as<int>()};
    }
    const YAML::Node text_offset = theme_data["TEXT_OFFSET"];
    std::pair<int, int> offset = {0, 0};
    if (text_offset.IsDefined() && text_offset.IsSequence() && text_offset.size() == 2) {
        offset = {text_offset[0].as<int>(), text_offset[1].as<int>()};
    }

    display().lcd->DisplayRadialProgressBar({
        .xc = config::get(theme_data, "X", 0),
        .yc = config::get(theme_data, "Y", 0),
        .radius = config::get(theme_data, "RADIUS", 1),
        .bar_width = config::get(theme_data, "WIDTH", 1),
        .min_value = config::get(theme_data, "MIN_VALUE", 0.0),
        .max_value = config::get(theme_data, "MAX_VALUE", 100.0),
        .angle_start = config::get(theme_data, "ANGLE_START", 0.0),
        .angle_end = config::get(theme_data, "ANGLE_END", 360.0),
        .angle_sep = config::get(theme_data, "ANGLE_SEP", 0),
        .angle_steps = config::get(theme_data, "ANGLE_STEPS", 1),
        .clockwise = config::get(theme_data, "CLOCKWISE", false),
        .value = std::isnan(value) ? 0.0 : value,
        .text = text,
        .font = config::FONTS_DIR + config::get(theme_data, "FONT", "roboto-mono/RobotoMono-Regular.ttf"),
        .font_size = config::get(theme_data, "FONT_SIZE", 10),
        .font_color = config::get_color(theme_data, "FONT_COLOR", {0, 0, 0}),
        .bar_color = config::get_color(theme_data, "BAR_COLOR", {0, 0, 0}),
        .background_color = config::get_color(theme_data, "BACKGROUND_COLOR", {0, 0, 0}),
        .background_image = get_theme_file_path(config::get(theme_data, "BACKGROUND_IMAGE", "")),
        .custom_bbox = bbox,
        .text_offset = offset,
        .bar_background_color = config::get_color(theme_data, "BAR_BACKGROUND_COLOR", {0, 0, 0}),
        .draw_bar_background = config::get(theme_data, "DRAW_BAR_BACKGROUND", false),
        .bar_decoration = config::get(theme_data, "BAR_DECORATION", ""),
    });
}

void display_themed_percent_radial_bar(const YAML::Node &theme_data, double value)
{
    display_themed_radial_bar(theme_data, to_int(value), std::to_string(to_int(value)), 3, "%");
}

void display_themed_temperature_radial_bar(const YAML::Node &theme_data, double value)
{
    display_themed_radial_bar(theme_data, to_int(value), std::to_string(to_int(value)), 3, "°C");
}

void display_themed_line_graph(const YAML::Node &theme_data, const std::vector<double> &values)
{
    if (!is_shown(theme_data)) {
        return;
    }

    const RGBColor line_color = config::get_color(theme_data, "LINE_COLOR", {0, 0, 0});

    display().lcd->DisplayLineGraph({
        .x = config::get(theme_data, "X", 0),
        .y = config::get(theme_data, "Y", 0),
        .width = config::get(theme_data, "WIDTH", 1),
        .height = config::get(theme_data, "HEIGHT", 1),
        .values = values,
        .min_value = config::get(theme_data, "MIN_VALUE", 0.0),
        .max_value = config::get(theme_data, "MAX_VALUE", 100.0),
        .autoscale = config::get(theme_data, "AUTOSCALE", false),
        .line_color = line_color,
        .line_width = config::get(theme_data, "LINE_WIDTH", 2),
        .graph_axis = config::get(theme_data, "AXIS", false),
        // If no color specified, use line color for axis
        .axis_color = config::get_color(theme_data, "AXIS_COLOR", line_color),
        .axis_font = config::FONTS_DIR + config::get(theme_data, "AXIS_FONT", "roboto/Roboto-Black.ttf"),
        .axis_font_size = config::get(theme_data, "AXIS_FONT_SIZE", 10),
        .background_color = config::get_color(theme_data, "BACKGROUND_COLOR", {0, 0, 0}),
        .background_image = get_theme_file_path(config::get(theme_data, "BACKGROUND_IMAGE", "")),
    });
}

void save_last_value(double value, std::vector<double> &last_values, int history_size)
{
    // Initialize last values list the first time with given size
    if (static_cast<int>(last_values.size()) != history_size) {
        last_values = last_values_list(history_size);
    }
    // Store the value to the list that can then be used for line graph
    last_values.push_back(value);
    // Also remove the oldest value from list
    last_values.erase(last_values.begin());
}

std::vector<double> last_values_list(int size)
{
    return std::vector<double>(static_cast<size_t>(std::max(size, 1)), NaN);
}

std::string bytes2human(double n, const std::string &value_format, const std::string &suffix)
{
    static const char *symbols[] = {"K", "M", "G", "T", "P", "E", "Z", "Y"};
    for (int i = 7; i >= 0; i--) {
        const double prefix = std::ldexp(1.0, (i + 1) * 10);
        if (std::fabs(n) >= prefix) {
            const double value = n / prefix;
            return std::vformat(value_format, std::make_format_args(value)) + symbols[i] + suffix;
        }
    }
    return std::vformat(value_format, std::make_format_args(n)) + "B" + suffix;
}

// ---------------------------------------------------------------------------------------------------------------------
// CPU

namespace {
std::vector<double> last_values_cpu_percentage;
std::vector<double> last_values_cpu_temperature;
std::vector<double> last_values_cpu_fan_speed;
std::vector<double> last_values_cpu_frequency;
}

void CPU::percentage()
{
    const YAML::Node theme_data = stats_node("CPU")["PERCENTAGE"];
    const YAML::Node interval = theme_data["INTERVAL"];
    const double cpu_percentage = sensors.cpu->percentage(
        interval.IsDefined() && !interval.IsNull() ? std::optional<double>(interval.as<double>()) : std::nullopt);
    save_last_value(cpu_percentage, last_values_cpu_percentage, history_size(theme_data["LINE_GRAPH"]));

    display_themed_progress_bar(theme_data["GRAPH"], cpu_percentage);
    display_themed_percent_radial_bar(theme_data["RADIAL"], cpu_percentage);
    display_themed_percent_value(theme_data["TEXT"], cpu_percentage);
    display_themed_line_graph(theme_data["LINE_GRAPH"], last_values_cpu_percentage);
}

void CPU::frequency()
{
    const double freq_ghz = sensors.cpu->frequency() / 1000;
    const YAML::Node theme_data = stats_node("CPU")["FREQUENCY"];

    save_last_value(freq_ghz, last_values_cpu_frequency, history_size(theme_data["LINE_GRAPH"]));

    const std::string freq_text = std::format("{:.2f}", freq_ghz);
    display_themed_value(theme_data["TEXT"], freq_text, 4, " GHz");
    display_themed_progress_bar(theme_data["GRAPH"], freq_ghz);
    display_themed_radial_bar(theme_data["RADIAL"], freq_ghz, freq_text, 4, " GHz");
    display_themed_line_graph(theme_data["LINE_GRAPH"], last_values_cpu_frequency);
}

void CPU::load()
{
    const auto cpu_load = sensors.cpu->load();
    const YAML::Node load_theme_data = stats_node("CPU")["LOAD"];

    display_themed_percent_value(load_theme_data["ONE"]["TEXT"], cpu_load[0]);
    display_themed_percent_value(load_theme_data["FIVE"]["TEXT"], cpu_load[1]);
    display_themed_percent_value(load_theme_data["FIFTEEN"]["TEXT"], cpu_load[2]);
}

void CPU::temperature()
{
    double temperature = sensors.cpu->temperature();
    const YAML::Node theme_data = stats_node("CPU")["TEMPERATURE"];
    save_last_value(temperature, last_values_cpu_temperature, history_size(theme_data["LINE_GRAPH"]));

    const YAML::Node cpu_temp_text_data = theme_data["TEXT"];
    const YAML::Node cpu_temp_radial_data = theme_data["RADIAL"];
    const YAML::Node cpu_temp_graph_data = theme_data["GRAPH"];
    const YAML::Node cpu_temp_line_graph_data = theme_data["LINE_GRAPH"];

    if (std::isnan(temperature)) {
        temperature = 0;
        if (is_shown(cpu_temp_text_data) || is_shown(cpu_temp_radial_data) || is_shown(cpu_temp_graph_data) ||
            is_shown(cpu_temp_line_graph_data)) {
            logger.warning("Your CPU temperature is not supported yet");
            hide(cpu_temp_text_data);
            hide(cpu_temp_radial_data);
            hide(cpu_temp_graph_data);
            hide(cpu_temp_line_graph_data);
        }
    }

    display_themed_temperature_value(cpu_temp_text_data, temperature);
    display_themed_progress_bar(cpu_temp_graph_data, temperature);
    display_themed_temperature_radial_bar(cpu_temp_radial_data, temperature);
    display_themed_line_graph(cpu_temp_line_graph_data, last_values_cpu_temperature);
}

void CPU::fan_speed()
{
    double fan_percent = CPU_FAN != "AUTO" ? sensors.cpu->fan_percent(CPU_FAN) : sensors.cpu->fan_percent();

    const YAML::Node theme_data = stats_node("CPU")["FAN_SPEED"];
    save_last_value(fan_percent, last_values_cpu_fan_speed, history_size(theme_data["LINE_GRAPH"]));

    const YAML::Node cpu_fan_text_data = theme_data["TEXT"];
    const YAML::Node cpu_fan_radial_data = theme_data["RADIAL"];
    const YAML::Node cpu_fan_graph_data = theme_data["GRAPH"];
    const YAML::Node cpu_fan_line_graph_data = theme_data["LINE_GRAPH"];

    if (std::isnan(fan_percent)) {
        fan_percent = 0;
        if (is_shown(cpu_fan_text_data) || is_shown(cpu_fan_radial_data) || is_shown(cpu_fan_graph_data) ||
            is_shown(cpu_fan_line_graph_data)) {
            logger.warning("Your CPU Fan sensor could not be auto-detected. Select it from Configuration UI.");
            hide(cpu_fan_text_data);
            hide(cpu_fan_radial_data);
            hide(cpu_fan_graph_data);
            hide(cpu_fan_line_graph_data);
        }
    }

    display_themed_percent_value(cpu_fan_text_data, fan_percent);
    display_themed_progress_bar(cpu_fan_graph_data, fan_percent);
    display_themed_percent_radial_bar(cpu_fan_radial_data, fan_percent);
    display_themed_line_graph(cpu_fan_line_graph_data, last_values_cpu_fan_speed);
}

// ---------------------------------------------------------------------------------------------------------------------
// Gpu

namespace {
std::vector<double> last_values_gpu_percentage;
std::vector<double> last_values_gpu_mem_percentage;
std::vector<double> last_values_gpu_temperature;
std::vector<double> last_values_gpu_fps;
std::vector<double> last_values_gpu_fan_speed;
std::vector<double> last_values_gpu_frequency;

// Hide the given theme items (with a warning) if the value is NaN: the sensor is not supported
void hide_if_unsupported(double &value, const std::vector<YAML::Node> &items, const std::string &warning)
{
    if (!std::isnan(value)) {
        return;
    }
    value = 0;
    bool shown = false;
    for (const auto &item: items) {
        shown |= is_shown(item);
    }
    if (shown) {
        logger.warning("{}", warning);
        for (const auto &item: items) {
            hide(item);
        }
    }
}
}  // namespace

void Gpu::stats()
{
    auto [load, memory_percentage, memory_used_mb, total_memory_mb, temperature] = sensors.gpu->stats();
    double fps = sensors.gpu->fps();
    double fan_percent = sensors.gpu->fan_percent();
    const double freq_ghz = sensors.gpu->frequency() / 1000;

    const YAML::Node theme_gpu_data = stats_node("GPU");

    save_last_value(load, last_values_gpu_percentage, history_size(theme_gpu_data["PERCENTAGE"]["LINE_GRAPH"]));
    save_last_value(memory_percentage, last_values_gpu_mem_percentage,
                    history_size(theme_gpu_data["MEMORY_PERCENT"]["LINE_GRAPH"]));
    save_last_value(temperature, last_values_gpu_temperature, history_size(theme_gpu_data["TEMPERATURE"]["LINE_GRAPH"]));
    save_last_value(fps, last_values_gpu_fps, history_size(theme_gpu_data["FPS"]["LINE_GRAPH"]));
    save_last_value(fan_percent, last_values_gpu_fan_speed, history_size(theme_gpu_data["FAN_SPEED"]["LINE_GRAPH"]));
    save_last_value(freq_ghz, last_values_gpu_frequency, history_size(theme_gpu_data["FREQUENCY"]["LINE_GRAPH"]));

    // ------------------------------- for backward compatibility only
    const YAML::Node gpu_mem_graph_data = theme_gpu_data["MEMORY"]["GRAPH"];
    const YAML::Node gpu_mem_radial_data = theme_gpu_data["MEMORY"]["RADIAL"];
    double memory_percentage_compat = memory_percentage;
    hide_if_unsupported(memory_percentage_compat, {gpu_mem_graph_data, gpu_mem_radial_data},
                        "Your GPU memory relative usage (%) is not supported yet");

    const YAML::Node gpu_mem_text_data = theme_gpu_data["MEMORY"]["TEXT"];
    double memory_used_mb_compat = memory_used_mb;
    hide_if_unsupported(memory_used_mb_compat, {gpu_mem_text_data}, "Your GPU memory absolute usage (M) is not supported yet");

    display_themed_progress_bar(gpu_mem_graph_data, memory_percentage_compat);
    display_themed_percent_radial_bar(gpu_mem_radial_data, memory_percentage_compat);
    display_themed_value(gpu_mem_text_data, std::to_string(to_int(memory_used_mb_compat)), 5, " M");
    // ------------------------------- end of backward compatibility only

    // GPU usage (%)
    const YAML::Node gpu_percent_graph_data = theme_gpu_data["PERCENTAGE"]["GRAPH"];
    const YAML::Node gpu_percent_radial_data = theme_gpu_data["PERCENTAGE"]["RADIAL"];
    const YAML::Node gpu_percent_text_data = theme_gpu_data["PERCENTAGE"]["TEXT"];
    const YAML::Node gpu_percent_line_graph_data = theme_gpu_data["PERCENTAGE"]["LINE_GRAPH"];
    hide_if_unsupported(load, {gpu_percent_graph_data, gpu_percent_text_data, gpu_percent_radial_data,
                               gpu_percent_line_graph_data}, "Your GPU load is not supported yet");

    display_themed_progress_bar(gpu_percent_graph_data, load);
    display_themed_percent_radial_bar(gpu_percent_radial_data, load);
    display_themed_percent_value(gpu_percent_text_data, load);
    display_themed_line_graph(gpu_percent_line_graph_data, last_values_gpu_percentage);

    // GPU mem. usage (%)
    const YAML::Node gpu_mem_percent_graph_data = theme_gpu_data["MEMORY_PERCENT"]["GRAPH"];
    const YAML::Node gpu_mem_percent_radial_data = theme_gpu_data["MEMORY_PERCENT"]["RADIAL"];
    const YAML::Node gpu_mem_percent_text_data = theme_gpu_data["MEMORY_PERCENT"]["TEXT"];
    const YAML::Node gpu_mem_percent_line_graph_data = theme_gpu_data["MEMORY_PERCENT"]["LINE_GRAPH"];
    hide_if_unsupported(memory_percentage, {gpu_mem_percent_graph_data, gpu_mem_percent_radial_data,
                                            gpu_mem_percent_text_data, gpu_mem_percent_line_graph_data},
                        "Your GPU memory relative usage (%) is not supported yet");

    display_themed_progress_bar(gpu_mem_percent_graph_data, memory_percentage);
    display_themed_percent_radial_bar(gpu_mem_percent_radial_data, memory_percentage);
    display_themed_percent_value(gpu_mem_percent_text_data, memory_percentage);
    display_themed_line_graph(gpu_mem_percent_line_graph_data, last_values_gpu_mem_percentage);

    // GPU mem. absolute usage (M)
    const YAML::Node gpu_mem_used_text_data = theme_gpu_data["MEMORY_USED"]["TEXT"];
    hide_if_unsupported(memory_used_mb, {gpu_mem_used_text_data},
                        "Your GPU memory absolute usage (M) is not supported yet");
    display_themed_value(gpu_mem_used_text_data, std::to_string(to_int(memory_used_mb)), 5, " M");

    // GPU mem. total memory (M)
    const YAML::Node gpu_mem_total_text_data = theme_gpu_data["MEMORY_TOTAL"]["TEXT"];
    hide_if_unsupported(total_memory_mb, {gpu_mem_total_text_data},
                        "Your GPU total memory capacity (M) is not supported yet");
    display_themed_value(gpu_mem_total_text_data, std::to_string(to_int(total_memory_mb)), 5, " M");

    // GPU temperature (°C)
    const YAML::Node gpu_temp_text_data = theme_gpu_data["TEMPERATURE"]["TEXT"];
    const YAML::Node gpu_temp_radial_data = theme_gpu_data["TEMPERATURE"]["RADIAL"];
    const YAML::Node gpu_temp_graph_data = theme_gpu_data["TEMPERATURE"]["GRAPH"];
    const YAML::Node gpu_temp_line_graph_data = theme_gpu_data["TEMPERATURE"]["LINE_GRAPH"];
    hide_if_unsupported(temperature, {gpu_temp_text_data, gpu_temp_radial_data, gpu_temp_graph_data,
                                      gpu_temp_line_graph_data}, "Your GPU temperature is not supported yet");

    display_themed_temperature_value(gpu_temp_text_data, temperature);
    display_themed_progress_bar(gpu_temp_graph_data, temperature);
    display_themed_temperature_radial_bar(gpu_temp_radial_data, temperature);
    display_themed_line_graph(gpu_temp_line_graph_data, last_values_gpu_temperature);

    // GPU FPS
    const YAML::Node gpu_fps_text_data = theme_gpu_data["FPS"]["TEXT"];
    const YAML::Node gpu_fps_radial_data = theme_gpu_data["FPS"]["RADIAL"];
    const YAML::Node gpu_fps_graph_data = theme_gpu_data["FPS"]["GRAPH"];
    const YAML::Node gpu_fps_line_graph_data = theme_gpu_data["FPS"]["LINE_GRAPH"];
    if (fps < 0) {
        fps = NaN;
    }
    hide_if_unsupported(fps, {gpu_fps_text_data, gpu_fps_radial_data, gpu_fps_graph_data, gpu_fps_line_graph_data},
                        "Your GPU FPS is not supported yet");

    display_themed_progress_bar(gpu_fps_graph_data, fps);
    display_themed_value(gpu_fps_text_data, std::to_string(to_int(fps)), 4, " FPS");
    display_themed_radial_bar(gpu_fps_radial_data, to_int(fps), std::to_string(to_int(fps)), 4, " FPS");
    display_themed_line_graph(gpu_fps_line_graph_data, last_values_gpu_fps);

    // GPU Fan Speed (%)
    const YAML::Node gpu_fan_text_data = theme_gpu_data["FAN_SPEED"]["TEXT"];
    const YAML::Node gpu_fan_radial_data = theme_gpu_data["FAN_SPEED"]["RADIAL"];
    const YAML::Node gpu_fan_graph_data = theme_gpu_data["FAN_SPEED"]["GRAPH"];
    const YAML::Node gpu_fan_line_graph_data = theme_gpu_data["FAN_SPEED"]["LINE_GRAPH"];
    hide_if_unsupported(fan_percent, {gpu_fan_text_data, gpu_fan_radial_data, gpu_fan_graph_data,
                                      gpu_fan_line_graph_data}, "Your GPU Fan Speed is not supported yet");

    display_themed_percent_value(gpu_fan_text_data, fan_percent);
    display_themed_progress_bar(gpu_fan_graph_data, fan_percent);
    display_themed_percent_radial_bar(gpu_fan_radial_data, fan_percent);
    display_themed_line_graph(gpu_fan_line_graph_data, last_values_gpu_fan_speed);

    // GPU Frequency (Ghz)
    const YAML::Node gpu_freq_text_data = theme_gpu_data["FREQUENCY"]["TEXT"];
    const YAML::Node gpu_freq_radial_data = theme_gpu_data["FREQUENCY"]["RADIAL"];
    const YAML::Node gpu_freq_graph_data = theme_gpu_data["FREQUENCY"]["GRAPH"];
    const YAML::Node gpu_freq_line_graph_data = theme_gpu_data["FREQUENCY"]["LINE_GRAPH"];
    const std::string freq_text = std::format("{:.2f}", freq_ghz);
    display_themed_value(gpu_freq_text_data, freq_text, 4, " GHz");
    display_themed_progress_bar(gpu_freq_graph_data, freq_ghz);
    display_themed_radial_bar(gpu_freq_radial_data, freq_ghz, freq_text, 4, " GHz");
    display_themed_line_graph(gpu_freq_line_graph_data, last_values_gpu_frequency);
}

bool Gpu::is_available()
{
    return sensors.gpu->is_available();
}

// ---------------------------------------------------------------------------------------------------------------------
// Memory

namespace {
std::vector<double> last_values_memory_swap;
std::vector<double> last_values_memory_virtual;
}

void Memory::stats()
{
    const YAML::Node memory_stats_theme_data = stats_node("MEMORY");

    const double swap_percent = sensors.memory->swap_percent();
    save_last_value(swap_percent, last_values_memory_swap,
                    history_size(memory_stats_theme_data["SWAP"]["LINE_GRAPH"]));
    display_themed_progress_bar(memory_stats_theme_data["SWAP"]["GRAPH"], swap_percent);
    display_themed_percent_radial_bar(memory_stats_theme_data["SWAP"]["RADIAL"], swap_percent);
    display_themed_line_graph(memory_stats_theme_data["SWAP"]["LINE_GRAPH"], last_values_memory_swap);

    const double virtual_percent = sensors.memory->virtual_percent();
    save_last_value(virtual_percent, last_values_memory_virtual,
                    history_size(memory_stats_theme_data["VIRTUAL"]["LINE_GRAPH"]));
    display_themed_progress_bar(memory_stats_theme_data["VIRTUAL"]["GRAPH"], virtual_percent);
    display_themed_percent_radial_bar(memory_stats_theme_data["VIRTUAL"]["RADIAL"], virtual_percent);
    display_themed_percent_value(memory_stats_theme_data["VIRTUAL"]["PERCENT_TEXT"], virtual_percent);
    display_themed_line_graph(memory_stats_theme_data["VIRTUAL"]["LINE_GRAPH"], last_values_memory_virtual);

    const int64_t used = sensors.memory->virtual_used();
    const int64_t free = sensors.memory->virtual_free();
    display_themed_value(memory_stats_theme_data["VIRTUAL"]["USED"], std::to_string(used / (1024 * 1024)), 5, " M");
    display_themed_value(memory_stats_theme_data["VIRTUAL"]["FREE"], std::to_string(free / (1024 * 1024)), 5, " M");
    display_themed_value(memory_stats_theme_data["VIRTUAL"]["TOTAL"], std::to_string((free + used) / (1024 * 1024)),
                         5, " M");
}

// ---------------------------------------------------------------------------------------------------------------------
// Disk

namespace {
std::vector<double> last_values_disk_usage;
}

void Disk::stats()
{
    const int64_t used = sensors.disk->disk_used();
    const int64_t free = sensors.disk->disk_free();

    const YAML::Node disk_theme_data = stats_node("DISK");

    const double disk_usage_percent = sensors.disk->disk_usage_percent();
    save_last_value(disk_usage_percent, last_values_disk_usage, history_size(disk_theme_data["USED"]["LINE_GRAPH"]));
    display_themed_progress_bar(disk_theme_data["USED"]["GRAPH"], disk_usage_percent);
    display_themed_percent_radial_bar(disk_theme_data["USED"]["RADIAL"], disk_usage_percent);
    display_themed_percent_value(disk_theme_data["USED"]["PERCENT_TEXT"], disk_usage_percent);
    display_themed_line_graph(disk_theme_data["USED"]["LINE_GRAPH"], last_values_disk_usage);

    display_themed_value(disk_theme_data["USED"]["TEXT"], std::to_string(used / 1000000000), 5, " G");
    display_themed_value(disk_theme_data["TOTAL"]["TEXT"], std::to_string((free + used) / 1000000000), 5, " G");
    display_themed_value(disk_theme_data["FREE"]["TEXT"], std::to_string(free / 1000000000), 5, " G");
}

// ---------------------------------------------------------------------------------------------------------------------
// Net

namespace {
std::vector<double> last_values_wlo_upload;
std::vector<double> last_values_wlo_download;
std::vector<double> last_values_eth_upload;
std::vector<double> last_values_eth_download;

void show_themed_total_data(const YAML::Node &theme_data, double amount)
{
    display_themed_value(theme_data, bytes2human(amount), 6);
}

void show_themed_tax_rate(const YAML::Node &theme_data, double rate)
{
    display_themed_value(theme_data, bytes2human(rate, "{:.1f} ", "/s"), 10);
}

void show_interface(const YAML::Node &card_theme_data, const sensors::Net::Stats &stats,
                    std::vector<double> &last_upload, std::vector<double> &last_download)
{
    save_last_value(stats.upload_rate, last_upload, history_size(card_theme_data["UPLOAD"]["LINE_GRAPH"]));
    show_themed_tax_rate(card_theme_data["UPLOAD"]["TEXT"], stats.upload_rate);
    show_themed_total_data(card_theme_data["UPLOADED"]["TEXT"], static_cast<double>(stats.uploaded));
    display_themed_line_graph(card_theme_data["UPLOAD"]["LINE_GRAPH"], last_upload);

    save_last_value(stats.download_rate, last_download, history_size(card_theme_data["DOWNLOAD"]["LINE_GRAPH"]));
    show_themed_tax_rate(card_theme_data["DOWNLOAD"]["TEXT"], stats.download_rate);
    show_themed_total_data(card_theme_data["DOWNLOADED"]["TEXT"], static_cast<double>(stats.downloaded));
    display_themed_line_graph(card_theme_data["DOWNLOAD"]["LINE_GRAPH"], last_download);
}
}  // namespace

void Net::stats()
{
    const YAML::Node net_theme_data = stats_node("NET");
    const YAML::Node interval_node = net_theme_data["INTERVAL"];
    const std::optional<double> interval = interval_node.IsDefined() && !interval_node.IsNull()
                                               ? std::optional<double>(interval_node.as<double>()) : std::nullopt;

    show_interface(net_theme_data["WLO"], sensors.net->stats(WLO_CARD, interval), last_values_wlo_upload,
                   last_values_wlo_download);
    show_interface(net_theme_data["ETH"], sensors.net->stats(ETH_CARD, interval), last_values_eth_upload,
                   last_values_eth_download);
}

// ---------------------------------------------------------------------------------------------------------------------
// Date

void Date::stats()
{
    std::time_t date_now;
    if (HW_SENSORS == "STATIC" || HW_SENSORS == "STUB") {
        // For static or stubbed sensors, use predefined date/time
        date_now = 1694014609;
    } else {
        date_now = std::time(nullptr);
    }

    const std::string lc_time = get_lc_time();

    const YAML::Node date_theme_data = stats_node("DATE");
    const YAML::Node day_theme_data = date_theme_data["DAY"]["TEXT"];
    if (is_shown(day_theme_data)) {
        const std::string date_format = config::get(day_theme_data, "FORMAT", "medium");
        display_themed_value(day_theme_data, format_datetime(date_now, date_format, lc_time, false));
    }

    const YAML::Node hour_theme_data = date_theme_data["HOUR"]["TEXT"];
    if (is_shown(hour_theme_data)) {
        const std::string time_format = config::get(hour_theme_data, "FORMAT", "medium");
        display_themed_value(hour_theme_data, format_datetime(date_now, time_format, lc_time, true));
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// SystemUptime

void SystemUptime::stats()
{
    long long uptimesec = 0;
    if (HW_SENSORS == "STATIC" || HW_SENSORS == "STUB") {
        // For static or stubbed sensors, use predefined uptime
        uptimesec = 4294036;
    } else {
        std::ifstream file("/proc/uptime");
        double seconds = 0;
        file >> seconds;
        uptimesec = static_cast<long long>(seconds);
    }

    // Same format as Python str(datetime.timedelta(seconds=...)): "49 days, 16:47:16" or "16:47:16"
    const long long days = uptimesec / 86400;
    const long long rest = uptimesec % 86400;
    std::string uptimeformatted = std::format("{}:{:02}:{:02}", rest / 3600, (rest % 3600) / 60, rest % 60);
    if (days > 0) {
        uptimeformatted = std::format("{} day{}, ", days, days == 1 ? "" : "s") + uptimeformatted;
    }

    const YAML::Node systemuptime_theme_data = stats_node("UPTIME");
    display_themed_value(systemuptime_theme_data["SECONDS"]["TEXT"], std::to_string(uptimesec));
    display_themed_value(systemuptime_theme_data["FORMATTED"]["TEXT"], uptimeformatted);
}

// ---------------------------------------------------------------------------------------------------------------------
// Custom

void Custom::stats()
{
    const YAML::Node custom_theme_data = stats_node("CUSTOM");
    if (!custom_theme_data.IsDefined() || !custom_theme_data.IsMap()) {
        return;
    }
    for (const auto &item: custom_theme_data) {
        const std::string custom_stat = item.first.as<std::string>();
        if (custom_stat == "INTERVAL") {
            continue;
        }

        // Get the custom sensor class from sensors_custom based on the class name
        auto &sources = sensors_custom::custom_data_sources();
        const auto source = sources.find(custom_stat);
        if (source == sources.end()) {
            logger.error("Error loading custom sensor class {} from sensors_custom: class not found", custom_stat);
            return;
        }
        const std::optional<double> numeric_value = source->second->as_numeric();
        std::optional<std::string> string_value = source->second->as_string();
        const std::optional<std::vector<double>> last_values = source->second->last_values();

        if (!string_value && numeric_value) {
            string_value = std::format("{}", *numeric_value);
        }

        const YAML::Node &stat_theme_data = item.second;

        // Display text
        if (const YAML::Node theme_data = stat_theme_data["TEXT"]; theme_data.IsDefined() && string_value) {
            display_themed_value(theme_data, string_value);
        }

        // Display graph from numeric value
        if (const YAML::Node theme_data = stat_theme_data["GRAPH"];
            theme_data.IsDefined() && numeric_value && !std::isnan(*numeric_value)) {
            display_themed_progress_bar(theme_data, *numeric_value);
        }

        // Display radial from numeric and text value
        if (const YAML::Node theme_data = stat_theme_data["RADIAL"];
            theme_data.IsDefined() && numeric_value && !std::isnan(*numeric_value) && string_value) {
            display_themed_radial_bar(theme_data, *numeric_value, std::format("{}", *numeric_value), 0, "",
                                      string_value);
        }

        // Display plot graph from histo values
        if (const YAML::Node theme_data = stat_theme_data["LINE_GRAPH"]; theme_data.IsDefined() && last_values) {
            display_themed_line_graph(theme_data, *last_values);
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// Weather

void Weather::stats()
{
    static const std::map<std::string, std::string> WEATHER_UNITS = {
        {"metric", "°C"}, {"imperial", "°F"}, {"standard", "°K"}};

    const YAML::Node weather_theme_data = stats_node("WEATHER");
    const YAML::Node wtemperature_theme_data = weather_theme_data["TEMPERATURE"]["TEXT"];
    const YAML::Node wfelt_theme_data = weather_theme_data["TEMPERATURE_FELT"]["TEXT"];
    const YAML::Node wupdatetime_theme_data = weather_theme_data["UPDATE_TIME"]["TEXT"];
    const YAML::Node wdescription_theme_data = weather_theme_data["WEATHER_DESCRIPTION"]["TEXT"];
    const YAML::Node whumidity_theme_data = weather_theme_data["HUMIDITY"]["TEXT"];

    const bool activate = is_shown(wtemperature_theme_data) || is_shown(wfelt_theme_data) ||
                          is_shown(wupdatetime_theme_data) || is_shown(wdescription_theme_data) ||
                          is_shown(whumidity_theme_data);
    if (!activate) {
        return;
    }

    std::optional<std::string> temp, feel, desc, time, humidity;
    if (HW_SENSORS == "STATIC" || HW_SENSORS == "STUB") {
        temp = "17.5°C";
        feel = "(17.2°C)";
        desc = "Cloudy";
        time = "@15:33";
        humidity = "45%";
    } else {
        // API Parameters
        const YAML::Node &cfg = config::CONFIG_DATA;
        const std::string lat = config::get(cfg["config"], "WEATHER_LATITUDE", "");
        const std::string lon = config::get(cfg["config"], "WEATHER_LONGITUDE", "");
        const std::string api_key = config::get(cfg["config"], "WEATHER_API_KEY", "");
        const std::string units = config::get(cfg["config"], "WEATHER_UNITS", "metric");
        const std::string lang = config::get(cfg["config"], "WEATHER_LANGUAGE", "en");
        const auto unit_it = WEATHER_UNITS.find(units);
        const std::string deg = unit_it != WEATHER_UNITS.end() ? unit_it->second : "°?";
        if (!api_key.empty()) {
            const std::string url = std::format("https://api.openweathermap.org/data/3.0/onecall?lat={}&lon={}"
                                                "&exclude=minutely,hourly,daily,alerts&appid={}&units={}&lang={}",
                                                lat, lon, api_key, units, lang);
            std::string body;
            long status_code = 0;
            CURL *curl = curl_easy_init();
            CURLcode res = CURLE_FAILED_INIT;
            if (curl) {
                curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
                curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write);
                curl_easy_setopt(curl, CURLOPT_WRITEDATA, &body);
                curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
                curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
                res = curl_easy_perform(curl);
                curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status_code);
                curl_easy_cleanup(curl);
            }
            try {
                if (res != CURLE_OK) {
                    throw std::runtime_error(curl_easy_strerror(res));
                }
                // JSON is parsed with the YAML parser (JSON is a subset of YAML)
                const YAML::Node data = YAML::Load(body);
                if (status_code == 200) {
                    const YAML::Node current = data["current"];
                    temp = std::format("{:.1f}{}", current["temp"].as<double>(), deg);
                    feel = std::format("({:.1f}{})", current["feels_like"].as<double>(), deg);
                    desc = capitalize(current["weather"][0]["description"].as<std::string>());
                    humidity = std::format("{:.0f}%", current["humidity"].as<double>());
                    const std::time_t now = std::time(nullptr);
                    std::tm tm{};
                    localtime_r(&now, &tm);
                    time = std::format("@{:02}:{:02}", tm.tm_hour, tm.tm_min);
                } else {
                    logger.error("Error {} fetching OpenWeatherMap API:", status_code);
                    desc = config::get(data, "message", "");
                }
            } catch (const std::exception &e) {
                logger.error("Error fetching OpenWeatherMap API: {}", e.what());
                desc = "Error fetching OpenWeatherMap API";
            }
        } else {
            logger.warning("No OpenWeatherMap API key provided in config.yaml");
            desc = "No OpenWeatherMap API key";
        }
    }

    // Display Temperature
    display_themed_value(wtemperature_theme_data, temp);
    // Display Temperature Felt
    display_themed_value(wfelt_theme_data, feel);
    // Display Update Time
    display_themed_value(wupdatetime_theme_data, time);
    // Display Humidity
    display_themed_value(whumidity_theme_data, humidity);
    // Display Weather Description (or error message)
    display_themed_value(wdescription_theme_data, desc);
}

// ---------------------------------------------------------------------------------------------------------------------
// Ping

namespace {
std::vector<double> last_values_ping;
}

void Ping::stats()
{
    const YAML::Node theme_data = stats_node("PING");

    double delay;
    if (HW_SENSORS == "STATIC") {
        // For static sensors, use predefined ping delay
        delay = 50;
    } else if (HW_SENSORS == "STUB") {
        // For stub sensors, use random ping delay
        static std::mt19937 generator(10);
        delay = std::uniform_int_distribution<int>(5, 120)(generator);
    } else {
        // No answer (timeout or error): NaN
        delay = ping(PING_DEST).value_or(NaN);
    }

    save_last_value(delay, last_values_ping, history_size(theme_data["LINE_GRAPH"]));

    // When there is no answer, the text displays "-" instead of a delay
    const std::string delay_text = std::isnan(delay) ? "-" : std::to_string(to_int(delay));
    display_themed_progress_bar(theme_data["GRAPH"], delay);
    display_themed_radial_bar(theme_data["RADIAL"], to_int(delay), delay_text, 6, "ms");
    display_themed_value(theme_data["TEXT"], delay_text, 6, "ms");
    display_themed_line_graph(theme_data["LINE_GRAPH"], last_values_ping);
}

}  // namespace stats
