import unittest

from library.lcd.lcd_comm_rev_c import LcdCommRevC, Orientation

from .serial_mock import new_testing_serial
from .sample_image import generate_sample_image


class MockedLcdCommRevC(LcdCommRevC):
    def openSerial(self):
        self.lcd_serial = new_testing_serial()

    def expect_golden(self, tc: unittest.TestCase, fn: str):
        self.lcd_serial.expect_golden(tc, fn)

sample_img_portrait = generate_sample_image(480, 800)
sample_img_landscape = generate_sample_image(800, 480)

class TestLcdCommRevC(unittest.TestCase):
    def test_set_brightness(self):
        lcd = MockedLcdCommRevC()
        lcd.SetBrightness()

        lcd.expect_golden(self, "rev_c_set_brightness")

    # display_pil_image_<orientation> : display a full-screen image

    def test_display_pil_image_portrait(self):
        lcd = MockedLcdCommRevC()
        lcd.SetOrientation(orientation=Orientation.PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait)

        lcd.expect_golden(self, "rev_c_display_pil_image_portrait")

    def test_display_pil_image_landscape(self):
        lcd = MockedLcdCommRevC()
        lcd.SetOrientation(orientation=Orientation.LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape)

        lcd.expect_golden(self, "rev_c_display_pil_image_landscape")

    def test_display_pil_image_reverse_portrait(self):
        lcd = MockedLcdCommRevC()
        lcd.SetOrientation(orientation=Orientation.REVERSE_PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait)

        lcd.expect_golden(self, "rev_c_display_pil_image_reverse_portrait")

    def test_display_pil_image_reverse_landscape(self):
        lcd = MockedLcdCommRevC()
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape)

        lcd.expect_golden(self, "rev_c_display_pil_image_reverse_landscape")

    # display_pil_image_patch_<orientation> : display a less-than-full-screen image at a given location

    def test_display_pil_image_patch_portrait(self):
        lcd = MockedLcdCommRevC()
        lcd.SetOrientation(orientation=Orientation.PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_c_display_pil_image_patch_portrait")

    def test_display_pil_image_patch_landscape(self):
        lcd = MockedLcdCommRevC()
        lcd.SetOrientation(orientation=Orientation.LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_c_display_pil_image_patch_landscape")

    def test_display_pil_image_patch_reverse_portrait(self):
        lcd = MockedLcdCommRevC()
        lcd.SetOrientation(orientation=Orientation.REVERSE_PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_c_display_pil_image_patch_reverse_portrait")

    def test_display_pil_image_patch_reverse_landscape(self):
        lcd = MockedLcdCommRevC()
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_c_display_pil_image_patch_reverse_landscape")
