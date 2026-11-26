# 运行硬件演示与批量测量

从仓库根目录执行下列命令。采集新数据前，先按[硬件安装指南](../INSTALL.md)准备相应设备。

## 批量测量往返延迟

[sweep-bench.sh](sweep-bench.sh) 按控制器和协处理器的组合逐一调用 [bench.py](../benchmarks/bench.py)。先预览选中的组合，再开始测量。

```bash
./scripts/sweep-bench.sh -n
./scripts/sweep-bench.sh -o results
```

`-n` 只打印组合和目标路径。实际运行时，主机逐轮发起的测量将 CSV 写入 `results/`，FPGA 硬件循环的记录需按终端提示从板上取回。用 `-h` 查看选项。要统一设置轮数，把基准参数放在 `--` 后面，例如 `./scripts/sweep-bench.sh -- --iters 100000`。

## 更新硬件演示的参考日志

[run-demo.sh](run-demo.sh) 会先清空该演示的参考日志目录，再运行演示并保存输出。需要更新[参考日志](../demos/expected_logs/README.md)时执行：

```bash
./scripts/run-demo.sh demo_1_local_cpu_to_local_cpu_memcpy.py
```
