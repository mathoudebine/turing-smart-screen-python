#!/usr/bin/env python3
import struct
from time import sleep
import serial  # Install pyserial : pip install pyserial
from PIL import Image, ImageDraw, ImageFont  # Install PIL or Pillow

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux...
COM_PORT = "/dev/ttyACM1"
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


def SendReg(ser, cmd, x, y, ex, ey):
    byteBuffer = bytearray(6)
    byteBuffer[0] = (x >> 2)
    byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
    byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
    byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
    byteBuffer[4] = (ey & 255)
    byteBuffer[5] = cmd
    ser.write(bytes(byteBuffer))


def Reset(ser):
    SendReg(ser, Command.RESET, 0, 0, 0, 0)


def Clear(ser):
    SendReg(ser, Command.CLEAR, 0, 0, 0, 0)


def ScreenOff(ser):
    SendReg(ser, Command.SCREEN_OFF, 0, 0, 0, 0)


def ScreenOn(ser):
    SendReg(ser, Command.SCREEN_ON, 0, 0, 0, 0)


def SetBrightness(ser, level):
    # Level : 0 (brightest) - 255 (darkest)
    SendReg(ser, Command.SET_BRIGHTNESS, level, 0, 0, 0)


def DisplayPILImage(ser, image, x, y):
    image_height = image.size[1]
    image_width = image.size[0]

    SendReg(ser, Command.DISPLAY_BITMAP, x, y, image_width - 1, image_height - 1)

    pix = image.load()
    for h in range(image_height):
        line = bytes()
        for w in range(image_width):
            if w < image_width:
                R = pix[w, h][0] >> 3
                G = pix[w, h][1] >> 2
                B = pix[w, h][2] >> 3

                rgb = (R << 11) | (G << 5) | B
                line += struct.pack('H', rgb)
        ser.write(line)

    sleep(0.01)  # Wait 10 ms after picture display


def DisplayBitmap(ser, bitmap_path, x=0, y=0):
    image = Image.open(bitmap_path)
    DisplayPILImage(ser, image, x, y)


def DisplayText(ser, text, x=0, y=0,
                font="roboto/Roboto-Regular.ttf",
                font_size=20,
                font_color=(0, 0, 0),
                background_color=(255, 255, 255)):
    # Convert text to bitmap using PIL and display it

    # The text bitmap is created with max width/height by default
    # Note : alpha component from RGBA is not supported by the display
    text_image = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), background_color)

    # Draw text with specified color & font
    font = ImageFont.truetype("./res/fonts/" + font, font_size)
    d = ImageDraw.Draw(text_image)
    d.text((0, 0), text, font=font, fill=font_color)

    # Crop text bitmap to the size of the text
    text_width, text_height = d.textsize(text, font=font)
    text_image = text_image.crop((0, 0, text_width, text_height))

    DisplayPILImage(ser, text_image, x, y)


if __name__ == "__main__":
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
    
    DisplayText(lcd_comm, "Custom text", 5, 150,
                font="roboto/Roboto-BoldItalic.ttf",
                font_size=40,
                font_color=(0, 0, 255),
                background_color=(255, 255, 0))

    lcd_comm.close()
