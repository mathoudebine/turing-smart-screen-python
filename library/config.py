import os
import queue
import sys

import yaml

from library.log import logger

PNIC_BEFORE = ""

def load_yaml(configfile):
    with open(configfile, "r") as stream:
        yamlconfig = yaml.safe_load(stream)
        return yamlconfig


PATH = sys.path[0]
CONFIG_DATA = load_yaml("config.yaml")

try:
    theme_path = "res/themes/" + CONFIG_DATA['config']['THEME'] + "/"
    logger.info("Loading theme %s from %s" % (CONFIG_DATA['config']['THEME'], theme_path + "theme.yaml"))
    THEME_DATA = load_yaml(theme_path + "theme.yaml")
    THEME_DATA['PATH'] = theme_path
except:
    logger.error("Theme not found or contains errors!")
    try:
        sys.exit(0)
    except:
        os._exit(0)

# Queue containing the serial requests to send to the screen
update_queue = queue.Queue()
