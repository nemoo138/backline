"""Actual C++ queue checks without PennyLane or a GPU."""
import ctypes
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from backline_decoder_runtime import NativeCallback, build_coprocessor


@unittest.skipUnless(shutil.which("c++"), "requires C++20 compiler")
class BacklineProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        library = Path(cls.temp.name) / "coprocessor.so"
        build_coprocessor(library)
        cls.bridge = ctypes.CDLL(str(library))
        cls.call = cls.bridge.evodecode_coprocessor
        cls.call.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
        cls.call.restype = ctypes.c_size_t

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def message(self, kind, data):
        request = ctypes.create_string_buffer(data + struct.pack("<II", kind, 0))
        response = ctypes.create_string_buffer(8)
        self.assertEqual(self.call(request, 16, response, 8, None), 8)
        return tuple(response.raw[:2])

    def submit(self, shot):
        self.assertEqual(self.message(1, struct.pack("<II", 8, 1))[1], 0)
        self.assertEqual(self.message(2, bytes(8))[1], 0)
        return self.message(3, struct.pack("<Q", shot))

    def test_full_queue_duplicate_id_and_unknown_collection(self):
        with NativeCallback(self.bridge, lambda data: 1, queue_depth=1):
            self.assertEqual(self.submit(0), (0, 0))
            self.assertNotEqual(self.submit(1)[1], 0)
            self.assertEqual(self.message(4, struct.pack("<Q", 0)), (1, 0))
            self.assertNotEqual(self.submit(0)[1], 0)
            self.assertEqual(self.submit(1), (0, 0))
            self.assertEqual(self.message(4, struct.pack("<Q", 1)), (1, 0))
            self.assertNotEqual(self.message(4, struct.pack("<Q", 99))[1], 0)

    def test_callback_failure_is_reported_and_lifecycle_can_restart(self):
        def fail(data):
            raise ValueError("deliberate decoder failure")
        with NativeCallback(self.bridge, fail, queue_depth=1) as binding:
            self.assertEqual(self.submit(0)[1], 0)
            self.assertEqual(self.message(4, struct.pack("<Q", 0))[1], 2)
            self.assertIn("deliberate decoder failure", binding.error)
        with NativeCallback(self.bridge, lambda data: 0, queue_depth=1):
            self.assertEqual(self.submit(0)[1], 0)
            self.assertEqual(self.message(4, struct.pack("<Q", 0)), (0, 0))

    def test_truncated_request_is_rejected(self):
        with NativeCallback(self.bridge, lambda data: 0, request_size=16, queue_depth=1):
            self.assertEqual(self.message(1, struct.pack("<II", 16, 1))[1], 0)
            self.assertEqual(self.message(2, bytes(8))[1], 0)
            self.assertNotEqual(self.message(3, bytes(8))[1], 0)


if __name__ == "__main__":
    unittest.main()
