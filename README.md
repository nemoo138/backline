# EvoBackline

这个 Backline fork 为 EvoDecode 提供 `backline-decoder-runtime`，负责请求分片、任务队列和本地 Python 回调；EvoDecode 负责准备数据、加载模型和解码。

[用户指南](packages/decoder-runtime/README.md) · [开发者指南](docs/developer.md) · [Agent 工作指南](AGENTS.md)

<a id="先运行无权重示例"></a><a id="接口与使用限制"></a>

## 试用本地回调

在 Linux、Python 3.11+ 及支持 C++20 的虚拟环境中，从仓库根目录运行：

```bash
python -m pip install ./packages/decoder-runtime
python demos/demo_decoder_callback.py
```

终端应显示两个请求的结果 `0` 和 `1`，并输出 `PASS`。创建环境、编译及回调接口见[用户指南](packages/decoder-runtime/README.md)。

<a id="接入-evodecode"></a>

| 任务 | 入口 |
| --- | --- |
| 使用 EvoDecode 的回放或实时测量 | [SDK 环境与 runtime 配套安装](packages/decoder-runtime/README.md#在-evodecode-中部署) |
| 复现上游 CPU、RDMA、GPU 或 FPGA 演示 | [按硬件准备环境](INSTALL.md) · [运行演示](demos/README.md) · [测量与基准](benchmarks/README.md) |
| 查看队列、回调、原生符号和源码构建过程 | [架构与验收](docs/developer.md) |

<a id="与-evodecode-的分工"></a><a id="结构与调用流程"></a><a id="仓库内容"></a><a id="开发与验证"></a>

[仓库分工和调用流程图](docs/developer.md#结构与调用流程)

## 上游来源与许可

本项目基于 [PennyLaneAI/backline](https://github.com/PennyLaneAI/backline)。
本 fork 为 EvoDecode 维护的共享包不代表上游官方发布。
保留的上游演示与测量资料对应论文：
*Python in the front, party in the Backline: compiling quantum workloads across CPUs, GPUs, and FPGAs*。
使用这些研究成果时请保留相应引用：

```bibtex
@misc{lee2026,
  title={Python in the front, party in the Backline: compiling quantum workloads across CPUs, GPUs, and FPGAs},
  author={Joseph K. L. Lee and Mehrdad Malekmohammadi and Hong-Sheng Zheng and Shuli Shu and Cheick Doumbia and Kalman Szenes and Mehran Zamani Abnili and Thomas Ainsworth and Matthew Seymour and Thomas Germain and Leonhard Neuhaus and Josh Izaac and Lee J. O'Riordan},
  year={2026},
  eprint={2609.09270},
  archivePrefix={arXiv},
  primaryClass={quant-ph},
  url={https://arxiv.org/abs/2609.09270},
}
```

代码遵循 [Apache License 2.0](LICENSE)。共享包的来源说明见
[NOTICE](packages/decoder-runtime/src/backline_decoder_runtime/NOTICE)。

AMD、AMD Ryzen、AMD Ryzen Threadripper、AMD Instinct、AMD ROCm、Radeon、Versal 和
Xilinx 是 Advanced Micro Devices, Inc. 的商标。
