# EvoBackline

EvoBackline 提供 `backline-decoder-runtime`。它把应用提交的字节分片重组成请求，排队调用 Python 函数，再按请求编号返回结果。EvoDecode 使用它做回放和实时解码。

<a id="接入-evodecode"></a>

| 你想做什么 | 从哪里开始 |
| --- | --- |
| 在本机验证队列和 Python 回调 | 运行下方的 CPU 示例 |
| 用 EvoDecode 回放已有帧或实时测量 | [EvoDecode 部署入口](https://github.com/qhub-cn/evo-decode#backline)，配套 SDK 源码中的手册为 `docs/user/deployment.md` |
| 复现上游 CPU、RDMA、GPU 或 FPGA 演示 | [按现有硬件选择安装步骤](INSTALL.md#choose-your-hardware) |

<a id="先运行无权重示例"></a><a id="接口与使用限制"></a>

## 试用本地回调

在 Linux、Python 3.11+ 的虚拟环境中准备支持 C++20 的 `c++` 编译器。把下方路径换成本地 wheel 的位置，安装后可从任意空目录运行。

```bash
python -m pip install ./backline_decoder_runtime-0.1.1-py3-none-any.whl
python -m backline_decoder_runtime.demo
```

```text
request 0: 25 bytes, result=0
request 1: 25 bytes, result=1
PASS: fragmentation, queue, callback, and result collection
```

两个结果是各自 25 个字节的和对 2 取余。分片如何重组、回调收到什么，见[用户指南](packages/decoder-runtime/README.md#运行第一个回调)。

<a id="与-evodecode-的分工"></a><a id="结构与调用流程"></a><a id="仓库内容"></a><a id="开发与验证"></a>

## 维护与验证

[开发者指南](docs/developer.md)说明源码、会话和构建验收。[Agent 工作指南](AGENTS.md)给出按组件选择修改位置和检查命令的约定。

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
