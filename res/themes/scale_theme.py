#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
scale_theme.py — Rescale a turing-smart-screen theme YAML to a new resolution.

Usage:
    python scale_theme.py theme.yaml output.yaml --from 480x800 --to 800x1280
    python scale_theme.py theme.yaml output.yaml --from 800x480 --to 1280x800
"""

import sys
import re
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Keys that hold X / Y coordinates or dimensions to rescale
# ---------------------------------------------------------------------------
X_KEYS   = {"X", "RADIUS"}          # scaled by x_factor
Y_KEYS   = {"Y"}                     # scaled by y_factor
W_KEYS   = {"WIDTH"}                 # scaled by x_factor
H_KEYS   = {"HEIGHT"}                # scaled by y_factor
FS_KEYS  = {"FONT_SIZE", "AXIS_FONT_SIZE"}  # scaled by avg factor


def parse_resolution(res: str) -> tuple[int, int]:
    """Parse 'WxH' string into (width, height)."""
    match = re.fullmatch(r"(\d+)[xX×](\d+)", res.strip())
    if not match:
        raise ValueError(f"Invalid resolution format '{res}'. Expected WxH (e.g. 800x480).")
    return int(match.group(1)), int(match.group(2))


def scale_value(value: int | float, factor: float) -> int:
    """Apply factor and round to nearest integer."""
    return round(value * factor)


def process_lines(lines: list[str], fx: float, fy: float) -> list[str]:
    """
    Walk through YAML lines and rescale numeric values for known keys.
    Handles both  `KEY: value`  and  `WIDTH: value`  forms.
    Preserves comments, indentation, and all other content exactly.
    """
    favg = (fx + fy) / 2
    result = []

    for line in lines:
        # Match lines like:  [indent]KEY: number[optional comment]
        m = re.match(r"^(\s*)(\w+)(\s*:\s*)(-?\d+(?:\.\d+)?)(.*)", line)
        if m:
            indent, key, sep, raw_val, rest = m.groups()
            val = float(raw_val)

            if key in X_KEYS:
                new_val = scale_value(val, fx)
            elif key in Y_KEYS:
                new_val = scale_value(val, fy)
            elif key in W_KEYS:
                new_val = scale_value(val, fx)
            elif key in H_KEYS:
                new_val = scale_value(val, fy)
            elif key in FS_KEYS:
                new_val = scale_value(val, favg)
            else:
                result.append(line)
                continue

            # Preserve original int/float representation
            if "." in raw_val:
                result.append(f"{indent}{key}{sep}{float(new_val)}{rest}\n")
            else:
                result.append(f"{indent}{key}{sep}{new_val}{rest}\n")
        else:
            # Handle  PATH / background dims in static_images block:
            #   WIDTH: 800  →  already caught above
            # Also handle DISPLAY_SIZE (ignored as per spec):
            result.append(line)

    return result


def scale_theme(src: Path, dst: Path, src_res: str, dst_res: str) -> None:
    sw, sh = parse_resolution(src_res)
    dw, dh = parse_resolution(dst_res)

    fx = dw / sw
    fy = dh / sh

    print(f"Source      : {src}")
    print(f"Destination : {dst}")
    print(f"From        : {sw}×{sh}")
    print(f"To          : {dw}×{dh}")
    print(f"X factor    : {fx:.6f}   ({sw} → {dw})")
    print(f"Y factor    : {fy:.6f}   ({sh} → {dh})")
    print(f"Font factor : {(fx+fy)/2:.6f}  (average)")

    lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
    scaled = process_lines(lines, fx, fy)
    dst.write_text("".join(scaled), encoding="utf-8")

    print(f"\nDone — written to {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rescale a turing-smart-screen theme YAML to a new resolution."
    )
    parser.add_argument("input",  type=Path, help="Source theme.yaml")
    parser.add_argument("output", type=Path, help="Output theme.yaml")
    parser.add_argument("--from", dest="src_res", required=True,
                        metavar="WxH", help="Original resolution, e.g. 480x800")
    parser.add_argument("--to",   dest="dst_res", required=True,
                        metavar="WxH", help="Target resolution,   e.g. 800x1280")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    scale_theme(args.input, args.output, args.src_res, args.dst_res)


if __name__ == "__main__":
    main()
