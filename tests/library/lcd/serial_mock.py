import os
from unittest.mock import Mock
import unittest

# Set the environment variable to any non-empty string when running the tests
# to record golden files instead of asserting their expectations
RECORD_GOLDEN = bool(os.getenv("RECORD_GOLDEN"))

# Set the environment variable to any non-empty string when running the tests
# to enable benchmarking, i.e. make the serial reads/writes a no-op; and don't
# assert the test expectations. That way, the time to run the tests should be
# mostly representative of the serialization time.
BENCHMARK = bool(os.getenv("BENCHMARK"))

class MockSerial(Mock):
    def expect_golden(self, tc: unittest.TestCase, fn: str):
        golden_dir = os.path.join(os.path.dirname(__file__), "golden")
        full_path = os.path.join(golden_dir, fn + ".txt")

        if RECORD_GOLDEN:
            with open(full_path, "w+", encoding="ascii") as f:
                for method, args, _ in self.mock_calls:
                    if method == "write":
                        assert len(args) == 1
                        f.write(f"write {args[0].hex()}\n")
                    elif method == "read":
                        assert len(args) == 1
                        f.write(f"read {args[0]}\n")
                    # don't record the other methods

        else:
            with open(full_path, "r", encoding="ascii") as f:
                expected = list(filter(lambda l: l.strip() != "", f.readlines()))

                mock_calls = []
                for method, args, _ in self.mock_calls:
                    if method not in ["write", "read"]:
                        continue
                    mock_calls.append((method, args))

                tc.assertEqual(len(mock_calls), len(expected))
                for call, exp in zip(mock_calls, expected):
                    exp_name, exp_arg = exp.split()
                    call_name, call_args = call
                    tc.assertEqual(call_name, exp_name)
                    if call_name == "write":
                        tc.assertEqual(call_args, (bytes.fromhex(exp_arg),))
                    elif call_name == "read":
                        tc.assertEqual(call_args, (int(exp_arg),))

class NoopSerial:
    def write(self, data):
        pass

    def read(self, size):
        pass

    def close(self):
        pass

    def reset_input_buffer(self):
        pass

    def expect_golden(self, tc: unittest.TestCase, fn: str):
        pass


def new_testing_serial():
    if BENCHMARK:
        return NoopSerial()
    else:
        return MockSerial()
