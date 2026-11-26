# 论文正文的往返延迟数据

正文使用 5 份 `sw-for-loop.<responder>.csv`。主机软件发起每一轮，FPGA 握手引擎发送请求并检测响应。文件名中的 `<responder>` 表示协处理器上运行的程序：`cpu-echo`、`gpu-echo`、`cpu-steane`、`gpu-steane` 或 `gpu-qldpc`。

每行记录一轮的编号（`sample`）、往返周期数（`rtt_cycles`）和微秒数（`rtt_us`）。文件开头的注释给出时钟频率和测量配置。

<a id="drawing-the-figures"></a>

## 绘制这 5 组数据

在仓库的 `data/` 目录运行 `make main-text`。每份 CSV 对应一张 PNG，保存在 `data/data-main-text/figures/`。

<a id="reproducing-the-dataset"></a>

## 重新测量

按[基准测试指南](../../benchmarks/README.md#running)准备硬件后，在 `benchmarks/` 目录运行。每种配置测量 1,000,000 轮，CSV 写入当前目录。

```bash
for C in cpu-echo gpu-echo cpu-steane gpu-steane gpu-qldpc; do
  ./bench.py --ctrl hw-handshake-sw-loop \
    --coproc "$C" --iters 1000000 \
    -o "sw-for-loop.$C.csv"
done
```
