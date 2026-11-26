# EvoBackline

EvoBackline 提供 `backline-decoder-runtime`。它把应用提交的字节分片重组成请求，排队调用 Python 函数，再按请求编号返回结果。EvoDecode 使用它做回放和实时解码。

![编号 0 的请求分成四片，经 Backline 重组为 25 字节并排队。Python 回调计算字节和的奇偶性，应用按编号领取结果 0。](assets/request-round-trip.svg)

<a id="试用本地回调"></a><a id="先运行无权重示例"></a><a id="接口与使用限制"></a>

## 本地回调示例

准备一台 Linux 主机、Python 3.11 或更高版本，以及支持 C++20 的 `c++` 编译器。示例启动时会用这个编译器把包内的队列源码编译成临时共享库。普通 CPU 即可运行。

从仓库根目录安装并运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ./packages/decoder-runtime
python -m backline_decoder_runtime.demo
```

```text
request 0: 25 bytes, result=0
request 1: 25 bytes, result=1
PASS: fragmentation, queue, callback, and result collection
```

回调计算 25 个字节之和的奇偶性。两条请求只差一个字节，所以第一条返回 0，第二条返回 1。`PASS` 表示程序核对了回调收到的字节和按编号领取的结果。

<a id="接入-evodecode"></a>

| 接下来想做什么 | 从哪里开始 |
| --- | --- |
| 换成自己的 Python 回调 | [回调的输入、返回值和异常](packages/decoder-runtime/README.md#在-python-中接入应用) |
| 用 EvoDecode 回放已有帧或实时测量 | [EvoDecode 部署手册](https://github.com/qhub-cn/evo-decode/blob/main/docs/user/deployment.md) |
| 在本机运行 Steane 解码电路 | [硬件演示 1（CPU）](INSTALL.md#from-wheel)，使用 PennyLane 和 Catalyst |
| 复现论文中的往返延迟 | [读取归档样本](data/README.md#read-one-recorded-round-trip)或[采集新数据](benchmarks/README.md) |

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
