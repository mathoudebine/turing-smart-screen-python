import unittest

from PIL import Image

from library import config
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation

from ..scheduler_stub import import_scheduler
from .serial_mock import new_testing_serial
from .sample_image import generate_sample_image

scheduler = import_scheduler()


class MockedLcdCommRevA(LcdCommRevA):
    def openSerial(self):
        self.lcd_serial = new_testing_serial()

    def expect_golden(self, tc: unittest.TestCase, fn: str):
        self.lcd_serial.expect_golden(tc, fn)

sample_img_portrait = generate_sample_image(320, 480)
sample_img_landscape = generate_sample_image(480, 320)

class TestLcdCommRevA(unittest.TestCase):
    def test_set_brightness(self):
        lcd = MockedLcdCommRevA()
        lcd.SetBrightness()

        lcd.expect_golden(self, "rev_a_set_brightness")

    # display_pil_image_<orientation> : display a full-screen image

    def test_display_pil_image_portrait(self):
        lcd = MockedLcdCommRevA()
        lcd.SetOrientation(orientation=Orientation.PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait)

        lcd.expect_golden(self, "rev_a_display_pil_image_portrait")

    def test_display_pil_image_landscape(self):
        lcd = MockedLcdCommRevA()
        lcd.SetOrientation(orientation=Orientation.LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape)

        lcd.expect_golden(self, "rev_a_display_pil_image_landscape")

    def test_display_pil_image_reverse_portrait(self):
        lcd = MockedLcdCommRevA()
        lcd.SetOrientation(orientation=Orientation.REVERSE_PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait)

        lcd.expect_golden(self, "rev_a_display_pil_image_reverse_portrait")

    def test_display_pil_image_reverse_landscape(self):
        lcd = MockedLcdCommRevA()
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape)

        lcd.expect_golden(self, "rev_a_display_pil_image_reverse_landscape")

    # display_pil_image_patch_<orientation> : display a less-than-full-screen image at a given location

    def test_display_pil_image_patch_portrait(self):
        lcd = MockedLcdCommRevA()
        lcd.SetOrientation(orientation=Orientation.PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_a_display_pil_image_patch_portrait")

    def test_display_pil_image_patch_landscape(self):
        lcd = MockedLcdCommRevA()
        lcd.SetOrientation(orientation=Orientation.LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_a_display_pil_image_patch_landscape")

    def test_display_pil_image_patch_reverse_portrait(self):
        lcd = MockedLcdCommRevA()
        lcd.SetOrientation(orientation=Orientation.REVERSE_PORTRAIT)
        lcd.DisplayPILImage(sample_img_portrait, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_a_display_pil_image_patch_reverse_portrait")

    def test_display_pil_image_patch_reverse_landscape(self):
        lcd = MockedLcdCommRevA()
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        lcd.DisplayPILImage(sample_img_landscape, x=10, y=20, image_width=100, image_height=200)

        lcd.expect_golden(self, "rev_a_display_pil_image_patch_reverse_landscape")


def serial_writes(lcd) -> list:
    return [args[0] for method, args, _ in lcd.lcd_serial.mock_calls if method == "write"]


class TestLcdCommRevAQueue(unittest.TestCase):
    # Queued mode (update_queue set, queue writer driven by scheduler): supersession and dedup

    def setUp(self):
        while not config.update_queue.empty():
            config.update_queue.get_nowait()
        self.saved_driver = config.display_driver

    def tearDown(self):
        config.display_driver = self.saved_driver

    def test_stale_frame_for_same_region_never_reaches_serial(self):
        lcd = MockedLcdCommRevA(update_queue=config.update_queue)
        config.display_driver = lcd

        img_old = sample_img_portrait
        img_new = Image.new("RGB", (100, 200), (0, 0, 255))

        # Reference: what exactly one direct transmission of the newest frame looks like
        reference = MockedLcdCommRevA()
        reference.DisplayPILImage(img_new, x=10, y=20, image_width=100, image_height=200)
        expected = serial_writes(reference)

        lcd.DisplayPILImage(img_old, x=10, y=20, image_width=100, image_height=200)
        lcd.DisplayPILImage(img_new, x=10, y=20, image_width=100, image_height=200)
        self.assertEqual(lcd.update_queue.qsize(), 34)  # 2 x (1 window command + 16 data chunks)

        scheduler._process_update_queue(block=False)

        self.assertTrue(expected)
        self.assertEqual(serial_writes(lcd), expected)

    def test_direct_mode_bypasses_dedup_entirely(self):
        # Queue-less direct mode must write immediately and never touch the dedup cache
        lcd = MockedLcdCommRevA()
        img = Image.new("RGB", (100, 200), (0, 255, 0))

        lcd.DisplayPILImage(img, x=10, y=20, image_width=100, image_height=200)
        self.assertEqual(lcd.update_queue, None)
        self.assertTrue(serial_writes(lcd))
        self.assertEqual(lcd._last_sent_payload, {})

        lcd.DisplayPILImage(img, x=10, y=20, image_width=100, image_height=200)
        self.assertGreater(len(serial_writes(lcd)), 1)  # identical frame still written: no dedup
        self.assertEqual(lcd._last_sent_payload, {})

    def test_identical_frame_skipped_and_resent_after_clear(self):
        lcd = MockedLcdCommRevA(update_queue=config.update_queue)
        config.display_driver = lcd
        img = Image.new("RGB", (100, 200), (0, 255, 0))

        lcd.DisplayPILImage(img, x=10, y=20, image_width=100, image_height=200)
        scheduler._process_update_queue(block=False)
        first = serial_writes(lcd)
        self.assertTrue(first)
        self.assertEqual(lcd._last_sent_payload, {(10, 20, 100, 200): b"".join(first)})

        # Same content again: device already shows it, nothing must be transmitted
        lcd.DisplayPILImage(img, x=10, y=20, image_width=100, image_height=200)
        scheduler._process_update_queue(block=False)
        self.assertEqual(serial_writes(lcd), first)

        # After Clear() the screen content is lost: same content must be sent again
        lcd.Clear()
        scheduler._process_update_queue(block=False)  # flush the CLEAR command itself
        self.assertEqual(lcd._last_sent_payload, {})

        lcd.DisplayPILImage(img, x=10, y=20, image_width=100, image_height=200)
        scheduler._process_update_queue(block=False)
        self.assertGreater(len(serial_writes(lcd)), len(first))
