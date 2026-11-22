import unittest

from library.lcd.lcd_comm_rev_c import LcdCommRevC, Orientation, SubRevision

from .serial_mock import new_testing_serial
from .sample_image import generate_sample_image


class MockedLcdCommRevC(LcdCommRevC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Values normally detected by _hello(), which cannot run against the mock serial
        self.sub_revision = SubRevision.REV_5INCH
        self.rom_version = 87

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


from PIL import Image

from library import config

from ..scheduler_stub import import_scheduler

scheduler = import_scheduler()


class TestLcdCommRevCQueue(unittest.TestCase):
    # Queued mode (update_queue set, queue writer driven by scheduler): supersession must drop
    # whole transmission units, keeping WriteData/ReadData response pairs intact

    def setUp(self):
        while not config.update_queue.empty():
            config.update_queue.get_nowait()
        self.saved_driver = config.display_driver

    def tearDown(self):
        config.display_driver = self.saved_driver

    def test_discarded_frame_produces_no_serial_traffic(self):
        lcd = MockedLcdCommRevC(update_queue=config.update_queue)
        lcd.sub_revision = SubRevision.REV_5INCH  # normally detected by _hello()
        lcd.rom_version = 87
        config.display_driver = lcd

        img1 = Image.new("RGB", (100, 200), (255, 0, 0))
        img2 = Image.new("RGB", (100, 200), (0, 0, 255))

        lcd.DisplayPILImage(img1, x=10, y=20, image_width=100, image_height=200)
        lcd.DisplayPILImage(img2, x=10, y=20, image_width=100, image_height=200)

        scheduler._process_update_queue(block=False)

        calls = [method for method, _, _ in lcd.lcd_serial.mock_calls if method in ("write", "read")]
        # One partial frame = 3 writes (payload header, payload, status query) + its 1 read;
        # the superseded frame must not leave any traffic (in particular no orphan write)
        self.assertEqual(calls, ["write", "write", "write", "read"])
