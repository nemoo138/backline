"""Wire/ABI regression tests using Python and a C++ compiler."""
import ctypes
from pathlib import Path
import struct
import tempfile
import threading
import unittest

from backline_decoder_runtime import CALLBACK, NativeCallback


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        library = Path(cls.temp.name) / "bridge.so"
        from backline_decoder_runtime import build_coprocessor
        build_coprocessor(library)
        cls.bridge = ctypes.CDLL(str(library))
        cls.bridge.evodecode_set_callback.argtypes = [CALLBACK]
        cls.bridge.evodecode_set_callback.restype = None
        cls.fn = cls.bridge.evodecode_coprocessor
        cls.fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
        cls.fn.restype = ctypes.c_size_t

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def tearDown(self):
        self.bridge.evodecode_set_callback(CALLBACK())

    def call(self, payload, decoder_id=0):
        wire = ctypes.create_string_buffer(payload + struct.pack("<II", decoder_id, 37))
        output = ctypes.create_string_buffer(8)
        self.assertEqual(self.fn(wire, 16, output, 8, None), 8)
        return output.raw

    def test_payload_calls_same_process_decoder_and_returns_prediction(self):
        import os
        observed = []
        def predict(payload):
            observed.append(payload)
            return 1
        with NativeCallback(self.bridge, predict) as binding:
            self.assertEqual(self.call(bytes(range(8))), b"\x01" + b"\x00" * 7)
        self.assertEqual(observed, [bytes(range(8))])
        self.assertEqual(binding.calls[0]["pid"], os.getpid())
        self.assertEqual(self.call(bytes(range(8)))[1], 1)

    def test_exception_returns_error_and_preserves_original_traceback(self):
        def broken(payload):
            raise RuntimeError("inference failed")
        with NativeCallback(self.bridge, broken) as binding:
            reply = self.call(bytes(range(8)))
        self.assertEqual(reply[1], 2)
        self.assertIn("inference failed", binding.error)
        self.assertEqual(binding.calls, [])

    def test_invalid_prediction_is_not_a_successful_zero(self):
        with NativeCallback(self.bridge, lambda payload: 5) as binding:
            self.assertEqual(self.call(bytes(range(8)))[1], 2)
            self.assertIn("nonbinary", binding.error)

    def test_missing_callback_and_unknown_decoder_return_error(self):
        self.bridge.evodecode_set_callback(CALLBACK())
        self.assertEqual(self.call(bytes(range(8)))[1], 1)
        with NativeCallback(self.bridge, lambda payload: 1):
            self.assertEqual(self.call(bytes(range(8)), decoder_id=3)[1], 1)

    def test_fragmented_request_calls_model_only_after_finish(self):
        payload = bytes(range(25))
        with NativeCallback(self.bridge, lambda data: int(data == payload), request_size=25) as binding:
            self.assertEqual(self.call(struct.pack("<II", 25, 1), 1)[1], 0)
            padded = payload + bytes(7)
            for offset in range(0, 32, 8):
                self.assertEqual(self.call(padded[offset:offset+8], 2)[1], 0)
                self.assertEqual(binding.calls, [])
            self.assertEqual(self.call(bytes(8), 3)[:2], b"\x01\x00")
            self.assertEqual(len(binding.calls), 1)
            self.assertEqual(binding.calls[0]["request_hex"], payload.hex())
            self.assertEqual(self.call(bytes(8), 3)[1], 1)

    def test_fragment_rejects_incomplete_overflow_and_padding(self):
        with NativeCallback(self.bridge, lambda _: 1, request_size=9) as binding:
            self.assertEqual(self.call(bytes(8), 2)[1], 1)
            for size in (0, 8, 4097):
                self.assertEqual(self.call(struct.pack("<II", size, 1), 1)[1], 1)
            self.assertEqual(self.call(struct.pack("<II", 9, 9), 1)[1], 1)
            self.call(struct.pack("<II", 9, 1), 1)
            self.call(bytes(8), 2)
            self.assertEqual(self.call(bytes(8), 3)[1], 1)
            self.call(struct.pack("<II", 9, 1), 1)
            self.call(bytes(8), 2)
            self.call(b"\x00\x01" + bytes(6), 2)
            self.assertEqual(self.call(bytes(8), 3)[1], 1)
            self.call(struct.pack("<II", 9, 1), 1)
            self.call(bytes(8), 2)
            self.call(bytes(8), 2)
            self.assertEqual(self.call(bytes(8), 2)[1], 1)
            self.assertEqual(self.call(bytes(8), 3)[1], 1)
            self.assertEqual(binding.calls, [])

    def test_callback_teardown_discards_partial_request(self):
        with NativeCallback(self.bridge, lambda _: 1, request_size=9):
            self.call(struct.pack("<II", 9, 1), 1)
            self.call(bytes(8), 2)
        with NativeCallback(self.bridge, lambda _: 1, request_size=9) as binding:
            self.assertEqual(self.call(bytes(8), 3)[1], 1)
            self.assertEqual(binding.calls, [])

    def submit(self, payload, shot):
        self.assertEqual(self.call(struct.pack("<II", len(payload), 1), 1)[1], 0)
        padded = payload + bytes((-len(payload)) % 8)
        for offset in range(0, len(padded), 8):
            self.assertEqual(self.call(padded[offset:offset+8], 2)[1], 0)
        return self.call(struct.pack("<Q", shot), 3)

    def test_pipeline_acknowledges_before_inference_and_bounds_uncollected_results(self):
        started, release = threading.Event(), threading.Event()
        payloads = [bytes([i]) * 25 for i in range(3)]
        def predict(payload):
            started.set()
            if not release.wait(3):
                raise RuntimeError("submission blocked on inference")
            return payload[0] % 2
        with NativeCallback(self.bridge, predict, 25, queue_depth=2) as binding:
            try:
                self.assertEqual(self.submit(payloads[0], 0)[1], 0)
                self.assertTrue(started.wait(1))
                self.assertEqual(binding.calls, [])
                # The transport is still responsive while the first callback is blocked.
                self.assertEqual(self.submit(payloads[1], 1)[1], 0)
                self.assertEqual(self.submit(payloads[2], 2)[1], 3)
                self.assertEqual(self.submit(payloads[1], 1)[1], 3)
                self.assertEqual(self.call(struct.pack("<Q", 99), 4)[1], 1)
            finally:
                release.set()
            # Collect out of order: shot ID, not arrival order, chooses the result.
            self.assertEqual(self.call(struct.pack("<Q", 1), 4)[:2], b"\x01\x00")
            self.assertEqual(self.submit(payloads[2], 2)[1], 0)
            self.assertEqual(self.call(struct.pack("<Q", 0), 4)[:2], b"\x00\x00")
            self.assertEqual(self.call(struct.pack("<Q", 2), 4)[:2], b"\x00\x00")
            self.assertEqual(self.call(struct.pack("<Q", 2), 4)[1], 1)
        self.assertEqual([c["request_hex"] for c in binding.calls], [p.hex() for p in payloads])
        self.assertTrue(all(c["thread_id"] != threading.get_native_id() for c in binding.calls))

    def test_pipeline_reports_exception_at_collection_and_continues(self):
        def predict(payload):
            if payload[0] == 0: raise RuntimeError("asynchronous inference failed")
            return 1
        with NativeCallback(self.bridge, predict, 8, queue_depth=2) as binding:
            self.assertEqual(self.submit(bytes(8), 0)[1], 0)
            self.assertEqual(self.submit(bytes([1]) * 8, 1)[1], 0)
            self.assertEqual(self.call(struct.pack("<Q", 0), 4)[1], 2)
            self.assertEqual(self.call(struct.pack("<Q", 1), 4)[:2], b"\x01\x00")
        self.assertIn("asynchronous inference failed", binding.error)
        self.assertEqual(len(binding.calls), 1)

    def test_pipeline_teardown_drains_jobs_and_new_session_resets_ids(self):
        for _ in range(2):
            with NativeCallback(self.bridge, lambda _: 1, 8, queue_depth=2) as binding:
                self.assertEqual(self.submit(bytes(8), 0)[1], 0)
                self.assertEqual(self.submit(bytes(8), 1)[1], 0)
            self.assertEqual(len(binding.calls), 2)
        self.assertEqual(self.call(struct.pack("<Q", 0), 4)[1], 1)

    def test_pipeline_rejects_invalid_capacity(self):
        for capacity in (-1, 257):
            with self.assertRaises(RuntimeError):
                with NativeCallback(self.bridge, lambda _: 1, queue_depth=capacity):
                    self.fail("invalid queue capacity accepted")

    def test_short_request_and_output_do_not_overrun_buffers(self):
        with NativeCallback(self.bridge, lambda payload: 1):
            src = ctypes.create_string_buffer(8)
            dst = ctypes.create_string_buffer(b"sentinel")
            self.assertEqual(self.fn(src, 8, dst, 8, None), 8)
            self.assertEqual(dst.raw[1], 1)
            dst.value = b"sentinel"
            self.assertEqual(self.fn(src, 8, dst, 4, None), 0)
            self.assertEqual(dst.value, b"sentinel")


if __name__ == "__main__":
    unittest.main()
