#!/usr/bin/env python
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
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

# theme-preview-generator.py: Run by GitHub actions on new commits, to generate a MarkDown page containing themes list
# and their associated preview

import os

import yaml


def get_themes(display_size: str):
    themes = []
    directory = 'res/themes/'
    for filename in os.listdir('res/themes'):
        dir = os.path.join(directory, filename)
        # checking if it is a directory
        if os.path.isdir(dir):
            # Check if a theme.yaml file exists
            theme = os.path.join(dir, 'theme.yaml')
            if os.path.isfile(theme):
                # Get display size from theme.yaml
                with open(theme, "rt", encoding='utf8') as stream:
                    theme_data = yaml.safe_load(stream)
                    if theme_data['display'].get("DISPLAY_SIZE", '3.5"') == display_size:
                        themes.append(filename)
    return sorted(themes, key=str.casefold)


def write_theme_previews_to_file(themes, file, size):
    file.write(f"\n## {size} themes\n")
    file.write("<table>")
    i = 0
    for theme in themes:
        file.write(
            f"<td>{theme}<img src=\"https://raw.githubusercontent.com/mathoudebine/turing-smart-screen-python/main/res/themes/{theme}/preview.png\" width=\"150\"/></td>")
        i = i + 1
        if i >= 5:
            file.write("</table><table>")
            i = 0
    file.write("</table>\n")


if __name__ == "__main__":
    themes21inch = get_themes('2.1"')
    themes3inch = get_themes('3.5"')
    themes5inch = get_themes('5"')
    themes88inch = get_themes('8.8"')

    with open("res/themes/themes.md", "w", encoding='utf-8') as file:
        file.write("<!--- This file is generated automatically by GitHub Actions, do not edit it! --->\n")
        file.write("\n")
        file.write("# Turing Smart Screen themes\n")
        file.write("\n")
        file.write("ℹ️ Click on a preview to view full size\n\n")
        file.write("[2.1\" themes](#21-themes)\n\n")
        file.write("[3.5\" themes](#35-themes)\n\n")
        file.write("[5\" themes](#5-themes)\n\n")
        file.write("[8.8\" themes](#88-themes)\n")

        write_theme_previews_to_file(themes21inch, file, "2.1\"")
        write_theme_previews_to_file(themes3inch, file, "3.5\"")
        write_theme_previews_to_file(themes5inch, file, "5\"")
        write_theme_previews_to_file(themes88inch, file, "8.8\"")
