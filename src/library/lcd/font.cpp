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

// TrueType font rendering with FreeType, replacing the subset of Pillow (PIL.ImageFont, ImageDraw.text/textbbox)
// used by the Python code.

#include "library/lcd/font.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

#include <ft2build.h>
#include FT_FREETYPE_H
#include <hb-ft.h>
#include <hb.h>

namespace {

// FreeType library instance shared by all fonts. FreeType calls that create/destroy faces are serialized.
std::mutex freetype_mutex;

FT_Library freetype_library()
{
    static FT_Library library = [] {
        FT_Library lib = nullptr;
        if (FT_Init_FreeType(&lib) != 0) {
            throw std::runtime_error("Cannot initialize FreeType library");
        }
        return lib;
    }();
    return library;
}

long floor_div64(long v) { return static_cast<long>(std::floor(v / 64.0)); }

long ceil_div64(long v) { return static_cast<long>(std::ceil(v / 64.0)); }

}  // namespace

Font::Font(const std::string &path, int size)
{
    std::lock_guard lock(freetype_mutex);
    FT_Face ft_face = nullptr;
    if (FT_New_Face(freetype_library(), path.c_str(), 0, &ft_face) != 0) {
        throw std::runtime_error("Cannot open font " + path);
    }
    if (FT_Set_Pixel_Sizes(ft_face, 0, static_cast<FT_UInt>(size)) != 0) {
        FT_Done_Face(ft_face);
        throw std::runtime_error("Cannot set size " + std::to_string(size) + " for font " + path);
    }
    face = ft_face;

    // Text shaping with HarfBuzz, using hinted glyph metrics like Pillow
    hb_font_t *font = hb_ft_font_create_referenced(ft_face);
    hb_ft_font_set_load_flags(font, FT_LOAD_DEFAULT);
    hb_font = font;
}

Font::~Font()
{
    std::lock_guard lock(freetype_mutex);
    hb_font_destroy(static_cast<hb_font_t *>(hb_font));
    FT_Done_Face(static_cast<FT_Face>(face));
}

Font::Layout Font::layout(const std::string &text) const
{
    auto ft_face = static_cast<FT_Face>(face);
    Layout result;

    hb_buffer_t *buffer = hb_buffer_create();
    hb_buffer_add_utf8(buffer, text.c_str(), static_cast<int>(text.size()), 0, -1);
    hb_buffer_guess_segment_properties(buffer);
    hb_shape(static_cast<hb_font_t *>(hb_font), buffer, nullptr, 0);

    unsigned int count = 0;
    const hb_glyph_info_t *infos = hb_buffer_get_glyph_infos(buffer, &count);
    const hb_glyph_position_t *positions = hb_buffer_get_glyph_positions(buffer, &count);

    long pen_x = 0;
    for (unsigned int i = 0; i < count; i++) {
        const FT_UInt index = infos[i].codepoint;
        const long glyph_x = pen_x + positions[i].x_offset;
        const long glyph_y = positions[i].y_offset;
        pen_x += positions[i].x_advance;

        if (FT_Load_Glyph(ft_face, index, FT_LOAD_DEFAULT) != 0) {
            continue;
        }
        const FT_Glyph_Metrics &m = ft_face->glyph->metrics;
        if (m.width > 0 && m.height > 0) {
            const long x_min = glyph_x + m.horiBearingX, x_max = x_min + m.width;
            const long y_max = glyph_y + m.horiBearingY, y_min = y_max - m.height;
            if (!result.has_ink) {
                result.ink_x_min = x_min;
                result.ink_x_max = x_max;
                result.ink_y_min = y_min;
                result.ink_y_max = y_max;
                result.has_ink = true;
            } else {
                result.ink_x_min = std::min(result.ink_x_min, x_min);
                result.ink_x_max = std::max(result.ink_x_max, x_max);
                result.ink_y_min = std::min(result.ink_y_min, y_min);
                result.ink_y_max = std::max(result.ink_y_max, y_max);
            }
        }
        result.glyphs.push_back({index, glyph_x, glyph_y});
    }
    hb_buffer_destroy(buffer);

    result.advance = pen_x;
    return result;
}

