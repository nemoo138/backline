"""Resident, in-process CUDA decoders; uses EvoDecode internal model APIs."""
import json
import os
from pathlib import Path


class AQ2:
    def __init__(self, spec, checkpoint, work, device):
        import torch
        from evodecode.backends.aq2.worker import ResidentAQ2Decoder
        self.device = device
        content = torch.load(checkpoint, map_location="cpu", weights_only=True)
        self.external = content.get("model_arch") == "aq2"
        if self.external:
            from aq2_checkpoint import load_model
            self.model, self.locations, self.model_info = load_model(
                checkpoint, content, spec["code"], device)
        else:
            self.decoder = ResidentAQ2Decoder(
                checkpoint, spec["decoder"]["model"], spec["code"], self.device)
            self.model, self.checkpoint = self.decoder.model, self.decoder.checkpoint
            self.model_info = {"format": self.checkpoint["format"],
                               "model_config": self.checkpoint["model_config"]}
        self.model.eval()

    def predict(self, frame):
        import torch
        from evodecode.domain.models import QECFrame
        with torch.inference_mode():
            if self.external:
                from aq2_checkpoint import tensorize_frame as tensorize_external
                measurements, events, observable = tensorize_external(frame, self.locations)
                logits = self.model(
                    torch.tensor(measurements[None], device=self.device),
                    torch.tensor(events[None], device=self.device),
                    torch.arange(measurements.shape[1], device=self.device),
                    current_distance=int(frame["code"]["distance"]),
                    obs_idx=torch.tensor([observable], device=self.device))
                return int(torch.sigmoid(logits).item() >= 0.5)
            return self.decoder.predict(QECFrame.from_mapping(frame))


class Ising:
    def __init__(self, spec, checkpoint, work, device):
        from evodecode.backends.ising.worker import _public_config, _configure_inference_batch
        from evodecode.backends.ising.runtime.training.distributed import DistributedManager
        from evodecode.backends.ising.runtime.workflows.run import _load_model
        if os.environ.get("PREDECODER_SAFETENSORS_CHECKPOINT", "").strip():
            raise ValueError("unset PREDECODER_SAFETENSORS_CHECKPOINT to load the selected Ising weights")
        self.spec, self.work = spec, work
        self.samples = work / "stim_samples"
        os.environ["PREDECODER_STIM_SAMPLES_DIR"] = str(self.samples)
        os.environ["PREDECODER_INFERENCE_NUM_WORKERS"] = "0"
        os.environ["PREDECODER_TORCH_COMPILE"] = "0"
        os.environ["ONNX_WORKFLOW"] = "0"
        self.cfg = _public_config(spec, noise=spec["dataset"]["noise"], task="inference")
        geometry = (int(spec["code"]["distance"]), int(spec["code"]["rounds"]))
        if ((int(self.cfg.distance), int(self.cfg.n_rounds)) != geometry
                or (int(self.cfg.test.distance), int(self.cfg.test.n_rounds)) != geometry):
            raise ValueError("Ising runtime geometry disagrees with the live source")
        self.cfg.model_checkpoint_file = str(checkpoint)
        self.cfg.output = str(work)
        self.cfg.test.num_samples = 1
        self.cfg.test.meas_basis_test = spec["code"]["basis"]
        self.cfg.test.decode_output_dir = str(work / "decode_arrays")
        _configure_inference_batch(self.cfg, spec, 1)
        self.cfg.test.dataloader.num_workers = 0
        self.cfg.test.dataloader.persistent_workers = False
        self.cfg.test.dataloader.prefetch_factor = None
        self.cfg.torch_compile = False
        self.dist = DistributedManager()
        if self.dist.world_size != 1:
            raise ValueError("this demo requires a single-process CUDA environment")
        self.dist.device = device
        self.dist.local_rank = device.index
        self.device = device
        self.model = _load_model(self.cfg, self.dist)
        self.model.eval()
        self.model_info = {"format": "ising", "model_id": spec["decoder"]["model_id"],
            "parameters": sum(p.numel() for p in self.model.parameters()), "strict_state_dict": True,
            "inference_batch_size": 1, "inference_code": dict(spec["code"]), "skip_noise_upscaling": bool(spec["dataset"].get("skip_noise_upscaling", False)),
            "global_decoder": "pymatching", "postprocessing_device": "cpu"}

    def predict(self, frame):
        import numpy as np
        from evodecode.backends.ising.worker import _export_surface_samples
        from evodecode.backends.ising.runtime.evaluation.logical_error_rate import count_logical_errors_with_errorbar
        frames = self.work / "request.jsonl"
        frames.write_text(json.dumps(frame) + "\n")
        _export_surface_samples(self.spec, frames, self.samples)
        predictions = Path(self.cfg.test.decode_output_dir) / (
            self.spec["code"]["basis"] + "_ising_decoding_pymatching_predictions.npy"
        )
        predictions.unlink(missing_ok=True)  # never return an old request's output
        count_logical_errors_with_errorbar(self.model, self.device, self.dist, self.cfg)
        values = np.load(predictions).reshape(-1)
        if len(values) != 1 or values[0] not in (0, 1):
            raise RuntimeError("Ising did not produce exactly one binary prediction")
        return int(values[0])
