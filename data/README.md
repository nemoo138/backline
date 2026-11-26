# 测量数据说明

<a id="data"></a>

本目录保存论文图表使用的往返延迟（RTT）测量数据、绘图脚本，以及生成论文发表版本图表的 notebook。

| 文件或目录 | 内容 |
| --- | --- |
| `<YYYYMMDD>/` | 一次批量测量的样本，每组控制器与协处理器配置对应一个 CSV 文件 |
| `<YYYYMMDD>/figures/` | `make` 为每个 CSV 生成的 PNG 图 |
| [data-main-text/](data-main-text/) | 论文正文使用的 `sw-for-loop` 往返延迟记录 |
| [data-appendix/](data-appendix/) | 论文附录使用的 `hw-for-loop` 往返延迟记录 |
| [Makefile](Makefile) | 生成缺失的图，或在数据和绘图脚本更新后重新绘图 |
| [plot_latency.py](plot_latency.py) | 绘制延迟随时间的变化，以及同一批样本的延迟直方图 |
| [LatencyPlots.ipynb](LatencyPlots.ipynb) | 按实验配置查看往返延迟分布 |

<a id="read-one-recorded-round-trip"></a>

## 读懂一条往返延迟记录

从仓库根目录运行下面的 Python 代码，即可用标准库读取已归档的 CPU 回显实验首条样本。

```python
import csv
from pathlib import Path

trace = Path("data/data-main-text/sw-for-loop.cpu-echo.csv")
with trace.open(encoding="utf-8") as stream:
    clock = next(stream).strip()
    source = next(stream).strip()
    first = next(csv.DictReader(stream))
print(clock, source, sep="\n")
print(first["sample"], first["rtt_cycles"], first["rtt_us"])
```

```text
# clk_mhz=200.0
# source=ctrl=hw-handshake-sw-loop coproc=cpu-echo
0 928 4.6400
```

前两行记录时钟频率和实验配置。在这次实验中，主机逐轮发起通信，控制器硬件发送请求并检测响应，协处理器在 CPU 上执行回显。最后一行的 `0` 是样本编号，`928` 是该次往返经过的时钟周期数。200 MHz 表示每微秒 200 个周期，因此本次往返耗时为 **928 ÷ 200 = 4.64 微秒**。要分析该配置的延迟分布，应读取整份文件。

<a id="drawing-the-figures"></a>

## 生成图表

```bash
cd data
make                     # 生成缺失的图，或在 CSV、绘图脚本变动后重新绘图
make main-text           # 绘制 data-main-text/ 中的数据
make appendix            # 绘制 data-appendix/ 中的数据
make list                # 列出将绘制的图及使用的脚本
make clean               # 删除各个 figures/ 目录
make FLAGS='--logy'      # 本次绘图使用对数纵轴
```

每张图都依赖对应的 CSV 和绘图脚本。任一文件更新后，`make` 都会重新生成该图。若数据集目录内自带 `plot_latency.py`，则优先使用该版本，以便在共享绘图脚本更新后仍能复现归档结果。

<a id="the-csvs"></a>

## CSV 文件格式

[bench.py](../benchmarks/bench.py) 为每组配置写出一个 `rtt_<coproc>_<ctrl>.csv`。文件开头的两行注释记录时钟频率、控制器模式和协处理器类型，后续每行对应一个样本。

| 字段 | 含义 |
| --- | --- |
| `sample` | 样本编号 |
| `rtt_cycles` | 单次往返耗费的时钟周期数 |
| `rtt_us` | 同一次往返的耗时，单位为微秒 |

[sweep-bench.sh](../scripts/sweep-bench.sh) 可一次运行整组配置，将结果写入同一目录。绘图用的 Makefile 按 `YYYYMMDD` 匹配日期目录。归档时，将带时刻的测量目录（例如 `sweep-20260819-174612`）整理为 `20260819`，并在数据说明中保留测量时刻。

<a id="rtt-datasets"></a>

## 论文使用的往返延迟数据集

正文的 `data-main-text/` 包含 5 份 `sw-for-loop` 记录，由主机软件逐轮驱动。附录的 `data-appendix/` 包含 10 份 `hw-for-loop` 记录，由硬件驱动循环，分为连续发送（`b2b`）和随机延迟发送（`random-delayed`）两种节奏。两个目录各自的 README 说明文件命名、发送间隔参数、绘图命令和复现步骤。
