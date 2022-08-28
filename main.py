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
# MacOS COM port:
COM_PORT = '/dev/cu.usbmodem2017_2_251'

# The new device has a serial number of '2017-2-25'

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 480


class TuringError(Exception):
    pass


class Command:
    # Old protocol (6 byte packets, command in final byte)
    #RESET = 101
    #CLEAR = 102
    #SCREEN_OFF = 108
    #SCREEN_ON = 109
    #SET_BRIGHTNESS = 110
    #DISPLAY_BITMAP = 197

    # New protocol (10 byte packets, framed with the command, 8 data bytes inside)
    HELLO = 0xCA
    ORIENTATION = 0xCB
    ORIENTATION_PORTRAIT = 0
    ORIENTATION_LANDSCAPE = 1
    # The device seems to start in PORTRAIT, with the row ordering reversed from
    # the ORIENTATION_PORTRAIT setting. It is not clear how to restore the ordering
    # to the reset configuration.
    DISPLAY_BITMAP = 0xCC
    LIGHTING = 0xCD
    SET_BRIGHTNESS = 0xCE


def SendReg(ser: serial.Serial, cmd: int, x: int, y: int, ex: int, ey: int):
    byteBuffer = bytearray(6)
    byteBuffer[0] = (x >> 2)
    byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
    byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
    byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
    byteBuffer[4] = (ey & 255)
    byteBuffer[5] = cmd
    ser.write(bytes(byteBuffer))


def SendCommand(ser: serial.Serial, cmd: int, payload=None):
    if payload is None:
        payload = [0] * 8
    elif len(payload) < 8:
        payload = list(payload) + [0] * (8 - len(payload))

    byteBuffer = bytearray(10)
    byteBuffer[0] = cmd
    byteBuffer[1] = payload[0]
    byteBuffer[2] = payload[1]
    byteBuffer[3] = payload[2]
    byteBuffer[4] = payload[3]
    byteBuffer[5] = payload[4]
    byteBuffer[6] = payload[5]
    byteBuffer[7] = payload[6]
    byteBuffer[8] = payload[7]
    byteBuffer[9] = cmd
    print("Sending %r" % (byteBuffer,))
    ser.write(bytes(byteBuffer))


def Hello(ser: serial.Serial):
    hello = [ord('H'), ord('E'), ord('L'), ord('L'), ord('O')]
    SendCommand(ser, Command.HELLO, payload=hello)
    response = ser.read(10)
    if len(response) != 10:
        raise TuringError("Device not recognised (short response to HELLO)")
    if response[0] != Command.HELLO or response[-1] != Command.HELLO:
        raise TuringError("Device not recognised (bad framing)")
    if [x for x in response[1:6]] != hello:
        raise TuringError("Device not recognised (No HELLO; got %r)" % (response[1:6],))
    # The HELLO response here is followed by:
    #   0x0A, 0x12, 0x00
    # It is not clear what these might be.
    # It would be handy if these were a version number, or a set of capability
    # flags. The 0x0A=10 being version 10 or 0.10, and the 0x12 being the size or the
    # indication that a backlight is present, would be nice. But that's guessing
    # based on how I'd do it.


def Clear(ser: serial.Serial):
    # Unknown what command this is
    print("Clear unknown")
    # Cannot find a 'clear' command
    #SendReg(ser, Command.CLEAR, 0, 0, 0, 0)


def Orientation(ser: serial.Serial, state: int):
    print("Orientation: %r" % (state,))
    SendCommand(ser, Command.ORIENTATION, payload=[state])


def SetLighting(ser: serial.Serial, red: int, green: int, blue: int):
    print("Lighting: %i, %i, %i" % (red, green, blue))
    assert red < 256, 'Red lighting must be < 256'
    assert green < 256, 'Green lighting must be < 256'
    assert blue < 256, 'Blue lighting must be < 256'
    SendCommand(ser, Command.LIGHTING, payload=[red, green, blue])


def ScreenOff(ser: serial.Serial):
    print("Screen off unknown")
    # Cannot find a 'screen off' command
    #SendReg(ser, Command.SCREEN_OFF, 0, 0, 0, 0)


def ScreenOn(ser: serial.Serial):
    print("Screen on unknown")
    # Cannot find a 'screen on' command
    #SendReg(ser, Command.SCREEN_ON, 0, 0, 0, 0)


def SetBrightness(ser: serial.Serial, level: int):
    # Level : 0 (brightest) - 255 (darkest)
    assert 255 >= level >= 0, 'Brightness level must be [0-255]'
    # New protocol has 255 as the brightest, and 0 as off.
    SendCommand(ser, Command.SET_BRIGHTNESS, payload=[255-level])


def DisplayPILImage(ser: serial.Serial, image: Image, x: int, y: int):
    image_height = image.size[1]
    image_width = image.size[0]

    assert image_height > 0, 'Image width must be > 0'
    assert image_width > 0, 'Image height must be > 0'

    (x0, y0) = (x, y)
    (x1, y1) = (x + image_width - 1, y + image_height - 1)

    SendCommand(ser, Command.DISPLAY_BITMAP,
                payload=[(x0>>8) & 255, x0 & 255,
                         (y0>>8) & 255, y0 & 255,
                         (x1>>8) & 255, x1 & 255,
                         (y1>>8) & 255, y1 & 255])

    pix = image.load()
    line = bytes()
    for h in range(image_height):
        for w in range(image_width):
            R = pix[w, h][0] >> 3
            G = pix[w, h][1] >> 2
            B = pix[w, h][2] >> 3

            # Original: 0bRRRRRGGGGGGBBBBB
            #             fedcba9876543210
            # New:      0bgggBBBBBRRRRRGGG
            # That is...
            #   High 3 bits of green in b0-b2
            #   Low 3 bits of green in b13-b15
            #   Red 5 bits in b3-b7
            #   Blue 5 bits in b8-b12
            rgb = (B << 8) | (G>>3) | ((G&7)<<13) | (R<<3)
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

    # Hello! to check this is the right device
    Hello(lcd_comm)

    # Data orientation
    Orientation(lcd_comm, Command.ORIENTATION_PORTRAIT)

    # Set brightness to max value
    SetBrightness(lcd_comm, 0)

    # Lighting (a purple)
    SetLighting(lcd_comm, 128, 50, 112)

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
