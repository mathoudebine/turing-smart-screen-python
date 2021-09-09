#!/usr/bin/env python3
import struct
from time import sleep
import serial  # Install pyserial : pip install pyserial
from PIL import Image  # Install PIL or Pillow

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux...
COM_PORT = "/dev/ttyACM1"
# COM_PORT = "COM5"


class Command:
    RESET = 101
    CLEAR = 102
    SCREEN_OFF = 108
    SCREEN_ON = 109
    SET_BRIGHTNESS = 110
    DISPLAY_BITMAP = 197


def SendReg(ser, reg, x, y, ex, ey):
    byteBuffer = bytearray(6)
    byteBuffer[0] = (x >> 2)
    byteBuffer[1] = (((x & 3) << 6) + (y >> 4))
    byteBuffer[2] = (((y & 15) << 4) + (ex >> 6))
    byteBuffer[3] = (((ex & 63) << 2) + (ey >> 8))
    byteBuffer[4] = (ey & 255)
    byteBuffer[5] = reg
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


def PrintImage(ser, image):
    im = Image.open(image)
    image_height = im.size[1]
    image_width = im.size[0]

    SendReg(ser, Command.DISPLAY_BITMAP, 0, 0, image_width - 1, image_height - 1)

    pix = im.load()
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


if __name__ == "__main__":
    # Do not change COM port settings unless you know what you are doing
    lcd_comm = serial.Serial(COM_PORT, 115200, timeout=1, rtscts=1)

    # Clear screen (blank)
    Clear(lcd_comm)

    # Set brightness to max value
    SetBrightness(lcd_comm, 0)

    # Display sample picture
    PrintImage(lcd_comm, "res/example.png")

    lcd_comm.close()
