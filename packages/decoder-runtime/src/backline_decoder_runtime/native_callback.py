"""Keep a Python decode callable alive while the Backline native thread uses it."""
import ctypes
import os
import threading
import traceback
import time

CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t)


class NativeCallback:
    def __init__(self, bridge, predict, request_size=8, queue_depth=0):
        self.bridge = bridge
        self.predict = predict
        self.request_size = request_size
        self.queue_depth = queue_depth
        self.error = None
        self.calls = []
        self.callback = CALLBACK(self._invoke)
        bridge.evodecode_set_callback.argtypes = [CALLBACK]
        bridge.evodecode_set_callback.restype = None

    def _invoke(self, pointer, size):
        # ctypes acquires the GIL when entering from Backline's native thread.
        # Catalyst releases the GIL while executing/waiting in the compiled QNode.
        started = time.perf_counter_ns()
        try:
            if size != self.request_size:
                raise ValueError(f"expected a {self.request_size}-byte request")
            payload = ctypes.string_at(pointer, size)
            prediction = int(self.predict(payload))
            if prediction not in (0, 1):
                raise ValueError("decoder returned a nonbinary prediction")
            self.calls.append({"request_hex": payload.hex(), "prediction": prediction,
                               "pid": os.getpid(), "thread_id": threading.get_native_id(),
                               "decode_start_ns": started, "decode_end_ns": time.perf_counter_ns()})
            return prediction
        except BaseException:
            # An uncaught ctypes callback exception would leave an undefined C result.
            self.error = traceback.format_exc()
            return -1

    def __enter__(self):
        self.bridge.evodecode_set_callback(self.callback)
        if self.queue_depth:
            self.bridge.evodecode_start_pipeline.argtypes = [ctypes.c_size_t]
            self.bridge.evodecode_start_pipeline.restype = ctypes.c_int
            if self.bridge.evodecode_start_pipeline(self.queue_depth):
                self.bridge.evodecode_set_callback(CALLBACK())
                raise RuntimeError("could not start the bounded decode pipeline")
        return self

    def __exit__(self, *_):
        self.bridge.evodecode_set_callback(CALLBACK())
