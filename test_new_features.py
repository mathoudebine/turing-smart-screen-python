# This file is a simple Python test program using the library code to demonstrate the new video features

import os
import signal
import sys
import time
from datetime import datetime
from PIL import Image

# Import only the modules for LCD communication
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd.lcd_comm_rev_b import LcdCommRevB
from library.lcd.lcd_comm_rev_c import LcdCommRevC, Command, Padding
from library.lcd.lcd_simulated import LcdSimulated
from library.log import logger

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux, etc. or "AUTO" for auto-discovery
# COM_PORT = "/dev/ttyACM0"
COM_PORT = "COM4"

# Display revision: A for Turing 3.5", B for Xuanfang 3.5" (inc. flagship), C for Turing 5"
# Use SIMU for 3.5" simulated LCD (image written in screencap.png) or SIMU5 for 5" simulated LCD
# To identify your revision: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions

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

    # Build your LcdComm object for Turing 5"
    print("Selected Hardware Revision C (Turing Smart Screen 5\")")
    lcd_comm = LcdCommRevC(com_port=COM_PORT,
                            display_width=480,
                            display_height=800)

    # Set LANDSCAPE orientation.
    orientation = Orientation.LANDSCAPE
    lcd_comm.SetOrientation(orientation=orientation)

    # Send initialization commands
    lcd_comm.InitializeComm()

    ##### New feature examples #####

    # List files in root directory.
    print(lcd_comm.ListFiles("/"))

    # List: internal images ; internal videos ; SDCARD images ; SDCARD videos.
    print(lcd_comm.ListImagesInternalStorage())
    print(lcd_comm.ListVideosInternalStorage())
    print(lcd_comm.ListImagesSDStorage())
    print(lcd_comm.ListVideosSDStorage())

    # Check if video is loaded and upload video if needed.
    video_size = lcd_comm.GetFileSize("/mnt/SDCARD/video/particle_wave.mp4")

    if video_size == 0:
        # Upload a background video.
        print("Uploading video ...")
        lcd_comm.UploadFile(local_path="res/videos/particle_wave.mp4", destination_path="/mnt/SDCARD/video/particle_wave.mp4")
        print("Upload done")

    # Print size of the uploaded video.
    print(lcd_comm.GetFileSize("/mnt/SDCARD/video/particle_wave.mp4"))

    # Clear screen.
    lcd_comm.StopVideo()
    lcd_comm.Clear()

    # Start the backgroud video.
    lcd_comm.StartVideo("/mnt/SDCARD/video/particle_wave.mp4")

    # Initialize the video overlay.
    # Must be called before drawing anything on the video!
    lcd_comm.InitializeVideoOverlay()

    # Draw a red square.
    test_image = Image.new("RGB", (50, 50), (255, 0, 0))
    lcd_comm.DrawPILImageOnVideo(test_image, x=10, y=10)

    # Refresh n°1
    time.sleep(1)
    lcd_comm.ResfreshVideoOverlay()

    # Transparent gray square.
    test_image2 = Image.new("RGBA", (100, 100), (64, 64, 64, 64))
    lcd_comm.DrawPILImageOnVideo(test_image2, x=250, y=50)

    # Yellow square.
    test_image3 = Image.new("RGB", (20, 20), (255, 255, 0))
    lcd_comm.DrawPILImageOnVideo(test_image3, x=400, y=60)

    # Refresh n°2
    time.sleep(1)
    lcd_comm.ResfreshVideoOverlay()

    # Display sample text on video.
    lcd_comm.DrawTextOnVideo("Basic text", 50, 100)

    # Refresh n°3
    lcd_comm.ResfreshVideoOverlay()

    # Close serial connection at exit
    lcd_comm.closeSerial()
