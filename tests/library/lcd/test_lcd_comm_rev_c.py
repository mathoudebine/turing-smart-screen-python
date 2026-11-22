import unittest

from library.lcd.lcd_comm_rev_c import Command, LcdCommRevC, Orientation, SubRevision

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


class TestLcdCommRevC113(unittest.TestCase):
    def test_hello_24_char_id_sets_rom_90_and_113_revision(self):
        lcd = MockedLcdCommRevC(display_width=480, display_height=1920)
        lcd.lcd_serial.read.return_value = b"chs_113inch.dev1_rom1.90"
        lcd.InitializeComm()
        self.assertEqual(lcd.sub_revision, SubRevision.REV_113INCH)
        self.assertEqual(lcd.rom_version, 90)
        self.assertEqual(lcd.display_width, 440)
        self.assertEqual(lcd.display_height, 1920)

    def test_hello_23_char_88inch_still_parses_rom_90(self):
        lcd = MockedLcdCommRevC(display_width=480, display_height=1920)
        lcd.lcd_serial.read.return_value = b"chs_88inch.dev1_rom1.90"
        lcd.InitializeComm()
        self.assertEqual(lcd.sub_revision, SubRevision.REV_8INCH)
        self.assertEqual(lcd.rom_version, 90)

    def test_full_frame_uses_3390_size_word_twice(self):
        from PIL import Image

        lcd = MockedLcdCommRevC(display_width=440, display_height=1920)
        lcd.lcd_serial.read.return_value = b"chs_113inch.dev1_rom1.90"
        lcd.InitializeComm()
        lcd.lcd_serial.read.return_value = b"full_png_sucess"
        lcd.DisplayPILImage(Image.new("RGB", (440, 1920), (255, 0, 0)))
        writes = [args[0] for method, args, _ in lcd.lcd_serial.mock_calls if method == "write"]
        marker_113 = bytes((0xC8, 0xEF, 0x69, 0x00, 0x33, 0x90))
        marker_88 = bytes((0xC8, 0xEF, 0x69, 0x00, 0x38, 0x40))
        c8 = [w for w in writes if w[:6] == marker_113]
        self.assertEqual(len(c8), 2)
        self.assertFalse(any(w[:6] == marker_88 for w in writes))
        self.assertTrue(all(len(w) % 250 == 0 for w in c8))

    def test_full_frame_header_bypasses_a_real_update_queue(self):
        # Regression test for the 2026-08-17 bug: _write_113inch_c8_body/
        # _wait_113inch_full_png_success always write/read the serial port directly,
        # so if the header commands (PRE_UPDATE_BITMAP, START_DISPLAY_BITMAP,
        # DISPLAY_BITMAP_113INCH) were queued instead of bypassing, a real
        # update_queue (as main.py always supplies, unlike a standalone
        # script or the other tests above that construct the driver with no
        # queue at all) would leave them stuck unsent while the body raced
        # ahead of its own header on the wire. That's what caused the
        # intermittent "missing full_png_sucess" seen running a real theme.
        from PIL import Image
        import queue

        lcd = MockedLcdCommRevC(display_width=440, display_height=1920, update_queue=queue.Queue())
        lcd.lcd_serial.read.return_value = b"chs_113inch.dev1_rom1.90"
        lcd.InitializeComm()
        lcd.lcd_serial.read.return_value = b"full_png_sucess"
        lcd.DisplayPILImage(Image.new("RGB", (440, 1920), (255, 0, 0)))
        writes = [args[0] for method, args, _ in lcd.lcd_serial.mock_calls if method == "write"]
        pre_update_marker = bytes(Command.PRE_UPDATE_BITMAP.value)
        c8_marker = bytes((0xC8, 0xEF, 0x69, 0x00, 0x33, 0x90))
        self.assertTrue(
            any(w[:len(pre_update_marker)] == pre_update_marker for w in writes),
            "PRE_UPDATE_BITMAP never reached the wire -- stuck in the queue",
        )
        self.assertEqual(len([w for w in writes if w[:6] == c8_marker]), 2)

    def test_partial_update_is_cc_after_status_with_incrementing_count(self):
        from PIL import Image

        from library.lcd.lcd_comm_rev_c import Count

        Count.Start = 0
        lcd = MockedLcdCommRevC(display_width=440, display_height=1920)
        lcd.lcd_serial.read.return_value = b"chs_113inch.dev1_rom1.90"
        lcd.InitializeComm()
        lcd.SetOrientation(Orientation.REVERSE_PORTRAIT)
        lcd.DisplayPILImage(Image.new("RGB", (40, 20), (255, 255, 0)), x=10, y=20)
        writes = [args[0] for method, args, _ in lcd.lcd_serial.mock_calls if method == "write"]
        statuses = [w for w in writes if w[:1] == b"\xcf"]
        ccs = [w for w in writes if w[:3] == bytes((0xCC, 0xEF, 0x69))]
        self.assertGreaterEqual(len(statuses), 1)
        self.assertGreaterEqual(len(ccs), 1)
        # count field is bytes 10:14 of the 0xcc header, starts at 0 after hello
        self.assertEqual(int.from_bytes(ccs[0][10:14], "big"), 0)

    def test_pack_reshapes_440x1920_glass_into_1760x480_canvas(self):
        # Canvas pixel (cy, cx) is glass pixel (4*cy + cx//440, cx%440):
        # each canvas row packs 4 glass rows side by side. Confirmed on
        # hardware (not just derived) via tools/reshape_test.py in the
        # shinysnake-g600 repo: a native 440x1920 card reshaped this way
        # showed correct edges (magenta far-left, cyan far-right) and full
        # vertical resolution, where the old 480-wide-tile packing put
        # cyan near the LEFT edge (wraparound) and only lit 1 glass row in 4.
        from PIL import Image

        lcd = MockedLcdCommRevC(display_width=440, display_height=1920)
        lcd.lcd_serial.read.return_value = b"chs_113inch.dev1_rom1.90"
        lcd.InitializeComm()
        glass = Image.new("RGB", (440, 1920), (0, 0, 0))
        glass.putpixel((0, 0), (255, 0, 0))      # glass row 0, col 0
        glass.putpixel((439, 0), (0, 255, 0))    # glass row 0, col 439 (last column)
        glass.putpixel((0, 1), (0, 0, 255))      # glass row 1 -> same canvas row, sub=1
        glass.putpixel((0, 4), (255, 255, 0))    # glass row 4 -> canvas row 1, sub=0
        packed = lcd._pack_113inch_c8(glass)
        self.assertEqual(packed.size, (1760, 480))
        self.assertEqual(packed.getpixel((0, 0)), (255, 0, 0))     # canvas(0,0)
        self.assertEqual(packed.getpixel((439, 0)), (0, 255, 0))   # canvas(0,439)
        self.assertEqual(packed.getpixel((440, 0)), (0, 0, 255))   # canvas(0,440) = glass row1,col0
        self.assertEqual(packed.getpixel((0, 1)), (255, 255, 0))   # canvas(1,0) = glass row4,col0
        native = Image.new("RGB", (1760, 480), (0, 255, 0))
        self.assertIs(lcd._pack_113inch_c8(native), native)

    def test_borrowed_8_8inch_background_scales_instead_of_cropping(self):
        # Regression test for 2026-08-18: a borrowed 8.8" theme's full
        # background (480x1920 -- matches its declared WIDTH/HEIGHT exactly,
        # so DisplayBitmap never resizes it) used to fall through to the
        # generic crop path shared by every Rev C size, which hard-crops to
        # our declared width (440) *before* _pack_113inch_c8 ever runs --
        # silently discarding the rightmost 40px of real content instead of
        # scaling it in. Confirmed on the actual Gradient theme: its
        # gauge-ring content reached x=447 of 480 and was being clipped by
        # the x=439 crop boundary.
        #
        # Goes through the real DisplayPILImage entry point (not
        # _pack_113inch_c8 directly) and inspects what image actually
        # reached the packer, so this fails again if the whitelist entry
        # for (480, GLASS_HEIGHT) that fixes the dispatch is ever reverted
        # -- calling the packer directly wouldn't catch that, since a
        # pre-cropped 440x1920 image looks like a no-op resize to it.
        from PIL import Image

        lcd = MockedLcdCommRevC(display_width=440, display_height=1920)
        lcd.lcd_serial.read.return_value = b"chs_113inch.dev1_rom1.90"
        lcd.InitializeComm()
        lcd.lcd_serial.read.return_value = b"full_png_sucess"

        seen_sizes = []
        original_pack = lcd._pack_113inch_c8
        lcd._pack_113inch_c8 = lambda image: (seen_sizes.append(image.size), original_pack(image))[1]

        bg = Image.new("RGB", (480, 1920), (0, 0, 0))
        lcd.DisplayPILImage(bg, 0, 0, 480, 1920)

        self.assertEqual(
            seen_sizes, [(480, 1920)],
            "packer received a pre-cropped image instead of the original 480-wide one -- "
            "content was already lost before it could be scaled",
        )

    def test_map_view_to_glass_scales_portrait_y(self):
        # Declared height == glass height (1920) -- see class docstring on
        # why this must be 1:1: an 8.8" theme borrowed via the size picker
        # (also declared 1920 tall) crashed a DisplayText bounds assert when
        # the declared height was 1760 while the background path already
        # filled the full 1920-tall glass regardless.
        lcd = MockedLcdCommRevC(display_width=440, display_height=1920)
        lcd.lcd_serial.read.return_value = b"chs_113inch.dev1_rom1.90"
        lcd.InitializeComm()
        self.assertEqual(lcd._map_113inch_view_to_glass(10, 0, 40, 1920), (10, 0, 40, 1920))
        self.assertEqual(lcd._map_113inch_view_to_glass(10, 960, 40, 192), (10, 960, 40, 192))
        # Clamp: a widget that would run past the bottom edge gets trimmed.
        self.assertEqual(lcd._map_113inch_view_to_glass(10, 1900, 40, 50), (10, 1900, 40, 20))