void Font::anchor_offset(const Layout &l, const std::string &anchor, long &x_anchor, long &y_anchor) const
{
    if (anchor.size() != 2) {
        throw std::invalid_argument("invalid anchor '" + anchor + "'");
    }
    const FT_Size_Metrics &metrics = static_cast<FT_Face>(face)->size->metrics;

    switch (anchor[0]) {
        case 'l': x_anchor = 0; break;
        case 'm': x_anchor = l.advance / 2; break;
        case 'r': x_anchor = l.advance; break;
        default: throw std::invalid_argument("invalid anchor '" + anchor + "'");
    }
    switch (anchor[1]) {
        case 'a': y_anchor = metrics.ascender; break;
        case 't': y_anchor = l.ink_y_max; break;
        case 'm': y_anchor = (metrics.ascender + metrics.descender) / 2; break;
        case 's': y_anchor = 0; break;
        case 'b': y_anchor = l.ink_y_min; break;
        case 'd': y_anchor = metrics.descender; break;
        default: throw std::invalid_argument("invalid anchor '" + anchor + "'");
    }
}

TextBox Font::textbbox(double x, double y, const std::string &text, const std::string &anchor) const
{
    std::lock_guard lock(mutex);
    const Layout l = layout(text);
    long x_anchor, y_anchor;
    anchor_offset(l, anchor, x_anchor, y_anchor);

    // Horizontally: from the text origin (or the ink if it goes further) to the advance width (or the ink).
    // Vertically: the ink extents.
    const long left = std::min(0L, l.has_ink ? l.ink_x_min : 0L) - x_anchor;
    const long right = std::max(l.advance, l.has_ink ? l.ink_x_max : 0L) - x_anchor;
    const long top = y_anchor - (l.has_ink ? l.ink_y_max : 0L);
    const long bottom = y_anchor - (l.has_ink ? l.ink_y_min : 0L);

    return {x + floor_div64(left), y + floor_div64(top), x + ceil_div64(right), y + ceil_div64(bottom)};
}

void Font::draw(Image &image, double x, double y, const std::string &text, RGBColor fill,
                const std::string &anchor) const
{
    std::lock_guard lock(mutex);
    auto ft_face = static_cast<FT_Face>(face);
    const Layout l = layout(text);
    long x_anchor, y_anchor;
    anchor_offset(l, anchor, x_anchor, y_anchor);

    const long origin_x = std::lround(x - x_anchor / 64.0);
    const long baseline = std::lround(y + y_anchor / 64.0);

    for (const auto &glyph: l.glyphs) {
        if (FT_Load_Glyph(ft_face, glyph.index, FT_LOAD_DEFAULT) != 0 ||
            FT_Render_Glyph(ft_face->glyph, FT_RENDER_MODE_NORMAL) != 0) {
            continue;
        }
        const FT_GlyphSlot slot = ft_face->glyph;
        const FT_Bitmap &bitmap = slot->bitmap;
        const long gx = origin_x + floor_div64(glyph.pen_x) + slot->bitmap_left;
        const long gy = baseline - floor_div64(glyph.pen_y) - slot->bitmap_top;

        for (unsigned int row = 0; row < bitmap.rows; row++) {
            for (unsigned int col = 0; col < bitmap.width; col++) {
                uint8_t coverage;
                if (bitmap.pixel_mode == FT_PIXEL_MODE_MONO) {
                    coverage = (bitmap.buffer[row * bitmap.pitch + col / 8] & (0x80 >> (col % 8))) ? 255 : 0;
                } else {
                    coverage = bitmap.buffer[row * bitmap.pitch + col];
                }
                image.blend(static_cast<int>(gx + col), static_cast<int>(gy + row), fill, coverage);
            }
        }
    }
}
