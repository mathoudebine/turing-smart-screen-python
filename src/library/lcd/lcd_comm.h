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
// It renders text, bitmaps, progress bars, line graphs and radial progress bars into images, then the driver
// (subclass) sends the images to the screen with DisplayPILImage().

#pragma once

#include <condition_variable>
#include <deque>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <tuple>
#include <vector>

#include "library/lcd/color.h"
#include "library/lcd/font.h"
#include "library/lcd/image.h"
#include "library/lcd/serial_port.h"

enum class Orientation : int
{
    PORTRAIT = 0,
    LANDSCAPE = 2,
    REVERSE_PORTRAIT = 1,
    REVERSE_LANDSCAPE = 3,
};

// The screen resets itself when the program starts, so its COM port can disappear or change for a
// few seconds: opening it is retried instead of giving up (and exiting) on the first failure.
constexpr int SERIAL_OPEN_ATTEMPTS = 10;
constexpr int SERIAL_OPEN_RETRY_DELAY = 1;  // seconds

// Thread-safe FIFO of requests to send to the screen (like Python queue.Queue of (function, args) tuples)
class UpdateQueue
{
public:
    using Request = std::function<void()>;

    void put(Request request);

    // Wait for a request and remove it from the queue
    Request get();

    bool empty() const;

private:
    mutable std::mutex mutex;
    std::condition_variable not_empty;
    std::deque<Request> requests;
};

// Parameters of LcdComm::DisplayText()
struct TextOptions
{
    std::string text;
    int x = 0;
    int y = 0;
    int width = 0;
    int height = 0;
    std::string font = "./res/fonts/roboto-mono/RobotoMono-Regular.ttf";
    int font_size = 20;
    RGBColor font_color = {0, 0, 0};
    RGBColor background_color = {255, 255, 255};
    // Provide the background image path to display text with transparent background
    std::optional<std::string> background_image;
    std::string align = "left";
    std::string anchor = "la";
};

// Parameters of LcdComm::DisplayProgressBar()
struct ProgressBarOptions
{
    int x = 0;
    int y = 0;
    int width = 0;
    int height = 0;
    double min_value = 0;
    double max_value = 100;
    double value = 50;
    RGBColor bar_color = {0, 0, 0};
    bool bar_outline = true;
    RGBColor background_color = {255, 255, 255};
    // Provide the background image path to display progress bar with transparent background
    std::optional<std::string> background_image;
    bool reverse_direction = false;
};

// Parameters of LcdComm::DisplayLineGraph()
struct LineGraphOptions
{
    int x = 0;
    int y = 0;
    int width = 0;
    int height = 0;
    std::vector<double> values;  // NaN values are not plotted
    double min_value = 0;
    double max_value = 100;
    bool autoscale = false;
    RGBColor line_color = {0, 0, 0};
    int line_width = 2;
    bool graph_axis = true;
    RGBColor axis_color = {0, 0, 0};
    std::string axis_font = "./res/fonts/roboto/Roboto-Black.ttf";
    int axis_font_size = 10;
    RGBColor background_color = {255, 255, 255};
    // Provide the background image path to display plot graph with transparent background
    std::optional<std::string> background_image;
    std::string axis_minmax_format = "{:0.0f}";  // std::format syntax
};

// Parameters of LcdComm::DisplayRadialProgressBar()
struct RadialProgressBarOptions
{
    int xc = 0;
    int yc = 0;
    int radius = 0;
    int bar_width = 0;
    double min_value = 0;
    double max_value = 100;
    double angle_start = 0;
    double angle_end = 360;
    int angle_sep = 5;
    int angle_steps = 10;
    bool clockwise = true;
    double value = 50;
    // Text displayed in the center. If empty, the percentage is displayed
    std::optional<std::string> text;
    bool with_text = true;
    std::string font = "./res/fonts/roboto/Roboto-Black.ttf";
    int font_size = 20;
    RGBColor font_color = {0, 0, 0};
    RGBColor bar_color = {0, 0, 0};
    RGBColor background_color = {255, 255, 255};
    // Provide the background image path to display progress bar with transparent background
    std::optional<std::string> background_image;
    std::tuple<int, int, int, int> custom_bbox = {0, 0, 0, 0};
    std::pair<int, int> text_offset = {0, 0};
    RGBColor bar_background_color = {0, 0, 0};
    bool draw_bar_background = false;
    std::string bar_decoration;  // "" or "Ellipse"
};

