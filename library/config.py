# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022-2023  Rollbacke
# Copyright (C) 2022-2023  Ebag333
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

import os
import queue
import sys
from pathlib import Path
import yaml

from library.log import logger


def load_yaml(configfile):
    with open(configfile, "rt", encoding='utf8') as stream:
        yamlconfig = yaml.safe_load(stream)
        return yamlconfig


PATH = sys.path[0]
MAIN_DIRECTORY = Path(__file__).parent.parent.resolve()
FONTS_DIR = str(MAIN_DIRECTORY / "res" / "fonts") + "/"
CONFIG_DATA = load_yaml(MAIN_DIRECTORY / "config.yaml")
THEME_DEFAULT = load_yaml(MAIN_DIRECTORY / "res/themes/default.yaml")
THEME_DATA = None


def copy_default(default, theme):
    """recursively supply default values into a dict of dicts of dicts ...."""
    for k, v in default.items():
        if k not in theme:
            theme[k] = v
        if type(v) == type({}):
            copy_default(default[k], theme[k])


def load_theme():
    global THEME_DATA
    try:
        theme_path = Path("res/themes/" + CONFIG_DATA['config']['THEME'])
        logger.info("Loading theme %s from %s" % (CONFIG_DATA['config']['THEME'], theme_path / "theme.yaml"))
        THEME_DATA = load_yaml(MAIN_DIRECTORY / theme_path / "theme.yaml")
        THEME_DATA['PATH'] = str(MAIN_DIRECTORY / theme_path) + "/"
    except:
        logger.error("Theme not found or contains errors!")
        try:
            sys.exit(0)
        except:
            os._exit(0)

    copy_default(THEME_DEFAULT, THEME_DATA)


def check_theme_compatible(display_size: str):
    # Check if theme is compatible with hardware revision
    if display_size != THEME_DATA['display'].get("DISPLAY_SIZE", '3.5"'):
        logger.error("The selected theme " + CONFIG_DATA['config'][
            'THEME'] + " is not compatible with your display revision " + CONFIG_DATA["display"]["REVISION"])
        try:
            sys.exit(0)
        except:
            os._exit(0)


# Load theme on import
load_theme()

# Queue containing the serial requests to send to the screen
update_queue = queue.Queue()
