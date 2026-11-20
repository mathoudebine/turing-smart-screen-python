import unittest
from unittest import mock

from PIL import Image

from library import config
from library.lcd.lcd_comm_rev_b import LcdCommRevB, Orientation

from ..scheduler_stub import import_scheduler
from .serial_mock import new_testing_serial
from .sample_image import generate_sample_image

scheduler = import_scheduler()


class MockedLcdCommRevB(LcdCommRevB):
    def openSerial(self):
        self.lcd_serial = new_testing_serial()

    def expect_golden(self, tc: unittest.TestCase, fn: str):
        self.lcd_serial.expect_golden(tc, fn)

sample_img_portrait = generate_sample_image(320, 480)
sample_img_landscape = generate_sample_image(480, 320)

class TestLcdCommRevB(unittest.TestCase):
    def test_set_brightness(self):
        lcd = MockedLcdCommRevB()
        lcd.SetBrightness()

        lcd.expect_golden(self, "rev_b_set_brightness")

    # display_pil_image_<orientation> : display a full-screen image

    def test_display_pil_image_portrait(self):
        lcd = MockedLcdCommRevB()
        lcd.SetOrientation(orientation=Orientation.PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait)

        lcd.expect_golden(self, "rev_b_display_pil_image_portrait")

    def test_display_pil_image_landscape(self):
        lcd = MockedLcdCommRevB()
        lcd.SetOrientation(orientation=Orientation.LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape)

        lcd.expect_golden(self, "rev_b_display_pil_image_landscape")

    def test_display_pil_image_reverse_portrait(self):
        lcd = MockedLcdCommRevB()
        lcd.SetOrientation(orientation=Orientation.REVERSE_PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait)

        lcd.expect_golden(self, "rev_b_display_pil_image_reverse_portrait")

    def test_display_pil_image_reverse_landscape(self):
        lcd = MockedLcdCommRevB()
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape)

        lcd.expect_golden(self, "rev_b_display_pil_image_reverse_landscape")

    # display_pil_image_patch_<orientation> : display a less-than-full-screen image at a given location

    def test_display_pil_image_patch_portrait(self):
        lcd = MockedLcdCommRevB()
        lcd.SetOrientation(orientation=Orientation.PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_b_display_pil_image_patch_portrait")

    def test_display_pil_image_patch_landscape(self):
        lcd = MockedLcdCommRevB()
        lcd.SetOrientation(orientation=Orientation.LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_b_display_pil_image_patch_landscape")

    def test_display_pil_image_patch_reverse_portrait(self):
        lcd = MockedLcdCommRevB()
        lcd.SetOrientation(orientation=Orientation.REVERSE_PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_b_display_pil_image_patch_reverse_portrait")

    def test_display_pil_image_patch_reverse_landscape(self):
        lcd = MockedLcdCommRevB()
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_b_display_pil_image_patch_reverse_landscape")


class TestLcdCommRevBQueue(unittest.TestCase):
    # Queued mode (update_queue set, queue writer driven by scheduler): supersession

    def setUp(self):
        while not config.update_queue.empty():
            config.update_queue.get_nowait()
        self.saved_driver = config.display_driver

    def tearDown(self):
        config.display_driver = self.saved_driver

    def test_superseded_frame_drops_its_cooldown_sleep_with_it(self):
        lcd = MockedLcdCommRevB(update_queue=config.update_queue)
        config.display_driver = lcd
        img1 = Image.new("RGB", (100, 200), (255, 0, 0))
        img2 = Image.new("RGB", (100, 200), (0, 0, 255))

        # time.sleep is patched before queueing: queued items reference the patched function
        with mock.patch("library.lcd.lcd_comm_rev_b.time.sleep") as sleep:
            lcd.DisplayPILImage(img1, x=10, y=20, image_width=100, image_height=200)
            lcd.DisplayPILImage(img2, x=10, y=20, image_width=100, image_height=200)
            self.assertEqual(lcd.update_queue.qsize(), 36)  # 2 x (1 cmd + 16 chunks + 1 sleep)

            scheduler._process_update_queue(block=False)

            # Only the surviving newest frame is transmitted, with its single cooldown sleep
            sleep.assert_called_once_with(0.05)
