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

// RGB image and 2D drawing primitives, replacing the subset of Pillow (PIL.Image / PIL.ImageDraw) used by the
// Python code.

#include "library/lcd/image.h"

#include <algorithm>
#include <cmath>
#include <csetjmp>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <memory>
#include <stdexcept>

#include <jpeglib.h>
#include <png.h>

namespace {

bool has_png_signature(const std::string &path)
{
    std::ifstream file(path, std::ios::binary);
    unsigned char header[8] = {};
    file.read(reinterpret_cast<char *>(header), sizeof(header));
    return file.gcount() == 8 && png_sig_cmp(header, 0, 8) == 0;
}

struct JpegErrorManager
{
    jpeg_error_mgr pub;
    std::jmp_buf jump;
    char message[JMSG_LENGTH_MAX];
};

void jpeg_error_exit(j_common_ptr cinfo)
{
    auto *err = reinterpret_cast<JpegErrorManager *>(cinfo->err);
    (*cinfo->err->format_message)(cinfo, err->message);
    std::longjmp(err->jump, 1);
}

// Pillow bicubic filter
double bicubic_filter(double x)
{
    constexpr double a = -0.5;
    x = std::fabs(x);
    if (x < 1.0) {
        return ((a + 2.0) * x - (a + 3.0)) * x * x + 1.0;
    }
    if (x < 2.0) {
        return (((x - 5.0) * x + 8.0) * x - 4.0) * a;
    }
    return 0.0;
}

struct ResampleCoeffs
{
    int min;
    std::vector<double> weights;
};

// Same coefficients as Pillow's precompute_coeffs(), for a separable convolution
std::vector<ResampleCoeffs> precompute_coeffs(int in_size, int out_size)
{
    constexpr double filter_support = 2.0;
    const double scale = static_cast<double>(in_size) / out_size;
    const double filterscale = std::max(scale, 1.0);
    const double support = filter_support * filterscale;

    std::vector<ResampleCoeffs> coeffs(out_size);
    for (int xx = 0; xx < out_size; xx++) {
        const double center = (xx + 0.5) * scale;
        const int xmin = std::max(static_cast<int>(center - support + 0.5), 0);
        const int xmax = std::min(static_cast<int>(center + support + 0.5), in_size);
        auto &c = coeffs[xx];
        c.min = xmin;
        double total = 0.0;
        for (int x = xmin; x < xmax; x++) {
            const double w = bicubic_filter((x - center + 0.5) / filterscale);
            c.weights.push_back(w);
            total += w;
        }
        if (total != 0.0) {
            for (auto &w: c.weights) {
                w /= total;
            }
        }
    }
    return coeffs;
}

uint8_t clip8(double v)
{
    return static_cast<uint8_t>(std::clamp(std::lround(v), 0L, 255L));
}

double normalize_angle(double angle)
{
    angle = std::fmod(angle, 360.0);
    return angle < 0 ? angle + 360.0 : angle;
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// Image

Image::Image(int width, int height, RGBColor color) : width_(width), height_(height)
{
    if (width < 0 || height < 0) {
        throw std::invalid_argument("Image size must be >= 0");
    }
    pixels.resize(static_cast<size_t>(width) * height * 3);
    for (size_t i = 0; i < pixels.size(); i += 3) {
        pixels[i] = color.r;
        pixels[i + 1] = color.g;
        pixels[i + 2] = color.b;
    }
}

Image Image::open(const std::string &path)
{
    Image result;

    if (has_png_signature(path)) {
        png_image png{};
        png.version = PNG_IMAGE_VERSION;
        if (!png_image_begin_read_from_file(&png, path.c_str())) {
            throw std::runtime_error("Cannot open image " + path + ": " + png.message);
        }
        png.format = PNG_FORMAT_RGBA;
        std::vector<uint8_t> rgba(PNG_IMAGE_SIZE(png));
        if (!png_image_finish_read(&png, nullptr, rgba.data(), 0, nullptr)) {
            png_image_free(&png);
            throw std::runtime_error("Cannot read image " + path + ": " + png.message);
        }

        result.width_ = static_cast<int>(png.width);
        result.height_ = static_cast<int>(png.height);
        result.pixels.resize(static_cast<size_t>(result.width_) * result.height_ * 3);
        // Drop alpha channel, like Pillow does when converting/pasting a RGBA image into a RGB image
        for (size_t i = 0, j = 0; i < rgba.size(); i += 4, j += 3) {
            result.pixels[j] = rgba[i];
            result.pixels[j + 1] = rgba[i + 1];
            result.pixels[j + 2] = rgba[i + 2];
        }
        return result;
    }

    // Not a PNG file: try JPEG
    struct FileCloser
    {
        void operator()(FILE *f) const { std::fclose(f); }
    };
    std::unique_ptr<FILE, FileCloser> file(std::fopen(path.c_str(), "rb"));
    if (!file) {
        throw std::runtime_error("Cannot open image " + path + ": " + std::strerror(errno));
    }

    jpeg_decompress_struct cinfo{};
    JpegErrorManager err{};
    cinfo.err = jpeg_std_error(&err.pub);
    err.pub.error_exit = jpeg_error_exit;
    if (setjmp(err.jump)) {
        jpeg_destroy_decompress(&cinfo);
        throw std::runtime_error("Cannot read image " + path + ": " + err.message);
    }

    jpeg_create_decompress(&cinfo);
    jpeg_stdio_src(&cinfo, file.get());
    jpeg_read_header(&cinfo, TRUE);
    cinfo.out_color_space = JCS_RGB;
    jpeg_start_decompress(&cinfo);

    const int width = static_cast<int>(cinfo.output_width);
    const int height = static_cast<int>(cinfo.output_height);
    std::vector<uint8_t> pixels(static_cast<size_t>(width) * height * 3);
    while (cinfo.output_scanline < cinfo.output_height) {
        JSAMPROW row = pixels.data() + static_cast<size_t>(cinfo.output_scanline) * width * 3;
        jpeg_read_scanlines(&cinfo, &row, 1);
    }
    jpeg_finish_decompress(&cinfo);
    jpeg_destroy_decompress(&cinfo);

    result.width_ = width;
    result.height_ = height;
    result.pixels = std::move(pixels);
    return result;
}

void Image::save(const std::string &path) const
{
    png_image png{};
    png.version = PNG_IMAGE_VERSION;
    png.width = static_cast<png_uint_32>(width_);
    png.height = static_cast<png_uint_32>(height_);
    png.format = PNG_FORMAT_RGB;
    if (!png_image_write_to_file(&png, path.c_str(), 0, pixels.data(), 0, nullptr)) {
        throw std::runtime_error("Cannot save image " + path + ": " + png.message);
    }
}

RGBColor Image::getpixel(int x, int y) const
{
    if (x < 0 || y < 0 || x >= width_ || y >= height_) {
        throw std::out_of_range("Pixel out of image");
    }
    const size_t i = (static_cast<size_t>(y) * width_ + x) * 3;
    return {pixels[i], pixels[i + 1], pixels[i + 2]};
}

void Image::putpixel(int x, int y, RGBColor color)
{
    if (x < 0 || y < 0 || x >= width_ || y >= height_) {
        return;
    }
    const size_t i = (static_cast<size_t>(y) * width_ + x) * 3;
    pixels[i] = color.r;
    pixels[i + 1] = color.g;
    pixels[i + 2] = color.b;
}

void Image::blend(int x, int y, RGBColor color, uint8_t alpha)
{
    if (x < 0 || y < 0 || x >= width_ || y >= height_ || alpha == 0) {
        return;
    }
    const size_t i = (static_cast<size_t>(y) * width_ + x) * 3;
    auto mix = [alpha](uint8_t dst, uint8_t src) {
        return static_cast<uint8_t>((dst * (255 - alpha) + src * alpha + 127) / 255);
    };
    pixels[i] = mix(pixels[i], color.r);
    pixels[i + 1] = mix(pixels[i + 1], color.g);
    pixels[i + 2] = mix(pixels[i + 2], color.b);
}

Image Image::crop(int left, int top, int right, int bottom) const
{
    Image result(std::max(right - left, 0), std::max(bottom - top, 0), {0, 0, 0});
    for (int y = 0; y < result.height_; y++) {
        const int src_y = top + y;
        if (src_y < 0 || src_y >= height_) {
            continue;
        }
        const int x_start = std::max(0, -left);
        const int x_end = std::min(result.width_, width_ - left);
        if (x_end <= x_start) {
            continue;
        }
        std::memcpy(&result.pixels[(static_cast<size_t>(y) * result.width_ + x_start) * 3],
                    &pixels[(static_cast<size_t>(src_y) * width_ + left + x_start) * 3],
                    static_cast<size_t>(x_end - x_start) * 3);
    }
    return result;
}

Image Image::resize(int new_width, int new_height) const
{
    if (new_width <= 0 || new_height <= 0) {
        throw std::invalid_argument("Resized image size must be > 0");
    }
    if (new_width == width_ && new_height == height_) {
        return *this;
    }

    // Horizontal pass
    const auto hcoeffs = precompute_coeffs(width_, new_width);
    std::vector<double> tmp(static_cast<size_t>(new_width) * height_ * 3);
    for (int y = 0; y < height_; y++) {
        for (int x = 0; x < new_width; x++) {
            const auto &c = hcoeffs[x];
            double sum[3] = {0, 0, 0};
            for (size_t k = 0; k < c.weights.size(); k++) {
                const uint8_t *p = &pixels[(static_cast<size_t>(y) * width_ + c.min + k) * 3];
                for (int ch = 0; ch < 3; ch++) {
                    sum[ch] += p[ch] * c.weights[k];
                }
            }
            for (int ch = 0; ch < 3; ch++) {
                tmp[(static_cast<size_t>(y) * new_width + x) * 3 + ch] = clip8(sum[ch]);
            }
        }
    }

    // Vertical pass
    const auto vcoeffs = precompute_coeffs(height_, new_height);
    Image result(new_width, new_height);
    for (int y = 0; y < new_height; y++) {
        const auto &c = vcoeffs[y];
        for (int x = 0; x < new_width; x++) {
            double sum[3] = {0, 0, 0};
            for (size_t k = 0; k < c.weights.size(); k++) {
                const double *p = &tmp[((c.min + k) * new_width + x) * 3];
                for (int ch = 0; ch < 3; ch++) {
                    sum[ch] += p[ch] * c.weights[k];
                }
            }
            for (int ch = 0; ch < 3; ch++) {
                result.pixels[(static_cast<size_t>(y) * new_width + x) * 3 + ch] = clip8(sum[ch]);
            }
        }
    }
    return result;
}

void Image::paste(const Image &image, int x, int y)
{
    const int x_start = std::max(0, -x);
    const int x_end = std::min(image.width_, width_ - x);
    if (x_end <= x_start) {
        return;
    }
    for (int row = std::max(0, -y); row < image.height_ && y + row < height_; row++) {
        std::memcpy(&pixels[(static_cast<size_t>(y + row) * width_ + x + x_start) * 3],
                    &image.pixels[(static_cast<size_t>(row) * image.width_ + x_start) * 3],
                    static_cast<size_t>(x_end - x_start) * 3);
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// ImageDraw

void ImageDraw::rectangle(double x0d, double y0d, double x1d, double y1d, std::optional<RGBColor> fill,
                          std::optional<RGBColor> outline, int width)
{
    // Coordinates are truncated to integers, like Pillow does
    const int x0 = static_cast<int>(x0d), y0 = static_cast<int>(y0d);
    const int x1 = static_cast<int>(x1d), y1 = static_cast<int>(y1d);
    if (x1 < x0) {
        throw std::invalid_argument("x1 must be greater than or equal to x0");
    }
    if (y1 < y0) {
        throw std::invalid_argument("y1 must be greater than or equal to y0");
    }

    if (fill) {
        for (int y = y0; y <= y1; y++) {
            for (int x = x0; x <= x1; x++) {
                image.putpixel(x, y, *fill);
            }
        }
    }
    if (outline && width > 0) {
        for (int y = y0; y <= y1; y++) {
            for (int x = x0; x <= x1; x++) {
                if (x < x0 + width || x > x1 - width || y < y0 + width || y > y1 - width) {
                    image.putpixel(x, y, *outline);
                }
            }
        }
    }
}

void ImageDraw::draw_line_1px(int x0, int y0, int x1, int y1, RGBColor color)
{
    // Bresenham, both ends included
    const int dx = std::abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    const int dy = -std::abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    while (true) {
        image.putpixel(x0, y0, color);
        if (x0 == x1 && y0 == y1) {
            break;
        }
        const int e2 = 2 * err;
        if (e2 >= dy) {
            err += dy;
            x0 += sx;
        }
        if (e2 <= dx) {
            err += dx;
            y0 += sy;
        }
    }
}

void ImageDraw::line(const std::vector<PointF> &points, RGBColor fill, int width)
{
    for (size_t i = 0; i + 1 < points.size(); i++) {
        // Coordinates are truncated to integers, like Pillow does
        const int x0 = static_cast<int>(points[i].x), y0 = static_cast<int>(points[i].y);
        const int x1 = static_cast<int>(points[i + 1].x), y1 = static_cast<int>(points[i + 1].y);

        if (width <= 1) {
            draw_line_1px(x0, y0, x1, y1, fill);
            continue;
        }

        // Wide line: drawn as a polygon, with the same vertices computation as Pillow ImagingDrawWideLine
        const int dx = x1 - x0, dy = y1 - y0;
        if (dx == 0 && dy == 0) {
            image.putpixel(x0, y0, fill);
            continue;
        }
        const double big_hypotenuse = std::hypot(dx, dy);
        const double small_hypotenuse = (width - 1) / 2.0;
        const double ratio_max = std::ceil(small_hypotenuse) / big_hypotenuse;
        const double ratio_min = std::floor(small_hypotenuse) / big_hypotenuse;
        const double dxmin = std::floor(ratio_min * dy + 0.5), dxmax = std::floor(ratio_max * dy + 0.5);
        const double dymin = std::floor(ratio_min * dx + 0.5), dymax = std::floor(ratio_max * dx + 0.5);
        polygon({{x0 - dxmin, y0 + dymax}, {x1 - dxmin, y1 + dymax}, {x1 + dxmax, y1 - dymin}, {x0 + dxmax, y0 - dymin}},
                fill);
    }
}

void ImageDraw::polygon(const std::vector<PointF> &points, RGBColor fill)
{
    if (points.empty()) {
        return;
    }

    // Scanline fill, pixel centers at integer coordinates
    double min_y = points[0].y, max_y = points[0].y;
    for (const auto &p: points) {
        min_y = std::min(min_y, p.y);
        max_y = std::max(max_y, p.y);
    }
    for (int y = static_cast<int>(std::ceil(min_y)); y <= static_cast<int>(std::floor(max_y)); y++) {
        std::vector<double> xs;
        for (size_t i = 0; i < points.size(); i++) {
            const PointF &a = points[i], &b = points[(i + 1) % points.size()];
            if (a.y == b.y) {
                continue;
            }
            const double ymin = std::min(a.y, b.y), ymax = std::max(a.y, b.y);
            if (y < ymin || y >= ymax) {
                continue;
            }
            xs.push_back(a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y));
        }
        std::sort(xs.begin(), xs.end());
        for (size_t i = 0; i + 1 < xs.size(); i += 2) {
            for (int x = static_cast<int>(std::ceil(xs[i])); x <= static_cast<int>(std::floor(xs[i + 1])); x++) {
                image.putpixel(x, y, fill);
            }
        }
    }

    // Polygon edges are part of the polygon
    for (size_t i = 0; i < points.size(); i++) {
        const PointF &a = points[i], &b = points[(i + 1) % points.size()];
        draw_line_1px(static_cast<int>(std::lround(a.x)), static_cast<int>(std::lround(a.y)),
                      static_cast<int>(std::lround(b.x)), static_cast<int>(std::lround(b.y)), fill);
    }
}

void ImageDraw::ellipse_ring(double x0, double y0, double x1, double y1, int width, bool full_ellipse, double start,
                             double end, RGBColor color)
{
    // The box corners are included: the ellipse covers pixels x0..x1 and y0..y1
    const double cx = (x0 + x1 + 1.0) / 2.0, cy = (y0 + y1 + 1.0) / 2.0;
    const double rx = (x1 - x0 + 1.0) / 2.0, ry = (y1 - y0 + 1.0) / 2.0;
    if (rx <= 0 || ry <= 0) {
        return;
    }
    const double irx = rx - width, iry = ry - width;
    const bool has_hole = width > 0 && irx > 0 && iry > 0;

    // Same angle normalization as Pillow
    bool full_circle = full_ellipse;
    if (!full_circle) {
        if (end - start >= 360.0) {
            full_circle = true;
        } else {
            start = normalize_angle(start);
            end = normalize_angle(end);
            if (end < start) {
                end += 360.0;
            }
        }
    }

    for (int y = static_cast<int>(std::floor(y0)); y <= static_cast<int>(std::ceil(y1)); y++) {
        for (int x = static_cast<int>(std::floor(x0)); x <= static_cast<int>(std::ceil(x1)); x++) {
            const double dx = x + 0.5 - cx, dy = y + 0.5 - cy;
            if ((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) > 1.0) {
                continue;
            }
            if (has_hole && (dx * dx) / (irx * irx) + (dy * dy) / (iry * iry) < 1.0) {
                continue;
            }
            if (!full_circle) {
                const double angle = normalize_angle(std::atan2(dy, dx) * 180.0 / M_PI);
                const bool in_range = (angle >= start && angle <= end) ||
                                      (angle + 360.0 >= start && angle + 360.0 <= end);
                if (!in_range) {
                    continue;
                }
            }
            image.putpixel(x, y, color);
        }
    }
}

void ImageDraw::arc(double x0, double y0, double x1, double y1, double start, double end, RGBColor fill, int width)
{
    ellipse_ring(x0, y0, x1, y1, width, false, start, end, fill);
}

void ImageDraw::ellipse(double x0, double y0, double x1, double y1, std::optional<RGBColor> fill,
                        std::optional<RGBColor> outline, int width)
{
    if (fill) {
        // width 0 means no hole: the whole ellipse is filled
        ellipse_ring(x0, y0, x1, y1, 0, true, 0, 360, *fill);
    }
    if (outline && width > 0) {
        ellipse_ring(x0, y0, x1, y1, width, true, 0, 360, *outline);
    }
}
