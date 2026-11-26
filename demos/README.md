# 硬件演示

先按[硬件安装指南](../INSTALL.md#choose-your-hardware)准备环境并激活虚拟环境。**硬件演示 1（CPU）** 在本机运行 Steane 电路，适合检查 PennyLane、Catalyst、传输和解码器能否一起工作。要验证 Python 函数能否收到完整的字节请求，请运行共享包的[本地回调示例](../README.md#本地回调示例)。

| 演示 | 控制器 → 协处理器 | 通信 | 解码器 |
| --- | --- | --- | --- |
| [1](demo_1_local_cpu_to_local_cpu_memcpy.py) | 本机 CPU → 本机 CPU | 同一进程内存复制 | 预编译 Steane |
| [1a](demo_1a_local_cpu_to_local_cpu_rdma.py) | 本机 CPU → 本机 CPU | 同一进程 RDMA | 预编译 Steane |
| [2](demo_2_remote_cpu_to_remote_gpu_triton.py)、[2a](demo_2a_remote_cpu_to_remote_gpu_triton_runtime_calls.py) | 服务器 CPU → 服务器 GPU | 经同一台服务器的 RDMA 网卡 | Triton 编译的 qLDPC |
| [3](demo_3_remote_cpu_to_remote_gpu.py) | 服务器 CPU → 服务器 GPU | 经同一台服务器的 RDMA 网卡 | 预编译 Steane |
| [4](demo_4_remote_fpga_to_remote_gpu.py) | 远程 FPGA → 服务器 GPU | 跨主机 RDMA | 预编译 Steane |
| [5](demo_5_remote_fpga_to_remote_gpu_triton.py) | 远程 FPGA → 服务器 GPU | 跨主机 RDMA | Triton 编译的 Steane |

<a id="queue-and-callback-example-for-evodecode"></a>
<a id="running-demos"></a>
<a id="tier-1--demo-1"></a>

## 硬件演示 1（CPU）

以下命令从仓库根目录执行。后续演示命令均在 `demos/` 目录运行。

```bash
cd demos
./demo_1_local_cpu_to_local_cpu_memcpy.py
```

每次采样都经过多轮 Steane 测量、解码和纠正，每次解码都要往返协处理器一次。控制器使用 `null.qubit`，因此预期输出为 10 行三位的零。看到下列输出且程序正常结束，说明这次电路、传输和解码器调用均已完成。

```text
samples: [[0 0 0]
 [0 0 0]
 ...
 [0 0 0]]
```

<a id="tier-2--demo-1a"></a>

## 在本机验证 RDMA（演示 1a）

```bash
./demo_1a_local_cpu_to_local_cpu_rdma.py
```

预期仍是 10 行零。演示 1a 的请求和响应经本机 RDMA 设备往返。设备由 `machines.toml` 的 `[local]` 指定，例如 `config = "dev=rxe0;gid=1"`。用 `ibv_devinfo` 和 `/sys/class/infiniband/<dev>/ports/1/gids/` 查找当前设备的 IPv4 RoCE v2 条目，再填写它的 GID 索引。

<a id="tier-3--gpu-demos"></a>

## 在服务器 GPU 上解码（演示 2、2a、3）

先运行演示 3。它使用预编译的 Steane 解码器，可以先验证远程传输，预期输出仍为 10 行零。

```bash
./demo_3_remote_cpu_to_remote_gpu.py
./demo_2_remote_cpu_to_remote_gpu_triton.py
./demo_2a_remote_cpu_to_remote_gpu_triton_runtime_calls.py
```

演示 2 依次对每个数据量子比特施加 I、X、Y、Z，每种错误输出两个稳定子均值。全部正确纠正时，四行均为 1：

```text
I (Array(1., dtype=float64), Array(1., dtype=float64))
X (Array(1., dtype=float64), Array(1., dtype=float64))
Y (Array(1., dtype=float64), Array(1., dtype=float64))
Z (Array(1., dtype=float64), Array(1., dtype=float64))
```

演示 2a 执行相同计算，把 `qp.backline.decode` 展开成 `get_session`、`stage_payload`、`post`、`collect` 四个调用。可用同样的四行输出核对结果。

演示 2、2a 和 5 在构建机上用 Triton 编译解码器。按目标 GPU 填写 `platform`（后端、架构、warp 大小），例如 MI210 使用 `hip:gfx90a:64`，NVIDIA 的一个示例为 `cuda:80:32`。构建机需安装 Triton 和对应的 `hipcc` 或 `nvcc`。

<a id="tier-4--fpga-demos"></a>

## 从 FPGA 向 GPU 提交请求（演示 4、5）

```bash
./demo_4_remote_fpga_to_remote_gpu.py
./demo_5_remote_fpga_to_remote_gpu_triton.py
```

VPK120 上的控制器在硬件中发送请求并检测响应，服务器 GPU 解码，主机 CPU 不参与这段往返。两个演示均输出 10 行零。

<a id="pointing-it-at-your-own-machines"></a>

## 配置机器和文件路径

本仓库记录的 RDMA/GPU 演示使用 AMD MI210、ConnectX-7 网卡及 VPK120 开发板。换用自己的机器时，编辑 [machines.toml](../config/machines.toml) 中的主机、端口、设备和部署路径。`demos/placement.py` 和 `benchmarks/placement.py` 都读取这份配置。

| 演示 | 本地构建机 | 远程服务器（`[server]`） | 开发板（`[vpk]`） |
| --- | --- | --- | --- |
| 1、1a | 编译、启动，同时运行控制器和协处理器（`[local]`） | — | — |
| 2、2a、3 | 编译、分发并启动 | 控制器和协处理器各占一个进程 | — |
| 4、5 | 编译、分发并启动 | 运行协处理器 | 运行控制器 |

每次运行都读取 `[paths]`。默认值与本机目录不符时，用下列环境变量覆盖，可在当前 shell 或 shell 配置中设置。

| 环境变量 | 演示 | 指向的目录 |
| --- | --- | --- |
| `CATALYST_ROOT` | 1、1a | Catalyst 源码树，Steane 解码器从 `$CATALYST_ROOT/runtime/build/lib` 加载 |
| `BACKLINE_BUNDLES` | 2 至 5，含 2a | 部署包目录，每个包名对应一个子目录。相对路径从仓库根目录解析 |

<a id="reference-logs"></a>

## 核对运行结果

[参考日志](expected_logs/README.md)记录了各演示的启动输出、执行器日志和对应提交。要用一次新的运行替换演示 1 的参考日志，在仓库根目录执行：

```bash
./scripts/run-demo.sh demo_1_local_cpu_to_local_cpu_memcpy.py
```

<a id="words-used-throughout"></a>

## 术语

| 名称 | 在硬件演示中的含义 |
| --- | --- |
| 控制器（controller） | 运行电路、发送解码请求 |
| 协处理器（coprocessor） | 运行解码器、返回响应 |
| 综合征（syndrome）与纠正值（correction） | 控制器发送 8 字节综合征，解码器返回 8 字节纠正值 |
| 通信网络（fabric） | 控制器与协处理器间的 RDMA 网络，与登录主机使用的网络分开 |
| 机器（machine）与节点（node） | 机器是配置中的主机或开发板，节点是分配到机器上的控制器或协处理器角色 |
| 执行器（executor） | Backline 在远程机器上启动的进程，用来运行节点工作流 |

需要测量一次往返耗时多久时，使用[基准测试](../benchmarks/README.md)。
