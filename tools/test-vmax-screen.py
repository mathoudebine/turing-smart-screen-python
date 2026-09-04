import sys
import os
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add turing-smart-screen-python to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from library.lcd.lcd_comm_vmax import LcdCommVmax
from library.lcd.lcd_comm import Orientation
from library.log import logger

print("==================================================")
print("Testing HL-VMAX / Solarmax in turing-smart-screen")
print("==================================================")

try:
    print("[1] Initializing LcdCommVmax (auto-detecting COM port)...")
    lcd = LcdCommVmax(com_port="AUTO")
    print(f"    Opened port: {lcd.lcd_serial.port if lcd.lcd_serial else 'None'}")

    print("[2] Running InitializeComm & Handshake...")
    lcd.InitializeComm()
    print(f"    Serial number: {lcd.serial_number}")
    print(f"    Detected size: {lcd.display_width} x {lcd.display_height}")

    print("[3] Setting brightness to 75%...")
    lcd.SetBrightness(75)

    print("[4] Setting orientation to PORTRAIT...")
    lcd.SetOrientation(Orientation.PORTRAIT)

    w = lcd.get_width()
    h = lcd.get_height()
    print(f"[5] Creating test dashboard image ({w}x{h})...")

    img = Image.new("RGB", (w, h), color=(15, 20, 30))
    draw = ImageDraw.Draw(img)

    # Decorative header
    draw.rectangle([0, 0, w, 80], fill=(24, 75, 140))
    draw.text((20, 25), "TURING SMART SCREEN PYTHON", fill=(255, 255, 255))

    # Sub-header
    draw.rectangle([0, 85, w, 140], fill=(30, 40, 60))
    draw.text((20, 100), f"HL-VMAX Driver | {w}x{h} Native", fill=(0, 230, 180))

    # System Status Card
    draw.rounded_rectangle([20, 160, w - 20, 380], radius=15, fill=(25, 35, 50), outline=(50, 70, 100), width=2)
    draw.text((40, 180), "HARDWARE INFO", fill=(200, 200, 200))
    draw.text((40, 220), f"Serial: {lcd.serial_number}", fill=(255, 255, 255))
    draw.text((40, 260), f"Port: {lcd.lcd_serial.port}", fill=(255, 255, 255))
    draw.text((40, 300), f"Resolution: {w} x {h}", fill=(0, 255, 200))
    draw.text((40, 340), "Driver Status: ONLINE & WORKING", fill=(50, 255, 50))

    # CPU Load simulation bar
    draw.rounded_rectangle([20, 410, w - 20, 560], radius=15, fill=(25, 35, 50), outline=(50, 70, 100), width=2)
    draw.text((40, 430), "CPU USAGE (SIMULATED)", fill=(200, 200, 200))
    draw.text((40, 465), "Load: 42%", fill=(255, 255, 255))
    draw.rounded_rectangle([40, 505, w - 40, 535], radius=6, fill=(40, 50, 70))
    bar_w = int((w - 80) * 0.42)
    draw.rounded_rectangle([40, 505, 40 + bar_w, 535], radius=6, fill=(0, 180, 255))

    # RAM Load simulation bar
    draw.rounded_rectangle([20, 590, w - 20, 740], radius=15, fill=(25, 35, 50), outline=(50, 70, 100), width=2)
    draw.text((40, 610), "RAM USAGE (SIMULATED)", fill=(200, 200, 200))
    draw.text((40, 645), "Used: 68% (21.7 / 32 GB)", fill=(255, 255, 255))
    draw.rounded_rectangle([40, 685, w - 40, 715], radius=6, fill=(40, 50, 70))
    bar_ram = int((w - 80) * 0.68)
    draw.rounded_rectangle([40, 685, 40 + bar_ram, 715], radius=6, fill=(180, 80, 255))

    # GPU Status card
    draw.rounded_rectangle([20, 770, w - 20, 920], radius=15, fill=(25, 35, 50), outline=(50, 70, 100), width=2)
    draw.text((40, 790), "GPU STATUS (SIMULATED)", fill=(200, 200, 200))
    draw.text((40, 825), "Load: 25% | Temp: 48°C", fill=(255, 255, 255))
    draw.rounded_rectangle([40, 865, w - 40, 895], radius=6, fill=(40, 50, 70))
    bar_gpu = int((w - 80) * 0.25)
    draw.rounded_rectangle([40, 865, 40 + bar_gpu, 895], radius=6, fill=(0, 230, 120))

    # Footer
    draw.rectangle([0, h - 60, w, h], fill=(20, 25, 35))
    draw.text((20, h - 42), "Turing Smart Screen Python • HL-VMAX Driver", fill=(120, 140, 170))

    print("[6] Sending frame via DisplayPILImage...")
    lcd.DisplayPILImage(img, 0, 0, w, h)
    print("[7] Frame sent successfully to the screen!")

    time.sleep(1)
    lcd.closeSerial()
    print("Test finished successfully!")

except Exception as e:
    import traceback
    print("Error during test:")
    traceback.print_exc()
