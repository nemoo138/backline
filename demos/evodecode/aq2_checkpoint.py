"""Load the local AQ2-full checkpoint and adapt canonical XV surface frames.

The snapshot preserves the training model's positional encoding and auxiliary
heads. The input adapter reflects canonical coordinates into the training layout
and reconstructs measurement features as cumulative detector parity.
"""
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np

DATA_SCHEMA = "aq2-xzzx-cz-modern-si1000-v1"
DEFAULT_CHECKPOINT = (Path(__file__).resolve().parents[2] / "models" /
    "aq2_full_d357_rebuild_20260915" / "aq2_full_d357_50m_step670000.pth")


def load_runtime(checkpoint):
    """Import the accompanying snapshot without adding a global 'src' package."""
    root = Path(checkpoint).resolve().parent / "runtime"
    name = "_backline_aq2_" + hashlib.sha256(str(root).encode()).hexdigest()[:12]
    if name + ".model" in sys.modules:
        return sys.modules[name + ".model"]
    for suffix, path in [("", root / "__init__.py"), (".model", root / "model.py")]:
        spec = importlib.util.spec_from_file_location(name + suffix, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"missing AQ2 runtime snapshot: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name + suffix] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name + suffix, None)
            raise
    return module


def load_model(checkpoint_path, checkpoint, code, device):
    import torch.utils.checkpoint  # the upstream forward uses torch.utils.checkpoint

    config = checkpoint.get("model_config", {})
    if (checkpoint.get("model_arch") != "aq2"
            or config.get("architecture_schema") != "aq2-full-v1"
            or checkpoint.get("data_schema_version") != DATA_SCHEMA):
        raise ValueError("expected an aq2-full-v1 checkpoint with modern XZZX SI1000 schema")
    distances = config.get("distances", [])
    if int(code["distance"]) not in distances:
        raise ValueError("checkpoint does not support the requested distance")
    if checkpoint.get("basis") not in (None, code["basis"]):
        raise ValueError("checkpoint basis does not match the circuit")
    runtime = load_runtime(checkpoint_path)
    options = {key: config[key] for key in (
        "distances", "num_rounds", "d_model", "nhead", "dim_feedforward",
        "dropout", "attn_key_size", "temporal_K")}
    model = runtime.GoogleDecoder(**options)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.to(device).eval()
    info = {
        "format": "upstream-aq2-full-v1", "step": int(checkpoint["step"]),
        "examples_seen": int(checkpoint["examples_seen"]), "model_config": config,
        "training_data_schema": DATA_SCHEMA, "weights": "model_state_dict",
        "input_adapter": "canonical-XV-reflection-and-detector-cumulative-xor/v1",
        "runtime": str(Path(checkpoint_path).resolve().parent / "runtime/model.py"),
        "training_eval_rounds": checkpoint.get("training_profile", {}).get("eval_rounds"),
    }
    return model, runtime.STABILIZER_LOCATIONS, info


def tensorize_frame(frame, locations):
    """Map XV CSS syndromes to the model's slots while preserving its logical line.

    X memory reflects y; Z memory reflects x. In each case the logical readout
    line stays on the same boundary as Stim's rotated memory convention. The
    physical noise remains the live circuit's configured Pauli-25 distribution.
    """
    code = frame["code"]
    if frame.get("circuit_metadata", {}).get("data_schema") == DATA_SCHEMA:
        events = np.asarray(frame["detection_events"], dtype=np.float32)
        if events.shape != (int(code["rounds"]) + 1, int(code["distance"])**2 - 1):
            raise ValueError("invalid checkpoint-aligned detector shape")
        if np.any((events != 0) & (events != 1)):
            raise ValueError("detector values must be binary")
        measurements = np.logical_xor.accumulate(events.astype(bool), axis=0).astype(np.float32)
        return measurements, events, int(code["basis"] == "X")
    distance = int(code["distance"])
    basis = code["basis"]
    if (code["family"], code["variant"], basis) not in {
        ("surface", "rotated_surface", "X"), ("surface", "rotated_surface", "Z")
    } or frame["boundary_definition"].get("rotation") != "XV":
        raise ValueError("AQ2 checkpoint adapter requires canonical XV surface X/Z memory")
    coordinates = frame["stabilizer_coordinates"]
    mapped = {}
    for index, (x, y) in enumerate(coordinates):
        if x != int(x) or y != int(y):
            raise ValueError("stabilizer coordinates must be integral")
        coordinate = (int(x), 2 * distance - int(y)) if basis == "X" else (2 * distance - int(x), int(y))
        if coordinate in mapped:
            raise ValueError("duplicate stabilizer coordinate")
        mapped[coordinate] = index
    expected = [tuple(c) for c in locations[distance]]
    if set(mapped) != set(expected):
        raise ValueError("canonical coordinates do not match checkpoint stabilizer slots")
    order = [mapped[c] for c in expected]
    rows = np.asarray(frame["detection_events"], dtype=np.int64)
    if rows.shape != (int(code["rounds"]), distance**2 - 1) or np.any((rows != 0) & (rows != 1)):
        raise ValueError("invalid detector rows")
    basis_indices = [i for i, kind in enumerate(frame["stabilizer_types"]) if kind == basis]
    boundary = np.asarray(frame["boundary_detection_events"], dtype=np.int64)
    if boundary.shape != (len(basis_indices),) or np.any((boundary != 0) & (boundary != 1)):
        raise ValueError("invalid boundary detectors")
    final = np.zeros(distance**2 - 1, dtype=np.int64)
    final[basis_indices] = boundary
    events = np.concatenate((rows, final[None, :]), axis=0)[:, order].astype(np.float32)
    measurements = np.logical_xor.accumulate(events.astype(bool), axis=0).astype(np.float32)
    return measurements, events, 1 if basis == "X" else 0
