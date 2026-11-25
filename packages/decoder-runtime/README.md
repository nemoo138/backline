# backline-decoder-runtime 用户指南

这个 Python 包接收字节请求，重组分片并通过本地队列调用应用提供的函数。回调接收 `bytes`，返回 0 或 1。下面的例子提交两个 25 字节请求，计算字节和的奇偶性。

<a id="构建与安装"></a>

## 运行第一个回调

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

[示例源码](../../demos/demo_decoder_callback.py)会在临时目录编译 C++ 库，
把两个请求分片提交到队列，再通过计算字节和的奇偶性检查回调结果。
运行结束后清理临时编译文件，不需要模型、GPU 或 PennyLane。

这个示例直接调用原生 C 接口，只验证分片、队列和回调。
它不经过 Catalyst QNode，也不能证明 RDMA、FPGA 或 GPU 推理已经可用。

## 在 Python 中接入应用

`build_coprocessor(path)` 编译原生库；`CALLBACK` 描述 ctypes 回调签名；`NativeCallback` 管理当前进程中的函数绑定、结果和错误。应用负责进程超时及模型资源的释放。安装 wheel 后首次使用仍需要 Linux 和 C++20 编译器。

```python
from pathlib import Path
from backline_decoder_runtime import build_coprocessor

library = build_coprocessor(Path("run/libdecoder.so"))
print(library)
```

<a id="两个仓库如何使用"></a><a id="职责边界"></a>

## 在 EvoDecode 中部署

先在使用的 EvoDecode 版本中查看 `pyproject.toml` 的 `backline` 依赖，再取得相同版本的 runtime wheel，交给该版本的 `tools/install_backline_cpu.py --runtime-wheel <wheel 路径>`。模型权重、帧和 `Deployment` 参数由 EvoDecode 用户手册说明。上游 RDMA 与 FPGA 演示另有安装步骤。

[EvoDecode 项目与用户文档](https://github.com/qhub-cn/evo-decode) · [源码构建与验收](../../docs/developer.md) · [硬件演示安装](../../INSTALL.md)

<a id="日常开发"></a><a id="版本与发布"></a><a id="本次验证2026-09-28"></a>

[开发和历史验证记录](../../docs/developer.md)
