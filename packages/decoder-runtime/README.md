# backline-decoder-runtime

Backline fork 维护的独立 Python 包，版本 **0.1.0**。负责 C++ 分片重组、有界任务队列、
Python 回调生命周期及原生库编译。包本身仅依赖 Python 标准库；编译运行需要 Linux
和 C++20 编译器。它不是官方 PennyLane/Catalyst 的替代品，也不依赖 EvoDecode。

## 两个仓库如何使用

- Backline 的无权重回调示例从本包导入 `NativeCallback` 和 `build_coprocessor`。
- EvoDecode 固定依赖 `backline-decoder-runtime==0.1.0`，负责数据、解码与实验管理。
- `src/backline_decoder_runtime/coprocessor.cpp` 是共享队列的唯一源码位置。

```python
from pathlib import Path
from backline_decoder_runtime import NativeCallback, build_coprocessor

library = build_coprocessor(Path("run/libdecoder.so"))
```

`NativeCallback` 接口与原演示一致，供同进程 C ABI 回调使用；外层进程管理者负责
超时终止。原生库在调用者的运行目录编译，不写入安装目录。wire ABI 仍使用
`evodecode_*` 符号，保持现有 Controller 兼容。

## 职责边界

本包只管理传输请求的分片、队列、回调执行和清理。调用者提供接收 bytes 并返回
二进制结果的函数；本包不加载 checkpoint，不构造 AQ2/Ising 模型，不生成纠错数据。
EvoDecode 管理权重、模型推理、数据转换及实验报告，Backline 不再另存其模型包。
旧 demo 1b、模型专用适配器及运行记录已移除；模型文件集中保存在 EvoDecode。
本包与测试无需这些历史文件。
官方硬件示例继续保留。`evodecode_*` C 符号是已有 ABI 名称，不表示反向依赖
EvoDecode，也不在本次整理中重命名。

无模型示例：`python demos/demo_decoder_callback.py`（从仓库根目录运行）。

## 构建与安装

在包含 setuptools>=77 和 wheel 的环境中，从 Backline 仓库根目录执行：

```bash
python -m pip wheel --no-deps --no-build-isolation \
  ./packages/decoder-runtime --wheel-dir ./dist
python -m pip install ./dist/backline_decoder_runtime-0.1.0-py3-none-any.whl
python -m unittest discover -s packages/decoder-runtime/tests -v
```

然后在 EvoDecode 仓库根目录执行：

```bash
python3.12 tools/install_backline_cpu.py \
  --runtime-wheel ../backline/dist/backline_decoder_runtime-0.1.0-py3-none-any.whl
```

两个仓库不必放在相邻目录；将参数替换为实际 wheel 路径即可。
此 wheel 包含跨架构可读的 Python/C++ 源码，实际运行仍限定 Linux；CPU 集成环境
目前只验证 Linux x86_64 / Python 3.12。

## 日常开发

开发者可在两项目共用的开发环境中执行：

```bash
python -m pip install --no-deps --no-build-isolation -e ./packages/decoder-runtime
```

源码修改即可被新的 Python 进程使用；已编译原生库在下一次运行时重新生成。
不要把开发环境的 editable 路径作为用户安装依赖。

## 版本与发布

本次只准备本地 0.1.0 wheel，尚未上传到 PyPI 或 GitHub Release。
发布时在你自己的 Backline fork 中审核、提交、测试，再按 Git 规范创建语义化版本
附注 tag，并把 wheel 和 SHA256 上传到对应 Release。不要使用官方项目的发布地址
冒充自己的包，也不要覆盖已经发布的同版本文件。

共享代码有修改时，更新本仓库包版本并测试；EvoDecode 更新 optional dependency、
CPU 清单及安装脚本中的期望版本，安装新的 wheel 后运行集成测试。涉及协议变化时
需要同时更新调用方，不能只改版本号。

测试：`tests/test_protocol.py` 和从演示迁入的 `tests/test_adapter.py` 共 15 项，
验证分片、ABI、队列容量、shot ID、回调错误、线程与清理。EvoDecode 保留自己的集成测试。
源码继承 Apache-2.0 许可；见 LICENSE 和包内 NOTICE。

## 本次验证（2026-09-28）

0.1.0 wheel 已构建并供两个项目安装。包协议测试 3 项、Backline 原演示适配测试
12 项、EvoDecode CPU 集成测试 26 项通过。错误版本 wheel 会在创建环境前被
EvoDecode 安装脚本拒绝。wheel 尚未上传；正式发布应从干净源码构建，保留 SHA256。

Backline 构建检查：`make check` 通过；补齐系统 rsync 后，`make test` 为 169 通过、0 失败、2 跳过（非 macOS 无法测 Mach-O；本机有 clang，无法模拟缺失工具链）。两个独立安装包在仓库外完成 32-shot CPU 示例，pip check 通过。
