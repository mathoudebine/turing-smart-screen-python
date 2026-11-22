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

// C++ port of library/lcd/lcd_comm.py: base class of all LCD screen drivers.

#include "library/lcd/lcd_comm.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <format>
#include <stdexcept>
#include <thread>

#include "library/log.h"

namespace {

// Replaces Python "assert": the error is reported as an exception
void check(bool condition, const std::string &message)
{
    if (!condition) {
        throw std::invalid_argument(message);
    }
}

// Python modulo operator on floats (result has the sign of the divisor)
double pymod(double a, double b)
{
    const double r = std::fmod(a, b);
    return (r != 0 && ((r < 0) != (b < 0))) ? r + b : r;
}

// Rounding of DrawRadialDecoration(): halfway cases are rounded towards the circle center
double round_to_center(double v, double direction)
{
    double int_part;
    if (std::modf(v, &int_part) == 0.5) {
        return direction > 0 ? std::floor(v) : std::ceil(v);
    }
    return std::floor(v + 0.5);
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// UpdateQueue

void UpdateQueue::put(Request request)
{
    {
        std::lock_guard lock(mutex);
        requests.push_back(std::move(request));
    }
    not_empty.notify_one();
}

UpdateQueue::Request UpdateQueue::get()
{
    std::unique_lock lock(mutex);
    not_empty.wait(lock, [this] { return !requests.empty(); });
    Request request = std::move(requests.front());
    requests.pop_front();
    return request;
}

std::optional<UpdateQueue::Request> UpdateQueue::get(std::chrono::milliseconds timeout)
{
    std::unique_lock lock(mutex);
    if (!not_empty.wait_for(lock, timeout, [this] { return !requests.empty(); })) {
        return std::nullopt;
    }
    Request request = std::move(requests.front());
    requests.pop_front();
    return request;
}

bool UpdateQueue::empty() const
{
    std::lock_guard lock(mutex);
    return requests.empty();
}

// ---------------------------------------------------------------------------------------------------------------------
// LcdComm

LcdComm::LcdComm(std::string com_port_, int display_width_, int display_height_, UpdateQueue *update_queue_)
    : com_port(std::move(com_port_)), display_width(display_width_), display_height(display_height_),
      update_queue(update_queue_)
{
}

LcdComm::~LcdComm() = default;

int LcdComm::get_width() const
{
    if (orientation == Orientation::PORTRAIT || orientation == Orientation::REVERSE_PORTRAIT) {
        return display_width;
    }
    return display_height;
}

int LcdComm::get_height() const
{
    if (orientation == Orientation::PORTRAIT || orientation == Orientation::REVERSE_PORTRAIT) {
        return display_height;
    }
    return display_width;
}

void LcdComm::openSerial()
{
    // com_port is kept as configured ("AUTO" or a port name): on AUTO the port is
    // detected again at every attempt, since it can change while the screen resets.
    for (int attempt = 1; attempt <= SERIAL_OPEN_ATTEMPTS; attempt++) {
        std::string port = com_port;
        if (port == "AUTO") {
            const auto detected = auto_detect_com_port();
            if (!detected) {
                logger.warning("Cannot find COM port automatically, retrying ({}/{})", attempt, SERIAL_OPEN_ATTEMPTS);
                std::this_thread::sleep_for(std::chrono::seconds(SERIAL_OPEN_RETRY_DELAY));
                continue;
            }
            port = *detected;
            logger.debug("Auto detected COM port: {}", port);
        } else {
            logger.debug("Static COM port: {}", port);
        }

        try {
            lcd_serial = std::make_unique<SerialPort>(port, 115200, 1.0, true);
            return;
        } catch (const SerialException &e) {
            logger.warning("Cannot open COM port {}: {} - retrying ({}/{})", port, e.what(), attempt,
                           SERIAL_OPEN_ATTEMPTS);
            std::this_thread::sleep_for(std::chrono::seconds(SERIAL_OPEN_RETRY_DELAY));
        }
    }

    logger.error("Cannot open COM port after {} attempts. If the screen is connected, run "
                 "Configuration again and select the COM port manually", SERIAL_OPEN_ATTEMPTS);
    std::_Exit(1);
}

void LcdComm::closeSerial()
{
    if (lcd_serial) {
        lcd_serial->close();
    }
}

void LcdComm::serial_write(const std::vector<uint8_t> &data)
{
    if (!lcd_serial) {
        throw SerialException("Serial port is not open");
    }
    lcd_serial->write(data);
}

std::vector<uint8_t> LcdComm::serial_read(size_t size)
{
    if (!lcd_serial) {
        throw SerialException("Serial port is not open");
    }
    return lcd_serial->read(size);
}

std::vector<uint8_t> LcdComm::serial_readall()
{
    if (!lcd_serial) {
        throw SerialException("Serial port is not open");
    }
    return lcd_serial->readall();
}

void LcdComm::serial_flush_input()
{
    if (lcd_serial) {
        lcd_serial->reset_input_buffer();
    }
}

void LcdComm::WriteData(const std::vector<uint8_t> &byteBuffer)
{
    WriteLine(byteBuffer);
}

void LcdComm::SendLine(const std::vector<uint8_t> &line)
{
    if (update_queue) {
        // Queue the request. Mutex is locked by caller to queue multiple lines
        update_queue->put([this, line] { WriteLine(line); });
    } else {
        // If no queue for async requests: do request now
        WriteLine(line);
    }
}

void LcdComm::WriteLine(const std::vector<uint8_t> &line)
{
    try {
        serial_write(line);
    } catch (const SerialTimeoutException &) {
        // We timed-out trying to write to our device, slow things down.
        logger.warning("(Write line) Too fast! Slow down!");
    } catch (const SerialException &) {
        // Error writing data to device: close and reopen serial port, try to write again
        logger.error("SerialException: Failed to send serial data to device. Closing and reopening COM port before "
                     "retrying once.");
        closeSerial();
        std::this_thread::sleep_for(std::chrono::seconds(1));
        openSerial();
        serial_write(line);
    }
}

std::vector<uint8_t> LcdComm::ReadData(size_t readSize)
{
    try {
        return serial_read(readSize);
    } catch (const SerialTimeoutException &) {
        // We timed-out trying to read from our device, slow things down.
        logger.warning("(Read data) Too fast! Slow down!");
        return {};
    } catch (const SerialException &) {
        // Error reading data from device: close and reopen serial port, try to read again
        logger.error("SerialException: Failed to read serial data from device. Closing and reopening COM port before "
                     "retrying once.");
        closeSerial();
        std::this_thread::sleep_for(std::chrono::seconds(1));
        openSerial();
        return serial_read(readSize);
    }
}

std::optional<std::string> LcdComm::auto_detect_com_port()
{
    return std::nullopt;
}

void LcdComm::SetBackplateLedColor(RGBColor)
{
}

void LcdComm::DisplayBitmap(const std::string &bitmap_path, int x, int y, int width, int height)
{
    Image image = open_image(bitmap_path);

    // Resize the picture if custom width/height provided
    if (width != 0 && height != 0) {
        if (width != image.width() || height != image.height()) {
            image = image.resize(width, height);
        }
    }

    DisplayPILImage(image, x, y, width, height);
}

void LcdComm::DisplayText(const TextOptions &options)
{
    // Convert text to bitmap using FreeType and display it
    // Provide the background image path to display text with transparent background
    const std::string &text = options.text;
    int x = options.x, y = options.y, width = options.width, height = options.height;
    const std::string &anchor = options.anchor;

    check(x <= get_width(), std::format("Text \"{}\" X coordinate {} must be <= display width {}", text, x,
                                        get_width()));
    check(y <= get_height(), std::format("Text \"{}\" Y coordinate {} must be <= display height {}", text, y,
                                         get_height()));
    check(!text.empty(), "Text must not be empty");
    check(options.font_size > 0, "Font size must be > 0");

    // If only width is specified, assume height based on font size (one-line text)
    if (width > 0 && height == 0) {
        height = options.font_size;
    }

    Image text_image;
    if (!options.background_image) {
        // A text bitmap is created with max width/height by default : text with solid background
        text_image = Image(get_width(), get_height(), options.background_color);
    } else {
        // The text bitmap is created from provided background image : text with transparent background
        text_image = open_image(*options.background_image);
    }

    // Get text bounding box
    const auto ttfont = open_font(options.font, options.font_size);

    int left, top, right, bottom;
    if (width == 0 || height == 0) {
        const TextBox box = ttfont->textbbox(x, y, text, anchor);

        // textbbox may return float values, which is not good for the bitmap operations below.
        // Let's extend the bounding box to the next whole pixel in all directions
        left = static_cast<int>(std::floor(box.left));
        top = static_cast<int>(std::floor(box.top));
        right = static_cast<int>(std::ceil(box.right));
        bottom = static_cast<int>(std::ceil(box.bottom));

        // Union with the area drawn last time at this same origin, so a new value that is narrower/shorter
        // than the previous one still gets its old pixels repainted with the background (prevents ghosting
        // of stale glyph fragments, independent of font metrics).
        std::lock_guard lock(cache_mutex);
        const auto bbox_key = std::make_pair(x, y);
        const auto prev = text_bbox_cache.find(bbox_key);
        const auto new_bbox = std::make_tuple(left, top, right, bottom);
        if (prev != text_bbox_cache.end()) {
            const auto [prev_left, prev_top, prev_right, prev_bottom] = prev->second;
            left = std::min(left, prev_left);
            top = std::min(top, prev_top);
            right = std::max(right, prev_right);
            bottom = std::max(bottom, prev_bottom);
        }
        text_bbox_cache[bbox_key] = new_bbox;
    } else {
        left = x;
        top = y;
        right = x + width;
        bottom = y + height;

        if (anchor.starts_with("m")) {
            x = (right + left) / 2;
        } else if (anchor.starts_with("r")) {
            x = right;
        } else {
            x = left;
        }

        if (anchor.ends_with("m")) {
            y = (bottom + top) / 2;
        } else if (anchor.ends_with("b")) {
            y = bottom;
        } else {
            y = top;
        }
    }

    // Draw text onto the background image with specified color & font
    ttfont->draw(text_image, x, y, text, options.font_color, anchor);

    // Restrict the dimensions if they overflow the display size
    left = std::max(left, 0);
    top = std::max(top, 0);
    right = std::min(right, get_width());
    bottom = std::min(bottom, get_height());

    // Crop text bitmap to keep only the text
    text_image = text_image.crop(left, top, right, bottom);

    DisplayPILImage(text_image, left, top);
}

void LcdComm::DisplayProgressBar(const ProgressBarOptions &o)
{
    // Generate a progress bar and display it
    // Provide the background image path to display progress bar with transparent background
    const int x = o.x, y = o.y, width = o.width, height = o.height;

    check(x <= get_width(), "Progress bar X coordinate must be <= display width");
    check(y <= get_height(), "Progress bar Y coordinate must be <= display height");
    check(x + width <= get_width(), "Progress bar width exceeds display width");
    check(y + height <= get_height(), "Progress bar height exceeds display height");

    // Don't let the set value exceed our min or max value, this is bad :)
    double value = o.value;
    if (o.value < o.min_value) {
        value = o.min_value;
    } else if (o.max_value < o.value) {
        value = o.max_value;
    }

    check(o.min_value <= value && value <= o.max_value, "Progress bar value shall be between min and max");

    Image bar_image;
    if (!o.background_image) {
        // A bitmap is created with solid background
        bar_image = Image(width, height, o.background_color);
    } else {
        // A bitmap is created from provided background image
        bar_image = open_image(*o.background_image);

        // Crop bitmap to keep only the progress bar background
        bar_image = bar_image.crop(x, y, x + width, y + height);
    }

    // Draw progress bar. Fill has to be computed from the offset into [min_value, max_value], not the raw value;
    // otherwise a bar with min_value > 0 (e.g. a 25..95 temperature bar) is filled by the wrong fraction.
    double bar_filled_width = 0, bar_filled_height = 0;
    if (width > height) {
        bar_filled_width = ((value - o.min_value) / (o.max_value - o.min_value) * width) - 1;
        if (bar_filled_width < 0) {
            bar_filled_width = 0;
        }
    } else {
        bar_filled_height = ((value - o.min_value) / (o.max_value - o.min_value) * height) - 1;
        if (bar_filled_height < 0) {
            bar_filled_height = 0;
        }
    }
    ImageDraw draw(bar_image);

    // most common setting
    double x1 = 0, y1 = 0, x2 = width - 1, y2 = height - 1;

    if (width > height) {
        if (o.reverse_direction) {
            x1 = width - 1 - bar_filled_width;
        } else {
            x2 = bar_filled_width;
        }
    } else {
        if (o.reverse_direction) {
            y2 = bar_filled_height;
        } else {
            y1 = height - 1 - bar_filled_height;
        }
    }
    draw.rectangle(x1, y1, x2, y2, o.bar_color, o.bar_color);

    if (o.bar_outline) {
        // Draw outline
        draw.rectangle(0, 0, width - 1, height - 1, std::nullopt, o.bar_color);
    }

    DisplayPILImage(bar_image, x, y);
}

void LcdComm::DisplayLineGraph(const LineGraphOptions &o)
{
    // Generate a plot graph and display it
    // Provide the background image path to display plot graph with transparent background
    const int x = o.x, y = o.y, width = o.width, height = o.height;
    double min_value = o.min_value, max_value = o.max_value;

    check(x <= get_width(), "Progress bar X coordinate must be <= display width");
    check(y <= get_height(), "Progress bar Y coordinate must be <= display height");
    check(x + width <= get_width(), "Progress bar width exceeds display width");
    check(y + height <= get_height(), "Progress bar height exceeds display height");
    check(!o.values.empty(), "Line graph must have at least one value");

    Image graph_image;
    if (!o.background_image) {
        // A bitmap is created with solid background
        graph_image = Image(width, height, o.background_color);
    } else {
        // A bitmap is created from provided background image
        graph_image = open_image(*o.background_image);

        // Crop bitmap to keep only the plot graph background
        graph_image = graph_image.crop(x, y, x + width, y + height);
    }

    // if autoscale is enabled, define new min/max value to "zoom" the graph
    if (o.autoscale) {
        double trueMin = max_value;
        double trueMax = min_value;
        for (double value: o.values) {
            if (!std::isnan(value)) {
                if (trueMin > value) {
                    trueMin = value;
                }
                if (trueMax < value) {
                    trueMax = value;
                }
            }
        }

        if (trueMin != max_value && trueMax != min_value) {
            min_value = std::max(trueMin - 5, min_value);
            max_value = std::min(trueMax + 5, max_value);
        }
    }

    const double step = static_cast<double>(width) / o.values.size();
    // pre compute yScale multiplier value
    const double yScale = (max_value - min_value) != 0 ? (height / (max_value - min_value)) : 0;

    std::vector<PointF> plots;
    int count = 0;
    for (double value: o.values) {
        if (!std::isnan(value)) {
            // Don't let the set value exceed our min or max value, this is bad :)
            if (value < min_value) {
                value = min_value;
            } else if (max_value < value) {
                value = max_value;
            }

            check(min_value <= value && value <= max_value, "Plot point value shall be between min and max");

            plots.push_back({count * step, height - (value - min_value) * yScale});

            count += 1;
        }
    }

    // Draw plot graph
    ImageDraw draw(graph_image);
    draw.line(plots, o.line_color, o.line_width);

    if (o.graph_axis) {
        // Draw axis
        draw.line({{0, static_cast<double>(height - 1)}, {static_cast<double>(width - 1), static_cast<double>(height - 1)}},
                  o.axis_color);
        draw.line({{0, 0}, {0, static_cast<double>(height - 1)}}, o.axis_color);

        // Draw Legend
        draw.line({{0, 0}, {1, 0}}, o.axis_color);
        const auto ttfont = open_font(o.axis_font, o.axis_font_size);

        std::string text = std::vformat(o.axis_minmax_format, std::make_format_args(max_value));
        TextBox box = ttfont->getbbox(text);
        ttfont->draw(graph_image, 2, 0 - box.top, text, o.axis_color);

        text = std::vformat(o.axis_minmax_format, std::make_format_args(min_value));
        box = ttfont->getbbox(text);
        ttfont->draw(graph_image, width - 1 - box.right, height - 2 - box.bottom, text, o.axis_color);
    }

    DisplayPILImage(graph_image, x, y);
}

void LcdComm::DrawRadialDecoration(ImageDraw &draw, double angle, double radius, double width, RGBColor color)
{
    const double i_cos = std::cos(angle * M_PI / 180);
    const double i_sin = std::sin(angle * M_PI / 180);
    const double x_f = round_to_center((i_cos * (radius - width / 2)) + radius, i_cos);
    const double y_f = round_to_center((i_sin * (radius - width / 2)) + radius, i_sin);
    draw.ellipse(x_f - width / 2, y_f - width / 2, x_f + width / 2, y_f - 1 + width / 2 - 1, color, color, 1);
}

void LcdComm::DisplayRadialProgressBar(const RadialProgressBarOptions &o)
{
    // Generate a radial progress bar and display it
    // Provide the background image path to display progress bar with transparent background
    const int xc = o.xc, yc = o.yc, radius = o.radius, bar_width = o.bar_width;
    const double min_value = o.min_value, max_value = o.max_value;
    double angle_start = o.angle_start, angle_end = o.angle_end;
    const int angle_sep = o.angle_sep, angle_steps = o.angle_steps;

    if (pymod(angle_start, 361) == pymod(angle_end, 361)) {
        if (o.clockwise) {
            angle_start += 0.1;
        } else {
            angle_end += 0.1;
        }
    }

    check(xc - radius >= 0 && xc + radius <= get_width(), "Radial is out of screen (left/right)");
    check(yc - radius >= 0 && yc + radius <= get_height(), "Radial is out of screen (up/down)");
    check(0 < bar_width && bar_width <= radius,
          std::format("Radial linewidth is {}, must be > 0 and <= radius", bar_width));
    check(pymod(angle_end, 361) != pymod(angle_start, 361),
          std::format("Invalid angles values, start = {}, end = {}", angle_start, angle_end));
    check(angle_sep >= 0, "Provide an angle_sep value >= 0");
    check(angle_steps > 0, "Provide an angle_step value > 0");
    check(angle_sep * angle_steps < 360, "Given angle_sep and angle_steps values are not correctly set");

    // Don't let the set value exceed our min or max value, this is bad :)
    double value = o.value;
    if (value < min_value) {
        value = min_value;
    } else if (max_value < value) {
        value = max_value;
    }

    check(min_value <= value && value <= max_value, "Radial value shall be between min and max");

    const int diameter = 2 * radius;
    Image bar_image;
    if (!o.background_image) {
        // A bitmap is created with solid background
        bar_image = Image(diameter, diameter, o.background_color);
    } else {
        // A bitmap is created from provided background image
        bar_image = open_image(*o.background_image);

        // Crop bitmap to keep only the progress bar background
        bar_image = bar_image.crop(xc - radius, yc - radius, xc + radius, yc + radius);
    }

    // Draw progress bar
    const double pct = (value - min_value) / (max_value - min_value);
    ImageDraw draw(bar_image);
    const double d = diameter - 1;

    // Arc angles use
    //  . 3 o'clock for 0
    //  . clockwise from angle start to angle end
    angle_start = pymod(angle_start, 361);
    angle_end = pymod(angle_end, 361);

    if (o.clockwise) {
        const double ecart = angle_end < angle_start ? 360 - angle_start + angle_end : angle_end - angle_start;

        // draw bar background
        if (o.draw_bar_background) {
            draw.arc(0, 0, d, d, angle_start, angle_start + ecart, o.bar_background_color, bar_width);
        }

        // draw bar decoration
        if (o.bar_decoration == "Ellipse") {
            DrawRadialDecoration(draw, angle_end, radius, bar_width, o.bar_background_color);
            DrawRadialDecoration(draw, angle_start, radius, bar_width, o.bar_color);
            DrawRadialDecoration(draw, angle_start + pct * ecart, radius, bar_width, o.bar_color);
        }

        if (angle_sep == 0) {
            // solid bar case
            draw.arc(0, 0, d, d, angle_start, angle_start + pct * ecart, o.bar_color, bar_width);
        } else {
            // discontinued bar case
            const double angleE = angle_start + pct * ecart;
            const double angle_complet = ecart / angle_steps;
            const int etapes = static_cast<int>((angleE - angle_start) / angle_complet);
            for (int i = 0; i < etapes; i++) {
                draw.arc(0, 0, d, d, angle_start + i * angle_complet, angle_start + (i + 1) * angle_complet - angle_sep,
                         o.bar_color, bar_width);
            }

            draw.arc(0, 0, d, d, angle_start + etapes * angle_complet, angleE, o.bar_color, bar_width);
        }
    } else {
        const double ecart = angle_end < angle_start ? angle_start - angle_end : 360 - angle_end + angle_start;

        // draw bar background
        if (o.draw_bar_background) {
            draw.arc(0, 0, d, d, angle_start - ecart, angle_start, o.bar_background_color, bar_width);
        }

        // draw bar decoration
        if (o.bar_decoration == "Ellipse") {
            DrawRadialDecoration(draw, angle_end, radius, bar_width, o.bar_background_color);
            DrawRadialDecoration(draw, angle_start, radius, bar_width, o.bar_color);
            DrawRadialDecoration(draw, angle_start - pct * ecart, radius, bar_width, o.bar_color);
        }

        if (angle_sep == 0) {
            // solid bar case
            draw.arc(0, 0, d, d, angle_start - pct * ecart, angle_start, o.bar_color, bar_width);
        } else {
            // discontinued bar case
            const double angleS = angle_start - pct * ecart;
            const double angle_complet = ecart / angle_steps;
            const int etapes = static_cast<int>((angle_start - angleS) / angle_complet);
            for (int i = 0; i < etapes; i++) {
                draw.arc(0, 0, d, d, angle_start - (i + 1) * angle_complet + angle_sep, angle_start - i * angle_complet,
                         o.bar_color, bar_width);
            }

            draw.arc(0, 0, d, d, angleS, angle_start - etapes * angle_complet, o.bar_color, bar_width);
        }
    }

    // Draw text
    if (o.with_text) {
        const std::string text = o.text ? *o.text : std::format("{}%", static_cast<int>(pct * 100 + .5));
        const auto ttfont = open_font(o.font, o.font_size);
        const TextBox box = ttfont->getbbox(text);
        const double w = box.right - box.left, h = box.bottom - box.top;
        ttfont->draw(bar_image, radius - w / 2 + o.text_offset.first, radius - box.top - h / 2 + o.text_offset.second,
                     text, o.font_color);
    }

    const auto [bx0, by0, bx1, by1] = o.custom_bbox;
    if (bx0 != 0 || by0 != 0 || bx1 != 0 || by1 != 0) {
        bar_image = bar_image.crop(bx0, by0, bx1, by1);
    }

    DisplayPILImage(bar_image, xc - radius + bx0, yc - radius + by0);
}

Image LcdComm::open_image(const std::string &bitmap_path)
{
    std::lock_guard lock(cache_mutex);
    auto it = image_cache.find(bitmap_path);
    if (it == image_cache.end()) {
        logger.debug("Bitmap {} is now loaded in the cache", bitmap_path);
        it = image_cache.emplace(bitmap_path, Image::open(bitmap_path)).first;
    }
    return it->second;
}

std::shared_ptr<Font> LcdComm::open_font(const std::string &name, int size)
{
    std::lock_guard lock(cache_mutex);
    const auto key = std::make_pair(name, size);
    auto it = font_cache.find(key);
    if (it == font_cache.end()) {
        it = font_cache.emplace(key, std::make_shared<Font>(name, size)).first;
    }
    return it->second;
}