class LcdComm
{
public:
    LcdComm(std::string com_port = "AUTO", int display_width = 320, int display_height = 480,
            UpdateQueue *update_queue = nullptr);
    virtual ~LcdComm();

    LcdComm(const LcdComm &) = delete;
    LcdComm &operator=(const LcdComm &) = delete;

    int get_width() const;
    int get_height() const;

    void openSerial();
    virtual void closeSerial();

    void serial_write(const std::vector<uint8_t> &data);
    std::vector<uint8_t> serial_read(size_t size);
    std::vector<uint8_t> serial_readall();
    void serial_flush_input();

    void WriteData(const std::vector<uint8_t> &byteBuffer);
    void SendLine(const std::vector<uint8_t> &line);
    void WriteLine(const std::vector<uint8_t> &line);
    std::vector<uint8_t> ReadData(size_t readSize);

    // To implement only for screens that use serial commands
    virtual std::optional<std::string> auto_detect_com_port();

    virtual void InitializeComm() = 0;
    virtual void Reset() = 0;
    virtual void Clear() = 0;
    virtual void ScreenOff() = 0;
    virtual void ScreenOn() = 0;
    virtual void SetBrightness(int level) = 0;
    virtual void SetBackplateLedColor(RGBColor led_color = {255, 255, 255});
    virtual void SetOrientation(Orientation orientation) = 0;
    virtual void DisplayPILImage(const Image &image, int x = 0, int y = 0, int image_width = 0,
                                 int image_height = 0) = 0;

    void DisplayBitmap(const std::string &bitmap_path, int x = 0, int y = 0, int width = 0, int height = 0);

    // Convert text to bitmap and display it
    void DisplayText(const TextOptions &options);

    // Generate a progress bar and display it
    void DisplayProgressBar(const ProgressBarOptions &options);

    // Generate a plot graph and display it
    void DisplayLineGraph(const LineGraphOptions &options);

    void DrawRadialDecoration(ImageDraw &draw, double angle, double radius, double width, RGBColor color = {0, 0, 0});

    // Generate a radial progress bar and display it
    void DisplayRadialProgressBar(const RadialProgressBarOptions &options);

    // Load image from the filesystem, or get from the cache if it has already been loaded previously
    Image open_image(const std::string &bitmap_path);

    std::shared_ptr<Font> open_font(const std::string &name, int size);

    std::unique_ptr<SerialPort> lcd_serial;

    // String containing absolute path to serial port e.g. "/dev/ttyACM1" or "AUTO" for auto-discovery
    // Ignored for USB HID screens
    std::string com_port;

    // Display always start in portrait orientation by default
    Orientation orientation = Orientation::PORTRAIT;
    // Display width in default orientation (portrait)
    int display_width;
    // Display height in default orientation (portrait)
    int display_height;

    // Queue containing the serial requests to send to the screen. An external thread should run to process requests
    // on the queue. If you want serial requests to be done in sequence, set it to nullptr
    UpdateQueue *update_queue;

    // Mutex to protect the queue in case a thread want to add multiple requests (e.g. image data) that should not be
    // mixed with other requests in-between
    std::mutex update_queue_mutex;

private:
    // Protects the caches below, used from several threads
    std::mutex cache_mutex;

    // Cache to store opened images, to avoid opening and loading from the filesystem every time
    std::map<std::string, Image> image_cache;

    // Cache to store opened fonts, to avoid opening and loading from the filesystem every time
    std::map<std::pair<std::string, int>, std::shared_ptr<Font>> font_cache;

    // Remember the bounding box drawn by the last DisplayText() call at a given (x, y) origin, so the
    // next call can redraw the union of the old and new areas and fully erase any previous text that is
    // narrower/shorter than what replaces it, regardless of font metrics ("ghosting" prevention).
    std::map<std::pair<int, int>, std::tuple<int, int, int, int>> text_bbox_cache;
};
