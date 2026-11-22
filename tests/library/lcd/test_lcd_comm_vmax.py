import unittest
from PIL import Image

from library.lcd.lcd_comm_vmax import LcdCommVmax
from library.lcd.lcd_comm import Orientation
from .serial_mock import new_testing_serial


class MockedLcdCommVmax(LcdCommVmax):
    def openSerial(self):
        self.lcd_serial = new_testing_serial()


class TestLcdCommVmax(unittest.TestCase):
    def test_brightness(self):
        lcd = MockedLcdCommVmax(display_width=462, display_height=1920)
        lcd.SetBrightness(80)
        writes = [args[0] for name, args, _ in lcd.lcd_serial.mock_calls if name == "write"]
        self.assertIn(bytes([0xAA, 0xBB, 80, 0xCC, 0xDD]), writes)

    def test_screen_off_on_preserves_brightness(self):
        lcd = MockedLcdCommVmax(display_width=462, display_height=1920)
        lcd.SetBrightness(45)
        self.assertEqual(lcd.brightness, 45)
        lcd.ScreenOff()
        self.assertEqual(lcd.brightness, 0)
        lcd.ScreenOn()
        self.assertEqual(lcd.brightness, 45)

    def test_parse_geometry(self):
        lcd = MockedLcdCommVmax(display_width=462, display_height=1920)
        lcd._parse_geometry("VMAXD160462*1920S262001750")
        self.assertEqual(lcd.display_width, 462)
        self.assertEqual(lcd.display_height, 1920)

        # Flipped geometry in serial string
        lcd._parse_geometry("VMAXD1601920*462S262001750")
        self.assertEqual(lcd.display_width, 462)
        self.assertEqual(lcd.display_height, 1920)

        # 11.3" geometry
        lcd._parse_geometry("VMAXA170320*1480S261001155")
        self.assertEqual(lcd.display_width, 320)
        self.assertEqual(lcd.display_height, 1480)

    def test_display_pil_image_portrait(self):
        lcd = MockedLcdCommVmax(display_width=100, display_height=200)
        lcd.SetOrientation(Orientation.PORTRAIT)
        img = Image.new("RGB", (100, 200), (255, 0, 0))
        lcd.DisplayPILImage(img)
        writes = [args[0] for name, args, _ in lcd.lcd_serial.mock_calls if name == "write"]
        self.assertTrue(len(writes) > 0)
        self.assertTrue(writes[0].startswith(b"\xff\xd8\xff"))
        self.assertTrue(writes[0].endswith(b"\xff\xd9"))

    def test_display_pil_image_reverse_portrait(self):
        lcd = MockedLcdCommVmax(display_width=100, display_height=200)
        lcd.SetOrientation(Orientation.REVERSE_PORTRAIT)
        img = Image.new("RGB", (100, 200), (0, 0, 255))
        lcd.DisplayPILImage(img)
        writes = [args[0] for name, args, _ in lcd.lcd_serial.mock_calls if name == "write"]
        self.assertTrue(len(writes) > 0)
        self.assertTrue(writes[0].startswith(b"\xff\xd8\xff"))
        self.assertTrue(writes[0].endswith(b"\xff\xd9"))

    def test_display_pil_image_landscape(self):
        lcd = MockedLcdCommVmax(display_width=100, display_height=200)
        lcd.SetOrientation(Orientation.LANDSCAPE)
        img = Image.new("RGB", (200, 100), (0, 255, 0))
        lcd.DisplayPILImage(img)
        writes = [args[0] for name, args, _ in lcd.lcd_serial.mock_calls if name == "write"]
        self.assertTrue(len(writes) > 0)
        self.assertTrue(writes[0].startswith(b"\xff\xd8\xff"))
        self.assertTrue(writes[0].endswith(b"\xff\xd9"))

    def test_display_pil_image_reverse_landscape(self):
        lcd = MockedLcdCommVmax(display_width=100, display_height=200)
        lcd.SetOrientation(Orientation.REVERSE_LANDSCAPE)
        img = Image.new("RGB", (200, 100), (255, 255, 0))
        lcd.DisplayPILImage(img)
        writes = [args[0] for name, args, _ in lcd.lcd_serial.mock_calls if name == "write"]
        self.assertTrue(len(writes) > 0)
        self.assertTrue(writes[0].startswith(b"\xff\xd8\xff"))
        self.assertTrue(writes[0].endswith(b"\xff\xd9"))
