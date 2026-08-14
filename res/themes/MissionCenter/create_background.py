#!/usr/bin/env python3
"""
Mission Center Theme Background Generator - V2 (Fixed)
Clean dark theme without accent lines
For Turing Smart Screen 3.5" Landscape (480x320)
"""

from PIL import Image, ImageDraw
import os

# Screen dimensions
WIDTH = 480
HEIGHT = 320

# Color palette
COLORS = {
    'bg_dark': (20, 22, 28),      # Dark background
    'bg_panel': (32, 34, 44),     # Panel background
    'bg_graph': (26, 28, 36),     # Graph area
    'border': (55, 58, 70),       # Panel borders
    'grid': (42, 45, 55),         # Grid lines
}


def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    """Draw a rounded rectangle"""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_grid(draw, x, y, w, h, color):
    """Draw subtle grid lines"""
    # 3 horizontal lines
    for i in range(1, 4):
        ly = y + (h * i // 4)
        draw.line([(x, ly), (x + w, ly)], fill=color, width=1)
    # 5 vertical lines
    for i in range(1, 6):
        lx = x + (w * i // 6)
        draw.line([(lx, y), (lx, y + h)], fill=color, width=1)


def create_background():
    img = Image.new('RGB', (WIDTH, HEIGHT), COLORS['bg_dark'])
    draw = ImageDraw.Draw(img)

    # Panel layout
    margin = 4
    gap = 4
    panel_w = (WIDTH - margin * 2 - gap) // 2   # 234
    panel_h = (HEIGHT - margin * 2 - gap) // 2  # 154

    panels = [
        (margin, margin),                           # CPU
        (margin + panel_w + gap, margin),           # GPU
        (margin, margin + panel_h + gap),           # RAM
        (margin + panel_w + gap, margin + panel_h + gap),  # NET
    ]

    for px, py in panels:
        # Panel background
        draw_rounded_rect(
            draw,
            (px, py, px + panel_w, py + panel_h),
            radius=6,
            fill=COLORS['bg_panel'],
            outline=COLORS['border'],
            width=1
        )

        # Graph area (leave space for header:24px and footer:30px)
        gx = px + 6
        gy = py + 26
        gw = panel_w - 12
        gh = panel_h - 58  # 96px for graph

        # Graph background
        draw_rounded_rect(
            draw,
            (gx, gy, gx + gw, gy + gh),
            radius=4,
            fill=COLORS['bg_graph']
        )

        # Grid inside graph
        draw_grid(draw, gx + 2, gy + 2, gw - 4, gh - 4, COLORS['grid'])

    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'background.png')
    img.save(output_path, 'PNG')
    print(f"Saved: {output_path}")
    print(f"Panel: {panel_w}x{panel_h}, Graph area: Y+26, H=96")


if __name__ == '__main__':
    create_background()
