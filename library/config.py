# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022 Rollbacke
# Copyright (C) 2022 Ebag333
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

class Config:
    def __init__(self):
        self.MAIN_DIRECTORY = Path(__file__).parent.parent.resolve()
        self.FONTS_DIR = str(self.MAIN_DIRECTORY / "res" / "fonts") + "/"
        self.CONFIG_DATA = self.load_yaml(self.MAIN_DIRECTORY / "config.yaml")
        self.THEME_DEFAULT = self.load_yaml(self.MAIN_DIRECTORY / "res/themes/default.yaml")
        self.THEME_DATA: dict = {}
        # Load theme on import
        self.load_theme()
        # Queue containing the serial requests to send to the screen
        self.update_queue = queue.Queue()

    def load_yaml(self, configfile: str | Path):
        with open(configfile, "rt", encoding='utf8') as stream:
            yamlconfig = yaml.safe_load(stream)
            return yamlconfig

    def copy_default(self, default: dict, theme: dict):
        """recursively supply default values into a dict of dicts of dicts ...."""
        for k, v in default.items():
            if k not in theme:
                theme[k] = v
            if isinstance(v, dict):
                self.copy_default(default[k], theme[k])

    def load_theme(self):
        try:
            theme_path = Path("res/themes/" + self.CONFIG_DATA['config']['THEME'])
            logger.info("Loading theme %s from %s" % (self.CONFIG_DATA['config']['THEME'], theme_path / "theme.yaml"))
            self.THEME_DATA = self.load_yaml(self.MAIN_DIRECTORY / theme_path / "theme.yaml")
            self.THEME_DATA['PATH'] = str(self.MAIN_DIRECTORY / theme_path) + "/"
        except:
            logger.error("Theme not found or contains errors!")
            try:
                sys.exit(0)
            except:
                os._exit(0)

        self.copy_default(self.THEME_DEFAULT, self.THEME_DATA)

    def check_theme_compatible(self, display_size: str):
        # Check if theme is compatible with hardware revision
        if display_size != self.THEME_DATA['display'].get("DISPLAY_SIZE", '3.5"'):
            logger.error("The selected theme " + self.CONFIG_DATA['config'][
                'THEME'] + " is not compatible with your display revision " + self.CONFIG_DATA["display"]["REVISION"])
            try:
                sys.exit(0)
            except:
                os._exit(0)

config = Config()