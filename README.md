# EvoBackline

`evobackline` 是本 Backline fork 为 [EvoDecode](https://github.com/qhub-cn/evo-decode)
长期维护的集成分支。这里维护数据传递所需的分片重组、任务队列和回调接口，
让 EvoDecode 可以把收到的数据交给自己的解码器，再返回结果。

本分支的主要交付物是独立 Python 包
[`backline-decoder-runtime`](packages/decoder-runtime/README.md)，当前版本为 **0.1.0**。
它不依赖 EvoDecode、Torch 或模型权重；官方 Backline 的核心实现仍由
PennyLane/Catalyst 提供。本仓库保留上游的硬件演示、构建配置和论文资料。

## 与 EvoDecode 的分工

| 工作 | 维护位置 |
| --- | --- |
| 原生请求分片重组、有界任务队列、结果收集 | 本仓库的 `packages/decoder-runtime/` |
| Python 回调注册、错误记录和退出清理 | 本仓库的 `packages/decoder-runtime/` |
| Controller/Coprocessor 配置及实际传输执行 | PennyLane/Catalyst；本仓库保留演示和构建配置 |
| 帧格式、输入转换、回放和实时数据生成 | EvoDecode |
| AQ2/Ising 模型构造、权重加载、CPU/GPU 推理 | EvoDecode |
| 实验配置、预测对比和结果报告 | EvoDecode |

共享包接收字节数据，调用应用提供的 Python 函数，当前回调要求返回 **0 或 1**。
它不解释数据对应哪种模型，也不决定模型如何分块推理。
旧的 EvoDecode 专用演示和模型适配器已经移除，本仓库不分发模型权重或本地实验结果。

## 先运行无权重示例

需要 **Linux、Python 3.11 或更新版本，以及支持 C++20 的 `c++` 编译器**。
以下命令从本仓库根目录执行；CPU 集成环境目前验证的是 Linux x86_64 / Python 3.12。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'setuptools>=77' wheel
python -m pip install --no-deps --no-build-isolation ./packages/decoder-runtime
python demos/demo_decoder_callback.py
```

预期输出：

```text
request 0: 25 bytes, result=0
request 1: 25 bytes, result=1
PASS: fragmentation, queue, callback, and result collection
```

[示例源码](demos/demo_decoder_callback.py)会在临时目录编译 C++ 库，
把两个请求分片提交到队列，再通过计算字节和的奇偶性检查回调结果。
运行结束后清理临时编译文件，不需要模型、GPU 或 PennyLane。

这个示例直接调用原生 C 接口，只验证分片、队列和回调。
它不经过 Catalyst QNode，也不能证明 RDMA、FPGA 或 GPU 推理已经可用。

## 接入 EvoDecode

先在本仓库根目录构建安装包：

```bash
python -m pip wheel --no-deps --no-build-isolation \
  ./packages/decoder-runtime --wheel-dir ./dist
```

然后在 EvoDecode 仓库根目录，将生成的 wheel 交给安装脚本：

```bash
python3.12 tools/install_backline_cpu.py \
  --runtime-wheel /path/to/backline/dist/backline_decoder_runtime-0.1.0-py3-none-any.whl
```

将 `/path/to/backline` 替换成实际路径。两个仓库不必放在相邻目录。
这一步安装 CPU 集成环境；GPU 推理还需按 EvoDecode 文档准备对应环境和权重。
实验入口、配置模板及模型使用方式请查看 EvoDecode 中的 `docs/backline.md`
和 `examples/backline/`，本仓库不再维护另一套模型运行入口。

当前 wheel 尚未发布到 PyPI 或 GitHub Release，需从源码构建。
wheel 包含 Python/C++ 源码；原生库在使用时编译到调用方指定的目录，
因此安装 wheel 后仍需要 C++20 编译器。

## 接口与使用限制

共享包公开 `NativeCallback`、`CALLBACK` 和 `build_coprocessor`：

- `build_coprocessor` 编译原生库到指定路径。
- `NativeCallback` 管理同进程 Python 回调，并可启用有界任务队列。
- `CALLBACK` 提供回调使用的 ctypes 函数类型。

完整可运行用法见[无权重示例](demos/demo_decoder_callback.py)，
安装、接口和版本说明见[共享包文档](packages/decoder-runtime/README.md)。
原生符号保留 `evodecode_*` 名称以兼容现有调用方；这不表示包依赖 EvoDecode。
回调执行超时的进程终止由调用方管理。共享包本身不提供远程部署或 GPU 调度。

## 仓库内容

| 路径 | 用途 |
| --- | --- |
| [`packages/decoder-runtime/`](packages/decoder-runtime/README.md) | 本分支维护的共享运行包及协议测试 |
| [`demos/demo_decoder_callback.py`](demos/demo_decoder_callback.py) | 不依赖模型的本地回调示例 |
| [`demos/`](demos/README.md) | 保留的上游 CPU、GPU、RDMA 和 FPGA 演示 |
| [`config/xbuild/`](config/xbuild/README.md) | 上游构建系统与目标机器配置 |
| [`config/machines.toml`](config/machines.toml) | 硬件演示使用的机器配置 |
| [`benchmarks/`](benchmarks/README.md) | 上游测量程序与使用说明 |
| `data/`、`assets/` | 上游实验数据及配图 |
| `scripts/` | 演示与测量辅助脚本 |

运行硬件演示时，按 [`INSTALL.md`](INSTALL.md) 准备对应的
PennyLane/Catalyst、网络和设备，再按[演示说明](demos/README.md)执行。
这些依赖与上面的独立回调示例不同。
上游论文中的延迟测量属于其指定硬件和实验条件，不作为本分支或 EvoDecode 模型的性能承诺。

## 开发与验证

在已准备好上述 Python 环境的仓库根目录执行：

```bash
python -m unittest discover -s packages/decoder-runtime/tests -v
python demos/demo_decoder_callback.py
make -C config/xbuild check
make -C config/xbuild test
```

共享包测试覆盖分片、请求编号、队列容量、回调错误、线程与清理。
构建系统测试检查构建规则；两者都不能替代实际硬件上的集成测试。

`evobackline` 长期保留。相关开发使用独立功能分支，经测试和代码审查后通过 PR
合入 `evobackline`。共享接口有变化时，在本仓库更新包版本，再由 EvoDecode 更新
固定依赖并运行集成测试；协议变化还需同步调整调用方。
参与开发前请阅读 [`AGENTS.md`](AGENTS.md) 中的构建注意事项。

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
