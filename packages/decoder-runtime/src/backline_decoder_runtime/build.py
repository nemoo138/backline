"""Build the bundled ABI-compatible queue inside the caller's run directory."""
from importlib.resources import as_file, files
from pathlib import Path
import re
import shutil
import subprocess
import sys


def build_coprocessor(output: Path, *, compiler: str = "c++",
                      entry_symbol: str = "evodecode_coprocessor") -> Path:
    """Compile a bridge exporting the C entry point requested by the controller."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", entry_symbol):
        raise ValueError("entry_symbol must be a C identifier")
    if not sys.platform.startswith("linux"):
        raise RuntimeError("Backline decoder runtime requires Linux")
    executable = shutil.which(compiler)
    if executable is None:
        raise RuntimeError(f"Backline requires a C++20 compiler: {compiler}")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with as_file(files("backline_decoder_runtime").joinpath("coprocessor.cpp")) as source:
        subprocess.run([executable, "-std=c++20", "-O2", "-shared", "-fPIC", "-pthread",
                        f"-DEVODECODE_ENTRY_SYMBOL={entry_symbol}", str(source), "-o", str(output)], check=True)
    return output
