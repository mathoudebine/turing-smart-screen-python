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

"""Locate the YAML configuration file used by the tools.

Resolution happens at import time in library.config (which loads the file as an
import side effect), so every entry-point script honours ``--config`` /
``TURING_CONFIG_FILE`` without having to parse arguments before importing the
library. This module is dependency-free (stdlib only) and must stay free of
import side effects so configure.py can use it without pulling in the rest of
the library.
"""

import os
from pathlib import Path
from typing import List, Mapping, Optional

# Environment variable selecting the configuration file, used when no
# --config/-c command-line option is given (handy for services/launchers).
CONFIG_FILE_ENV_VAR = "TURING_CONFIG_FILE"

# Command-line option selecting the configuration file (exact tokens only:
# --config, --config=value, -c value). Kept in sync with the argparse
# declarations of the entry-point scripts.
CONFIG_LONG_OPTION = "--config"
CONFIG_SHORT_OPTION = "-c"


class ConfigPathError(Exception):
    """The selected configuration path is unusable; the message names the reason."""


def _option_value(argv: List[str]) -> Optional[str]:
    # Return the value passed via --config/-c on the command line, or None.
    # Scanning stops at a bare "--" (argparse convention: the rest is not ours).
    index = 1
    while index < len(argv):
        token = argv[index]
        if token == "--":
            break
        if token in (CONFIG_LONG_OPTION, CONFIG_SHORT_OPTION):
            if index + 1 >= len(argv):
                raise ConfigPathError(f"{token} requires a file path")
            return argv[index + 1]
        if token.startswith(CONFIG_LONG_OPTION + "="):
            return token[len(CONFIG_LONG_OPTION) + 1:]
        index += 1
    return None


def resolve_config_path(argv: List[str], environ: Mapping[str, str], default_path: Path) -> Path:
    """Resolve which configuration file to use.

    Precedence: --config/-c option > TURING_CONFIG_FILE environment variable >
    default_path (the file shipped next to the program, preserving the historic
    behavior when neither is set).

    Raises ConfigPathError (naming the path and reason) when the selected file
    is empty, missing, not a regular file or not readable.
    """
    raw = _option_value(list(argv))
    source = "command line"
    if raw is None:
        raw = environ.get(CONFIG_FILE_ENV_VAR, "").strip()
        source = CONFIG_FILE_ENV_VAR
    elif not raw.strip():
        raise ConfigPathError("no file path given")
    if not raw.strip():
        # Nothing selected: the default must still be usable, same as before.
        path = Path(default_path)
        _validate(path, source="default location")
        return path

    path = Path(raw.strip()).expanduser()
    _validate(path, source=source)
    return path


def _validate(path: Path, source: str) -> None:
    if not str(path):
        raise ConfigPathError("no file path given")
    try:
        exists = path.exists()
    except OSError as e:
        raise ConfigPathError(f"'{path}' ({source}) cannot be checked: {e}")
    if not exists:
        raise ConfigPathError(f"'{path}' ({source}) does not exist")
    if path.is_dir():
        raise ConfigPathError(f"'{path}' ({source}) is a directory, not a configuration file")
    if not path.is_file():
        raise ConfigPathError(f"'{path}' ({source}) is not a regular file")
    if not os.access(str(path), os.R_OK):
        raise ConfigPathError(f"'{path}' ({source}) is not readable")
