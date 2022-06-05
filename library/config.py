import logging

import yaml
import os
import sys
import serial
import queue


def load_yaml(configfile):
    if not os.path.exists(configfile):
        logging.critical("No YAML file found")
        exit()

    with open(configfile, "r") as stream:
        try:
            yamlconfig = yaml.safe_load(stream)
        except yaml.YAMLError:
            logging.critical("Failed loading YAML configuration file")
            exit()

        return yamlconfig


PATH = sys.path[0]
CONFIG_DATA = load_yaml("config.yaml")
lcd_comm = serial.Serial(CONFIG_DATA["config"]["COM_PORT"], 115200, timeout=1, rtscts=1)
update_queue = queue.Queue()
