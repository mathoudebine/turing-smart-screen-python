from typing import Union, Tuple

from PIL import ImageColor

RGBColor = Tuple[int, int, int]

# Color can be an RGB tuple (RGBColor), or a string in any of these formats:
# - "r, g, b" (e.g. "255, 0, 0"), as is found in the themes' yaml settings
# - any of the formats supported by PIL: https://pillow.readthedocs.io/en/stable/reference/ImageColor.html 
#
# For example, here are multiple ways to write the pure red color:
# - (255, 0, 0)
# - "255, 0, 0"
# - "#ff0000"
# - "red"
# - "hsl(0, 100%, 50%)"
Color = Union[str, RGBColor]

def parse_color(color: Color) -> RGBColor:
    # even if undocumented, let's be nice and accept a list in lieu of a tuple
    if isinstance(color, tuple) or isinstance(color, list):
        if len(color) != 3:
            raise ValueError("RGB color must have 3 values")
        return (int(color[0]), int(color[1]), int(color[2]))

    if not isinstance(color, str):
        raise ValueError("Color must be either an RGB tuple or a string")

    # Try to parse it as our custom "r, g, b" format
    rgb = color.split(',')
    if len(rgb) == 3:
        r, g, b = rgb
        try:
            rgbcolor = (int(r.strip()), int(g.strip()), int(b.strip()))
        except ValueError:
            # at least one element can't be converted to int, we continue to
            # try parsing as a PIL color
            pass
        else:
            return rgbcolor

    # fallback as a PIL color
    rgbcolor = ImageColor.getrgb(color)
    if len(rgbcolor) == 4:
        return (rgbcolor[0], rgbcolor[1], rgbcolor[2])
    return rgbcolor

