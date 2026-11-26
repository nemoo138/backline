# 往返延迟基准测试

[`bench.py`](bench.py) 测量从控制器发送综合征到收到纠正值的往返延迟（RTT）。要看已有结果，可以直接[读取论文归档的 CPU 回显样本](../data/README.md#read-one-recorded-round-trip)，在普通 CPU 主机上用 Python 标准库即可换算出微秒数。

<a id="running"></a>

## 采集一组新数据

先按[硬件安装指南](../INSTALL.md#choose-your-hardware)准备设备，激活虚拟环境，并跑通对应的[硬件演示](../demos/README.md)。下面测量 FPGA 控制器与服务器 GPU 上的 Steane 解码器，使用与硬件演示 4 相同的传输路径。从仓库根目录执行：

```bash
cd benchmarks
./bench.py --help-cells
./bench.py --ctrl hw-handshake-sw-loop --coproc gpu-steane -o rtt.csv
```

一次运行测量一种控制器与协处理器组合。上述命令在当前目录写出 `rtt.csv`，每行是一轮测量，终端另列延迟分位数。用 `./bench.py --help` 查看全部参数。若由 FPGA 自行逐轮发送，记录保存在板上，见下文。

<a id="the-matrix"></a>

## 选择控制器和协处理器

`--ctrl` 决定谁发送请求、检测响应，以及谁发起下一轮。

| `--ctrl` | 谁发送请求并检测响应 | 谁控制轮次 |
| --- | --- | --- |
| `hw-handshake-sw-loop` | FPGA 握手引擎 | 主机软件逐轮发起，硬件演示 4 和 5 使用此方式 |
| `hw-handshake-hw-loop` | FPGA 握手引擎 | FPGA 从表中读取数据，按设定节奏发送 |
| `sw-handshake` | CPU 通过 ibverbs 提交并轮询 | 主机软件逐轮发起 |

| `--coproc` | 运行设备 | 收到请求后做什么 |
| --- | --- | --- |
| `cpu-echo`、`gpu-echo` | CPU 或 GPU | 原样返回，作为通信往返的基线 |
| `cpu-steane`、`gpu-steane` | CPU 或 GPU | 调用预编译的 Steane 解码器 |
| `gpu-qldpc` | GPU | 调用 Triton 从校验矩阵编译的 qLDPC 解码器 |

使用 `gpu-qldpc` 时，在启动基准的机器上安装 Triton，通过 `--gpu-platform` 指定目标 GPU，格式为 `backend:arch:warp_size`，默认 `hip:gfx90a:64`。例如，在 `benchmarks/` 中运行 `./bench.py --coproc gpu-qldpc --gpu-platform hip:gfx942:64`。预编译内核的架构由部署包确定。

<a id="what-is-measured"></a>

## 计时范围与输出文件

控制器发送 8 字节综合征，协处理器返回 8 字节纠正值，两个方向的载荷各为 16 字节。RTT 用控制器一侧的时钟计算，覆盖发送、处理和收到响应。主机只为整次基准发起一次调用。基准用 `qp.runtime_call` 直接调用传输层的 C ABI，由 runtime 执行计时循环；硬件演示通过编译后的节点配置执行。

| 控制方式 | 记录位置 | 延迟字段 |
| --- | --- | --- |
| 主机逐轮发起 | `-o` 指定的 CSV；终端另打印统计摘要 | `rtt_cycles` 为周期数，`rtt_us` 为微秒 |
| FPGA 逐轮发送（`hw-handshake-hw-loop`） | 先写入 VPK120 的跟踪 RAM，再保存到 `--pacer-trace-out` 指定的板上文件。按终端打印的 `scp` 命令取回 | `cycles` 为周期数，`ns` 为纳秒 |

硬件循环用 `--iters` 设置总轮数。跟踪 RAM 最多记录 1,048,576 轮，超出时程序会拒绝运行。[归档文件与单位换算](../data/README.md#the-csvs)

<a id="choosing-the-pacer-cadence"></a>

## 设置 FPGA 的发送间隔

在 200 MHz 时钟下，每个周期为 5 ns，1 ms 等于 200,000 个周期。`--pacer-freq` 设定基本间隔（周期），`--pacer-span` 是掩码，`--pacer-seed` 是伪随机序列的种子。实际间隔按 `freq + (lfsr & span)` 计算。`span=0` 时取固定间隔；设置随机间隔时，掩码必须形如 `2^N - 1`，因此可选范围是离散的。

在 `benchmarks/` 中用 [pacer_span.py](pacer_span.py) 把期望的时间范围换算成硬件参数：

```bash
./pacer_span.py 3ms
./pacer_span.py 1ms 10ms
./pacer_span.py 200us 5ms --iters 10000
./pacer_span.py 1ms 10ms --all
```

给出一个时间时得到固定间隔。给出上下界时，下界由 `freq` 精确指定；工具列出最接近期望上界的两种掩码，并标出宽度误差较小的一项。例如，期望 1–10 ms 时：

```text
   N          span                actual range  width error
  --  ------------  --------------------------  -----------
  20  0x000FFFFF             1 ms ~ 6.243 ms    -41.7%
  21  0x001FFFFF             1 ms ~ 11.49 ms    +16.5%  <- closest
```

根据实验可接受的误差选择。若间隔上界超过主机 5 秒的领取超时，可能得到 `kErrStuck`。工具会提示宽度误差超过 25% 的情况；指定 `--iters` 时还会估算总时长。输出中的固件 ABI 键 `demo_freq`、`demo_span` 由 [placement.py](placement.py) 写入配置，对应命令行的 `--pacer-freq`、`--pacer-span`。

<a id="sweeping"></a>

## 测量多种组合

从仓库根目录运行 [sweep-bench.sh](../scripts/sweep-bench.sh)。第一条只列出将执行的命令，第二条实际测量，主机逐轮发起的测量结果写入 `results/`，FPGA 硬件循环的记录按终端提示从板上取回。第三条示范如何为每组指定轮数。

```bash
./scripts/sweep-bench.sh -n
./scripts/sweep-bench.sh -o results
./scripts/sweep-bench.sh -- --iters 100000
```

<a id="prerequisites"></a><a id="wrx90-kernel-boot-parameters"></a>

## 复现论文延迟时的 WRX90 配置

参考协处理器服务器使用 AMD WRX90、NPS4、32 个物理核心、64 个逻辑 CPU 和 4 个 NUMA 域。MI210 与 ConnectX-7 同在节点 0。运行时，[machines.toml](../config/machines.toml) 使用 `numactl` 将执行器及其内存分配到该节点，绑定轮询线程，并请求实时调度。先在待测机器核对拓扑：

```bash
lscpu -e=CPU,CORE,NODE,ONLINE
numactl -H
```

参考机的节点 0 为 `0-7,32-39`，节点 1 为 `16-23,48-55`，节点 2 为 `24-31,56-63`，节点 3 为 `8-15,40-47`。处理器拓扑、NPS 或 SMT 设置有变化时，应按实机重新确定待隔离核心及其同核线程。

参考测量在 `/etc/default/grub` 的 `GRUB_CMDLINE_LINUX` 原有设置中加入下列参数。这里的 CPU 编号仅对应上述参考机：

```bash
GRUB_CMDLINE_LINUX="quiet splash pci=realloc=off iommu=pt isolcpus=0-7,32-39 nohz_full=0-7,32-39 rcu_nocbs=0-7,32-39 irqaffinity=8-31,40-63 processor.max_cstate=1 tsc=reliable"
```

| 参数 | 作用 |
| --- | --- |
| `pci=realloc=off`、`iommu=pt` | 保留 MI210 和网卡的固件 PCIe BAR 布局，使用 IOMMU 直通以支持 GPUDirect 和对等 DMA |
| `isolcpus`、`nohz_full`、`rcu_nocbs` | 隔离轮询核心及其同核线程，减少定时中断，将 RCU 回调移至其他核心 |
| `irqaffinity` | 把普通中断分配给其余核心 |
| `processor.max_cstate=1`、`tsc=reliable` | 限制深度空闲状态，使用可靠的 TSC 时钟 |

在要复现此配置的服务器上，确认参数后更新 GRUB 并重启：

```bash
sudo update-grub
sudo reboot
```

重启后用 `cat /proc/cmdline`、`lscpu` 和 `numactl -H` 核对实际生效的参数和拓扑。
