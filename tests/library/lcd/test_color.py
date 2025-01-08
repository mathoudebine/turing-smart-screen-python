import unittest

from library.lcd.color import parse_color


class TestColor(unittest.TestCase):
    def test_parse_color(self):
        self.assertEqual(parse_color("255, 0, 0"), (255, 0, 0))
        self.assertEqual(parse_color("red"), (255, 0, 0))
        self.assertEqual(parse_color("#f00"), (255, 0, 0))
        self.assertEqual(parse_color("#ff0000"), (255, 0, 0))
        self.assertEqual(parse_color((255, 0, 0)), (255, 0, 0))
