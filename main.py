#!/usr/bin/env python3
# A simple Python manager for "Turing Smart Screen" 3.5" IPS USB-C display
# https://github.com/mathoudebine/turing-smart-screen-python

import os
import signal
import struct
from datetime import datetime
from time import sleep

import serial  # Install pyserial : pip install pyserial
from PIL import Image, ImageDraw, ImageFont  # Install PIL or Pillow

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux...
COM_PORT = "/dev/ttyACM0"
# COM_PORT = "COM5"

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 480


class Command:
    RESET = 101
    CLEAR = 102
    SCREEN_OFF = 108
    SCREEN_ON = 109
    SET_BRIGHTNESS = 110
    DISPLAY_BITMAP = 197


def SendReg(ser: serial.Serial, cmd: int, x: int, y: int, ex: int, ey: int):
    byteBuffer = bytearray(6)
    byteBuffer[0] = (x >> 2)
    byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
    byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
    byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
    byteBuffer[4] = (ey & 255)
    byteBuffer[5] = cmd
    ser.write(bytes(byteBuffer))


def Reset(ser: serial.Serial):
    SendReg(ser, Command.RESET, 0, 0, 0, 0)


def Clear(ser: serial.Serial):
    SendReg(ser, Command.CLEAR, 0, 0, 0, 0)


def ScreenOff(ser: serial.Serial):
    SendReg(ser, Command.SCREEN_OFF, 0, 0, 0, 0)


def ScreenOn(ser: serial.Serial):
    SendReg(ser, Command.SCREEN_ON, 0, 0, 0, 0)


def SetBrightness(ser: serial.Serial, level: int):
    # Level : 0 (brightest) - 255 (darkest)
    assert 255 >= level >= 0, 'Brightness level must be [0-255]'
    SendReg(ser, Command.SET_BRIGHTNESS, level, 0, 0, 0)


def DisplayPILImage(ser: serial.Serial, image: Image, x: int, y: int):
    image_height = image.size[1]
    image_width = image.size[0]

    assert image_height > 0, 'Image width must be > 0'
    assert image_width > 0, 'Image height must be > 0'

    SendReg(ser, Command.DISPLAY_BITMAP, x, y, x + image_width - 1, y + image_height - 1)

    pix = image.load()
    line = bytes()
    for h in range(image_height):
        for w in range(image_width):
            R = pix[w, h][0] >> 3
            G = pix[w, h][1] >> 2
            B = pix[w, h][2] >> 3

            rgb = (R << 11) | (G << 5) | B
            line += struct.pack('H', rgb)

            # Send image data by multiple of DISPLAY_WIDTH bytes
            if len(line) >= DISPLAY_WIDTH * 8:
                ser.write(line)
                line = bytes()

    # Write last line if needed
    if len(line) > 0:
        ser.write(line)

    sleep(0.01)  # Wait 10 ms after picture display


def DisplayBitmap(ser: serial.Serial, bitmap_path: str, x=0, y=0):
    image = Image.open(bitmap_path)
    DisplayPILImage(ser, image, x, y)


def DisplayText(ser: serial.Serial, text: str, x=0, y=0,
                font="roboto/Roboto-Regular.ttf",
                font_size=20,
                font_color=(0, 0, 0),
                background_color=(255, 255, 255),
                background_image: str = None):
    # Convert text to bitmap using PIL and display it
    # Provide the background image path to display text with transparent background

    assert len(text) > 0, 'Text must not be empty'
    assert font_size > 0, "Font size must be > 0"

    if background_image is None:
        # A text bitmap is created with max width/height by default : text with solid background
        text_image = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), background_color)
    else:
        # The text bitmap is created from provided background image : text with transparent background
        text_image = Image.open(background_image)

    # Draw text with specified color & font (also crop if text overflows display)
    font = ImageFont.truetype("./res/fonts/" + font, font_size)
    d = ImageDraw.Draw(text_image)
    d.text((x, y), text, font=font, fill=font_color)

    # Crop text bitmap to keep only the text
    left, top, text_width, text_height = d.textbbox((0,0), text, font=font)
    text_image = text_image.crop(box=(x, y, min(x + text_width, DISPLAY_WIDTH), min(y + text_height, DISPLAY_HEIGHT)))

    DisplayPILImage(ser, text_image, x, y)


