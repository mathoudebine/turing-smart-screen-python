# SPDX-License-Identifier: GPL-3.0-or-later
from typing import Union, Tuple

from PIL import ImageColor

RGBColor = Tuple[int, int, int]
RGBAColor = Tuple[int, int, int, int]

# Color can be an RGB tuple (RGBColor), RGBA tuple (RGBAColor), or a string in any of these formats:
# - "r, g, b" (e.g. "255, 0, 0"), as is found in the themes' yaml settings
# - "r, g, b, a" (e.g. "255, 0, 0, 128") for RGBA with alpha channel
# - any of the formats supported by PIL: https://pillow.readthedocs.io/en/stable/reference/ImageColor.html
#
# For example, here are multiple ways to write the pure red color:
# - (255, 0, 0)
# - "255, 0, 0"
# - "#ff0000"
# - "red"
# - "hsl(0, 100%, 50%)"
Color = Union[str, RGBColor, RGBAColor]


def parse_color(color: Color, allow_alpha: bool = False) -> Union[RGBColor, RGBAColor]:
    # even if undocumented, let's be nice and accept a list in lieu of a tuple
    if isinstance(color, tuple) or isinstance(color, list):
        if len(color) == 3:
            return (int(color[0]), int(color[1]), int(color[2]))
        elif len(color) == 4 and allow_alpha:
            return (int(color[0]), int(color[1]), int(color[2]), int(color[3]))
        elif len(color) == 4:
            # Strip alpha if not allowed
            return (int(color[0]), int(color[1]), int(color[2]))
        else:
            raise ValueError("Color must have 3 or 4 values")

    if not isinstance(color, str):
        raise ValueError("Color must be either an RGB(A) tuple or a string")

    # Try to parse it as our custom "r, g, b" or "r, g, b, a" format
    components = color.split(',')
    if len(components) == 3:
        r, g, b = components
        try:
            rgbcolor = (int(r.strip()), int(g.strip()), int(b.strip()))
        except ValueError:
            # at least one element can't be converted to int, we continue to
            # try parsing as a PIL color
            pass
        else:
            return rgbcolor
    elif len(components) == 4:
        r, g, b, a = components
        try:
            if allow_alpha:
                return (int(r.strip()), int(g.strip()), int(b.strip()), int(a.strip()))
            else:
                return (int(r.strip()), int(g.strip()), int(b.strip()))
        except ValueError:
            # at least one element can't be converted to int, we continue to
            # try parsing as a PIL color
            pass

    # fallback as a PIL color
    rgbcolor = ImageColor.getrgb(color)
    if len(rgbcolor) == 4 and not allow_alpha:
        return (rgbcolor[0], rgbcolor[1], rgbcolor[2])
    return rgbcolor

