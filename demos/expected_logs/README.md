# 硬件演示的参考日志

每个子目录对应一个演示。`driver.log` 保存运行时的终端输出；`provenance.txt` 记录运行命令，以及当时能在本机找到的 Backline、Catalyst 和 PennyLane 仓库版本。

核对自己的运行结果时，先看同一组节点是否依次启动并报告预期事件，再看程序是否正常结束并给出样本输出。主机名、路径和耗时随机器变化。使用模拟器采样时，单次测量结果也可能不同。

要更新某个演示的参考日志，在仓库根目录运行以下命令。脚本会先清空该演示对应的日志目录。

```bash
./scripts/run-demo.sh demo_1_local_cpu_to_local_cpu_memcpy.py
```