def DisplayProgressBar(ser: serial.Serial, x: int, y: int, width: int, height: int, min_value=0, max_value=100,
                       value=50,
                       bar_color=(0, 0, 0),
                       bar_outline=True,
                       background_color=(255, 255, 255),
                       background_image: str = None):
    # Generate a progress bar and display it
    # Provide the background image path to display progress bar with transparent background

    assert x + width <= DISPLAY_WIDTH, 'Progress bar width exceeds display width'
    assert y + height <= DISPLAY_HEIGHT, 'Progress bar height exceeds display height'
    assert min_value <= value <= max_value, 'Progress bar value shall be between min and max'

    if background_image is None:
        # A bitmap is created with solid background
        bar_image = Image.new('RGB', (width, height), background_color)
    else:
        # A bitmap is created from provided background image
        bar_image = Image.open(background_image)

        # Crop bitmap to keep only the progress bar background
        bar_image = bar_image.crop(box=(x, y, x + width, y + height))

    # Draw progress bar
    bar_filled_width = value / (max_value - min_value) * width
    draw = ImageDraw.Draw(bar_image)
    draw.rectangle([0, 0, bar_filled_width-1, height-1], fill=bar_color, outline=bar_color)

    if bar_outline:
        # Draw outline
        draw.rectangle([0, 0, width-1, height-1], fill=None, outline=bar_color)

    DisplayPILImage(ser, bar_image, x, y)


stop = False

if __name__ == "__main__":

    def sighandler(signum, frame):
        global stop
        stop = True


    # Set the signal handlers, to send a complete frame to the LCD before exit
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    is_posix = os.name == 'posix'
    if is_posix:
        signal.signal(signal.SIGQUIT, sighandler)

    # Do not change COM port settings unless you know what you are doing
    lcd_comm = serial.Serial(COM_PORT, 115200, timeout=1, rtscts=1)

    # Clear screen (blank)
    Clear(lcd_comm)

    # Set brightness to max value
    SetBrightness(lcd_comm, 0)

    # Display sample picture
    DisplayBitmap(lcd_comm, "res/example.png")

    # Display sample text
    DisplayText(lcd_comm, "Basic text", 50, 100)

    # Display custom text with solid background
    DisplayText(lcd_comm, "Custom italic text", 5, 150,
                font="roboto/Roboto-Italic.ttf",
                font_size=30,
                font_color=(0, 0, 255),
                background_color=(255, 255, 0))

    # Display custom text with transparent background
    DisplayText(lcd_comm, "Transparent bold text", 5, 300,
                font="geforce/GeForce-Bold.ttf",
                font_size=30,
                font_color=(255, 255, 255),
                background_image="res/example.png")

    # Display text that overflows
    DisplayText(lcd_comm, "Text overflow!", 5, 430,
                font="roboto/Roboto-Bold.ttf",
                font_size=60,
                font_color=(255, 255, 255),
                background_image="res/example.png")

    # Display the current time and some progress bars as fast as possible
    bar_value = 0
    while not stop:
        DisplayText(lcd_comm, str(datetime.now().time()), 160, 2,
                    font="roboto/Roboto-Bold.ttf",
                    font_size=20,
                    font_color=(255, 0, 0),
                    background_image="res/example.png")

        DisplayProgressBar(lcd_comm, 10, 40,
                           width=140, height=30,
                           min_value=0, max_value=100, value=bar_value,
                           bar_color=(255, 255, 0), bar_outline=True,
                           background_image="res/example.png")

        DisplayProgressBar(lcd_comm, 160, 40,
                           width=140, height=30,
                           min_value=0, max_value=19, value=bar_value % 20,
                           bar_color=(0, 255, 0), bar_outline=False,
                           background_image="res/example.png")

        bar_value = (bar_value + 2) % 101

    lcd_comm.close()
