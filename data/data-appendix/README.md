# 论文附录的往返延迟数据

附录使用 10 份 `hw-for-loop.<responder>.<cadence>.csv`。FPGA 握手引擎控制每一轮的发送与接收，对 `cpu-echo`、`gpu-echo`、`cpu-steane`、`gpu-steane` 和 `gpu-qldpc` 分别测量两种发送节奏。

<a id="pacing-cadences"></a>

## 两种发送节奏

| 文件名中的节奏 | `--pacer-freq` | `--pacer-span` | 发送间隔 | 每份记录的轮数 |
| --- | ---: | ---: | --- | ---: |
| `b2b` | `0` | — | 收到上一次响应后立即发送，间隔取决于往返延迟 | 1,000,000 |
| `random-delayed` | `1000000` | `0xFFFFFFF` | 5 ms 至 1.347 s，平均约 676 ms | 10,000 |

CSV 按完成顺序记录每一轮的往返周期数（`cycles`）和纳秒数（`ns`）。绘图脚本将纳秒除以 1,000，图中以微秒显示。

<a id="drawing-the-figures"></a>

## 绘制这 10 组数据

在仓库的 `data/` 目录运行 `make appendix`。PNG 保存在 `data/data-appendix/figures/`。

<a id="reproducing-the-dataset"></a>

## 重新测量

按[基准测试指南](../../benchmarks/README.md#running)准备硬件，在 `benchmarks/` 目录设置板卡地址和协处理器。下面以 CPU 回显为例，请将示例地址换成自己的板卡地址。

```bash
BOARD=petalinux@192.168.3.15
C=cpu-echo
```

每次运行都在板上写入 `/tmp/t.csv`。在下一次测量前，用 `scp` 把它复制到当前目录，并在文件名中保留协处理器和发送节奏。更换 `C` 后重复这两次测量，即可得到其余记录。

```bash
./bench.py --ctrl hw-handshake-hw-loop --coproc "$C" --iters 1000000 \
  --pacer-freq 0 \
  --pacer-trace-out /tmp/t.csv
scp "$BOARD":/tmp/t.csv "hw-for-loop.$C.b2b.csv"

./bench.py --ctrl hw-handshake-hw-loop --coproc "$C" --iters 10000 \
  --pacer-freq 1000000 \
  --pacer-span 0xFFFFFFF \
  --pacer-trace-out /tmp/t.csv
scp "$BOARD":/tmp/t.csv "hw-for-loop.$C.random-delayed.csv"
```
