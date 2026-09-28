"""Shared Backline decoder runtime (independent of EvoDecode and GPU libraries)."""
from .native_callback import CALLBACK, NativeCallback
from .build import build_coprocessor

__version__ = "0.1.0"
__all__ = ["CALLBACK", "NativeCallback", "build_coprocessor"]
