"""Native adapter equivalence and separation from external checkpoints."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class IntegratedAQ2Tests(unittest.TestCase):
    def test_native_prediction_and_checkpoint_validation(self):
        import numpy as np
        import torch
        from evodecode.backends.aq2 import worker
        from evodecode.backends.aq2.runtime import build_aq2_model
        from evodecode.backends.backline.aq2_source import AQ2LiveSource
        from evodecode.domain.models import CodeSpec, QECFrame
        from evodecode.core.errors import ConfigError
        from gpu_decoder import AQ2
        cfg = dict(d_model=8, nhead=2, dim_feedforward=16, attn_key_size=4, temporal_k=3, dropout=0.0)
        for basis in ('X', 'Z'):
            code = CodeSpec('surface', 'rotated_surface', 3, 3, basis).to_dict()
            source = AQ2LiveSource(code, 7)
            frame = QECFrame.from_mapping(source.frame(np.zeros(source.num_measurements, dtype=np.uint8)))
            spec = {'code': code, 'decoder': {'model': cfg}}
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                checkpoint = work / 'model.pt'
                torch.manual_seed(7)
                model = build_aq2_model(cfg, [3]).eval()
                torch.save(worker._checkpoint(model, cfg, code, worker.LEGACY_PROTOCOL, None, {}), checkpoint)
                with patch.object(worker, 'ResidentAQ2Decoder', wraps=worker.ResidentAQ2Decoder) as factory:
                    adapter = AQ2(spec, checkpoint, work, torch.device('cpu'))
                    value = frame.to_dict()
                    expected = worker.ResidentAQ2Decoder(checkpoint, cfg, code, torch.device('cpu')).predict(frame)
                    self.assertEqual(adapter.predict(value), expected)
                    value['logical_observables'] = [1]
                    self.assertEqual(adapter.predict(value), expected)
                    self.assertIs(adapter.model, adapter.decoder.model)
                    self.assertEqual(factory.call_count, 2)
                content = torch.load(checkpoint, weights_only=True)
                content['runtime_api_version'] = '2'
                torch.save(content, checkpoint)
                with self.assertRaisesRegex(ConfigError, 'runtime API'):
                    AQ2(spec, checkpoint, work, torch.device('cpu'))

    def test_external_loader_is_preserved(self):
        import torch
        from gpu_decoder import AQ2
        model = Mock()
        with patch('torch.load', return_value={'model_arch': 'aq2'}), \
             patch('aq2_checkpoint.load_model', return_value=(model, {}, {'format': 'external'})) as load, \
             patch('evodecode.backends.aq2.worker.ResidentAQ2Decoder', side_effect=AssertionError('native loader used')):
            adapter = AQ2({'code': {}}, Path('external.pt'), Path('.'), torch.device('cpu'))
            self.assertTrue(adapter.external)
            load.assert_called_once()

    def test_lightning_executor_is_shared(self):
        from lightning_source import LightningSource
        from evodecode.backends.backline.lightning_source import LightningSource as IntegratedSource
        self.assertIs(LightningSource, IntegratedSource)
