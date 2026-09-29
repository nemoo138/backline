# EvoDecode 组件复用

这里保留旧演示使用的解码适配接口。需要安装包含 `ResidentAQ2Decoder` 和
`evodecode.backends.backline.lightning_source` 的 EvoDecode 源码版本；仅凭
`0.3.0` 版本号不能判断接口是否齐全。

- `gpu_decoder.AQ2` 对原生 v3 checkpoint 调用 EvoDecode 的常驻推理接口。
- `lightning_source.LightningSource` 直接导入 EvoDecode 门执行器。
- `aq2_checkpoint.py` 保留外部 AQ2 模型兼容路径，需要用户自己的 checkpoint
  及同目录的 `runtime/` 源码。历史默认模型路径不是随仓库提供的模型。
- `gpu_decoder.Ising` 保留原接口，本次没有接入正式 Backline worker。

旧 AQ2 测量源支持更多轮数和混合噪声，暂时保留其逻辑，只复用门执行器。
本提交只纳入适配源码、其直接依赖和测试；完整旧演示入口、其他演示源文件、
模型、报告与运行记录没有纳入。正式运行使用 EvoDecode 的 `examples/backline/` 模板。

安装上述 EvoDecode 和 Torch、Backline 依赖后，从 Backline 根目录执行：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 JAX_PLATFORMS=cpu python -m unittest discover -s demos/evodecode -p test_integrated_aq2.py -v
```
