import pathlib
import unittest

LCD_DIRECTORY = pathlib.Path(__file__).parents[3] / "library" / "lcd"


class TestQueueUsage(unittest.TestCase):
    # The transmission-unit queue protocol is only implemented by the serial LcdComm drivers.
    # The Turing USB driver talks USB directly and the simulated driver draws synchronously:
    # both must never consume config.update_queue items (there is no QueueHandler draining them).

    def test_usb_and_simulated_drivers_never_queue_requests(self):
        for filename in ["lcd_comm_turing_usb.py", "lcd_simulated.py"]:
            source = (LCD_DIRECTORY / filename).read_text(encoding="utf-8")
            self.assertNotIn("update_queue.put(", source, f"{filename} must not put on the update queue")
            self.assertNotIn("_queue_request(", source, f"{filename} must not use the TU queue helper")


if __name__ == "__main__":
    unittest.main()
