import logging
import os
import queue
import sys

import serial
import yaml
from serial.tools.list_ports import comports


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


def auto_detect_com_port():
    comports = serial.tools.list_ports.comports()
    auto_comport = None

    for comport in comports:
        if comport.serial_number == CONFIG_DATA['display']['SERIAL_NUMBER']:
            auto_comport = comport.device

    return auto_comport


PATH = sys.path[0]
CONFIG_DATA = load_yaml("config.yaml")

if CONFIG_DATA['config']['COM_PORT'] == 'AUTO':
    lcd_com_port = auto_detect_com_port()
    lcd_comm = serial.Serial(lcd_com_port, 115200, timeout=1, rtscts=1)
    print(f"Auto detected comm port: {lcd_com_port}")
else:
    lcd_com_port = CONFIG_DATA["config"]["COM_PORT"]
    print(f"Static comm port: {lcd_com_port}")
    lcd_comm = serial.Serial(lcd_com_port, 115200, timeout=1, rtscts=1)

update_queue = queue.Queue()
