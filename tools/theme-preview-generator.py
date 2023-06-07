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


def get_themes():
    themes = []
    directory = 'res/themes/'
    for filename in os.listdir('res/themes'):
        dir = os.path.join(directory, filename)
        # checking if it is a directory
        if os.path.isdir(dir):
            # Check if a theme.yaml file exists
            theme = os.path.join(dir, 'theme.yaml')
            if os.path.isfile(theme):
                themes.append(filename)
    return sorted(themes, key=str.casefold)


if __name__ == "__main__":
    themes = get_themes()

    with open("res/themes/themes.md", "w", encoding='utf-8') as file:
        file.write("<!--- This file is generated automatically bi GitHub Actions, do not edit it! --->\n")
        file.write("\n")
        file.write("<table cellspacing=\"0\" cellpadding=\"0\" style=\"border: none;\">")
        i = 0
        for theme in themes:
            file.write(f"<td><table cellspacing=\"0\" cellpadding=\"0\" style=\"border: none;\"><tr><th>{theme}</th></tr><tr><td><img src=\"https://raw.githubusercontent.com/mathoudebine/turing-smart-screen-python/main/res/themes/{theme}/preview.png\" width=\"150\"/></td></tr></table></td>")
            i = i + 1
            if i >= 5:
                file.write("</table><table cellspacing=\"0\" cellpadding=\"0\" style=\"border: none;\">")
                i = 0
        file.write("</table>\n")
