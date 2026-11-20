import queue
import unittest
from types import SimpleNamespace

from library import config
from .scheduler_stub import import_scheduler

scheduler = import_scheduler()

REGION_A = (0, 0, 10, 10)
REGION_B = (20, 20, 5, 5)


class TestUpdateQueueCoalescing(unittest.TestCase):
    def setUp(self):
        while not config.update_queue.empty():
            config.update_queue.get_nowait()
        self.executed = []
        self.saved_driver = config.display_driver
        config.display_driver = None

    def tearDown(self):
        config.display_driver = self.saved_driver

    def put(self, name, region_key=None, tu_id=None, line=None):
        def fn(arg):
            self.executed.append((name, arg))

        config.update_queue.put((fn, [name if line is None else line], region_key, tu_id))

    def drain(self):
        scheduler._process_update_queue(block=False)

    def test_stale_frames_for_same_region_are_superseded(self):
        self.put("A1", REGION_A, tu_id=1)
        self.put("A2", REGION_A, tu_id=2)
        self.put("A3", REGION_A, tu_id=3)
        self.drain()
        self.assertEqual([name for name, _ in self.executed], ["A3"])

    def test_single_pending_update_is_transmitted(self):
        self.put("A1", REGION_A, tu_id=1)
        self.drain()
        self.assertEqual([name for name, _ in self.executed], ["A1"])

    def test_cross_region_order_preserved(self):
        # text@A, graph@B, text@A-new => A-new (at A first-appearance slot), then B
        self.put("A1", REGION_A, tu_id=1)
        self.put("B1", REGION_B, tu_id=2)
        self.put("A2", REGION_A, tu_id=3)
        self.drain()
        self.assertEqual([name for name, _ in self.executed], ["A2", "B1"])

    def test_transmission_unit_stays_atomic(self):
        # One image = command + chunks sharing a tu_id: they must execute contiguously,
        # and a superseded unit must not leak individual lines
        self.put("cmd-old", REGION_A, tu_id=1, line=b"\x01")
        self.put("chunk-old", REGION_A, tu_id=1, line=b"\x02")
        self.put("cmd-new", REGION_A, tu_id=2, line=b"\x03")
        self.put("chunk-new", REGION_A, tu_id=2, line=b"\x04")
        self.put("cmd-b", REGION_B, tu_id=3, line=b"\x05")
        self.drain()
        self.assertEqual([arg for _, arg in self.executed], [b"\x03", b"\x04", b"\x05"])

    def test_control_items_keep_sequence_and_are_never_coalesced(self):
        # Brightness-like untagged items between two frames of one region: the pending stale frame
        # may be dropped, but the control item must run between it and... in order position
        self.put("A1", REGION_A, tu_id=1)
        self.put("brightness", None, None)
        self.put("A2", REGION_A, tu_id=2)
        self.drain()
        # A1 superseded by A2; brightness keeps its own slot (first-appearance order)
        self.assertEqual([name for name, _ in self.executed], ["A2", "brightness"])

    def test_backward_compatible_two_tuple_items(self):
        config.update_queue.put((lambda arg: self.executed.append(("legacy", arg)), ["x"]))
        self.drain()
        self.assertEqual([name for name, _ in self.executed], ["legacy"])

    def test_sustained_overload_stays_bounded(self):
        for i in range(1000):
            self.put(f"A{i}", REGION_A, tu_id=i + 1)
        self.drain()
        self.assertEqual([name for name, _ in self.executed], ["A999"])


class TestUpdateQueueDeduplication(unittest.TestCase):
    def setUp(self):
        while not config.update_queue.empty():
            config.update_queue.get_nowait()
        self.executed = []
        self.cache = {}
        self.saved_driver = config.display_driver
        config.display_driver = SimpleNamespace(_last_sent_payload=self.cache)

    def tearDown(self):
        config.display_driver = self.saved_driver

    def put_frame(self, payload, tu_id, region_key=REGION_A):
        def fn(arg):
            self.executed.append(arg)

        config.update_queue.put((fn, [payload], region_key, tu_id))

    def drain(self):
        scheduler._process_update_queue(block=False)

    def test_identical_payload_skipped_then_sent_again_when_changed(self):
        self.put_frame(b"same", tu_id=1)
        self.drain()
        self.assertEqual(self.executed, [b"same"])

        self.put_frame(b"same", tu_id=2)
        self.drain()
        self.assertEqual(self.executed, [b"same"])  # skipped: device already shows it

        self.put_frame(b"other", tu_id=3)
        self.drain()
        self.assertEqual(self.executed, [b"same", b"other"])

    def test_identical_payload_resent_after_screen_cleared(self):
        self.put_frame(b"same", tu_id=1)
        self.drain()
        self.cache.clear()  # what Clear()/Reset() do on the driver
        self.put_frame(b"same", tu_id=2)
        self.drain()
        self.assertEqual(self.executed, [b"same", b"same"])

    def test_no_dedup_without_driver_cache(self):
        config.display_driver = None
        self.put_frame(b"same", tu_id=1)
        self.drain()
        self.put_frame(b"same", tu_id=2)
        self.drain()
        self.assertEqual(self.executed, [b"same", b"same"])

    def test_dedup_is_per_region(self):
        self.put_frame(b"same", tu_id=1, region_key=REGION_A)
        self.drain()
        self.put_frame(b"same", tu_id=2, region_key=REGION_B)
        self.drain()
        self.assertEqual(self.executed, [b"same", b"same"])


if __name__ == "__main__":
    unittest.main()
