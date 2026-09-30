#!/usr/bin/env python3
"""Exercise the native fragment/queue/callback ABI without models or hardware.

This calls the shared C ABI directly. It does not exercise a Catalyst QNode,
CUDA, RDMA, or FPGA transport; use the numbered demos for those integrations.
"""
import ctypes
from pathlib import Path
import struct
import tempfile

from backline_decoder_runtime import NativeCallback, build_coprocessor


def main():
    with tempfile.TemporaryDirectory(prefix='backline-callback-') as directory:
        bridge = ctypes.CDLL(str(build_coprocessor(Path(directory)/'callback.so')))
        call = bridge.evodecode_coprocessor
        call.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                         ctypes.c_size_t, ctypes.c_void_p]
        call.restype = ctypes.c_size_t

        def message(command, data):
            if len(data) != 8:
                raise ValueError('each command carries exactly eight bytes')
            request = ctypes.create_string_buffer(data + struct.pack('<II', command, 0))
            response = ctypes.create_string_buffer(8)
            if call(request, 16, response, 8, None) != 8:
                raise RuntimeError('unexpected response length')
            if response.raw[1]:
                raise RuntimeError(f'command {command} failed with status {response.raw[1]}')
            return response.raw[0]

        # A deliberately simple callback: return byte-sum parity, not a QEC model.
        payloads = [bytes(range(25)), bytes([1])+bytes(range(1,25))]
        with NativeCallback(bridge, lambda data: sum(data) % 2,
                            request_size=25, queue_depth=2) as binding:
            for shot, payload in enumerate(payloads):
                message(1, struct.pack('<II', len(payload), 1))
                padded = payload + bytes((-len(payload)) % 8)
                for offset in range(0, len(padded), 8):
                    message(2, padded[offset:offset+8])
                message(3, struct.pack('<Q', shot))
            for shot, payload in enumerate(payloads):
                prediction = message(4, struct.pack('<Q', shot))
                if prediction != sum(payload) % 2:
                    raise RuntimeError('callback result differs from submitted bytes')
                print(f'request {shot}: {len(payload)} bytes, result={prediction}')
        if binding.error or [c['request_hex'] for c in binding.calls] != [p.hex() for p in payloads]:
            raise RuntimeError(binding.error or 'callback audit mismatch')
        print('PASS: fragmentation, queue, callback, and result collection')


if __name__ == '__main__':
    main()
