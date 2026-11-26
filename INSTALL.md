# 硬件安装指南

<a id="installation"></a>

仅运行本地 Python 回调时，按[runtime 用户指南](packages/decoder-runtime/README.md)安装即可。要复现上游硬件演示，先按下表准备环境，再按[演示指南](demos/README.md)运行相应示例。

<a id="choose-your-hardware"></a>

## 按硬件选择安装步骤

如果只有一台 Linux CPU 主机，从[使用预编译 wheel 运行演示 1](#from-wheel)开始。更高档位需要在上一档环境的基础上增加相应设备和工具。

| 安装档位 | 通信路径 | 所需环境 | 演示 |
| --- | --- | --- | --- |
| [1](#tier-1--demo-1) | 单机 CPU 与 CPU，通过内存复制通信 | Linux CPU 主机、PennyLane 和 Catalyst | [1](demos/demo_1_local_cpu_to_local_cpu_memcpy.py) |
| [2](#tier-2--demo-1a) | 单机 CPU 与 CPU，通过 RDMA 通信 | 增加支持 `libibverbs` 的设备。可用 Soft-RoCE，也可用 RDMA 网卡 | [1a](demos/demo_1a_local_cpu_to_local_cpu_rdma.py) |
| [3](#tier-3--gpu-demos-2-2a-3) | 远程服务器上的 CPU 与 GPU | 增加一台可通过 SSH 访问的服务器，配备 GPU 和 RDMA 网卡 | [2](demos/demo_2_remote_cpu_to_remote_gpu_triton.py)、[2a](demos/demo_2a_remote_cpu_to_remote_gpu_triton_runtime_calls.py)、[3](demos/demo_3_remote_cpu_to_remote_gpu.py) |
| [4](#tier-4--fpga-demos-4-5) | 远程 FPGA 与服务器的 CPU 或 GPU | 增加一块通过 RDMA 网络连接服务器的 [Xilinx VPK120 开发板](https://www.amd.com/en/products/adaptive-socs-and-fpgas/evaluation-boards/vpk120.html) | [4](demos/demo_4_remote_fpga_to_remote_gpu.py)、[5](demos/demo_5_remote_fpga_to_remote_gpu_triton.py)、[基准测试](benchmarks/README.md) |

<a id="requirements"></a>

## 系统与工具要求

| 系统、工具或设备 | 适用档位 | 用途或配置条件 |
| --- | --- | --- |
| Debian 或 Ubuntu | 全部 | 其他发行版可安装对应的软件包 |
| `clang`、`lld`、`g++` | 全部 | Catalyst 前端使用 `g++` 编译 |
| `python3-venv`、`python3-dev` | 全部 | Python 虚拟环境和开发文件 |
| `libibverbs-dev` | 2 起 | Fedora 对应 `rdma-core-devel`，Arch 对应 `rdma-core` |
| verbs 设备 | 2 起 | `ibv_devices` 应至少列出一个设备，可以是 Soft-RoCE |
| `wget`、`gnupg`、`rsync` | 3 起 | 添加 ROCm 软件源、复制服务器的系统头文件和库（sysroot） |
| ROCm 6 或更新版本 | 3 起 | 可从 AMD 的 apt 软件源安装。使用 NVIDIA GPU 时还需要 CUDA 12.8 或更新版本 |
| 带 GPU 的第二台主机 | 3 起 | 通过 SSH 连接。复现参考延迟时需要 `NOPASSWD` sudo，以绑定线程并设置实时调度优先级 |
| VPK120 开发板 | 4 | 与服务器接入同一 RDMA 网络 |

编译 GPU 后端的主机需要 ROCm 工具链，运行后端的主机需要 GPU。从演示 2 开始，本地构建机负责编译和启动演示，远程服务器负责执行。

<a id="quickstart"></a>

## 快速安装

下面给出从源码构建 Catalyst 的完整流程。将 `SERVER` 和 `BOARD` 分别换为自己的服务器和 VPK120 开发板地址，按所选档位执行相应步骤。只运行演示 1 时，可以直接安装 PennyLane、Lightning 和 Catalyst 的[预编译 wheel](#from-wheel)。

```bash
# 请替换为自己的地址，下面使用参考硬件的地址
SERVER=you@192.168.3.14
BOARD=petalinux@192.168.3.15
export CATALYST_ROOT=~/catalyst

# 1. 安装系统软件包
sudo apt update && sudo apt install -y \
    clang lld g++ ccache make cmake ninja-build git \
    python3 python3-venv python3-dev python3-pip \
    libibverbs-dev ibverbs-providers ibverbs-utils rdma-core \
    ca-certificates curl wget gnupg zstd binutils rsync numactl openssh-client

# 2. 第 3 档及以上需要 ROCm
sudo mkdir -p --mode=0755 /etc/apt/keyrings
wget -qO- https://repo.radeon.com/rocm/rocm.gpg.key \
    | sudo gpg --dearmor -o /etc/apt/keyrings/rocm.gpg
# Debian / Ubuntu 软件源；noble 对应 Ubuntu 24.04，其他发行版见第 3 档。
echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/latest noble main' \
    | sudo tee /etc/apt/sources.list.d/rocm.list
printf 'Package: *\nPin: origin repo.radeon.com\nPin-Priority: 900\n' \
    | sudo tee /etc/apt/preferences.d/rocm-pin-900
sudo apt update && sudo apt install -y hip-dev rocm-device-libs
export PATH=/opt/rocm/bin:$PATH

# 3. 安装 Catalyst 和 PennyLane
# 这里从源码构建。只运行演示 1 时也可以用预编译 wheel，见下文。
git clone --branch v0.16.0b1 --recurse-submodules --shallow-submodules \
    https://github.com/PennyLaneAI/catalyst.git "$CATALYST_ROOT"
cd "$CATALYST_ROOT"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ENABLE_TRANSPORT=ON ENABLE_EXECUTOR=ON LLVM_TARGETS_TO_BUILD="host;AArch64;X86"
make all

# 4. 为 Python 解码器安装 Triton。上一步已随 Catalyst 安装 PennyLane。
pip install triton

# 5. 获取 Backline 源码
git clone --branch v0.1.0b1 https://github.com/PennyLaneAI/backline.git ~/backline

# 6. 第 3 档及以上需要为远程设备构建部署包
cd ~/backline/config/xbuild
# sysroot 复制目标机的头文件和库，build 为目标机交叉编译组件。
# bundle 收集并检查产物，同时生成部署脚本。
make sysroot TARGET=threadripper SYSROOT_PROVIDER_ARGS="host=$SERVER port=22"
make build TARGET=threadripper CATALYST="$CATALYST_ROOT" \
    COMPONENT="executor rt-transport rt-capi rtd-null-qubit cpu-verbs-controller \
               cpu-verbs-coprocessor steane-coprocessor-cpu echo-coprocessor-cpu gpu-coprocessor"
make bundle TARGET=threadripper BUNDLE=threadripper-bundle CATALYST="$CATALYST_ROOT"

make sysroot TARGET=vpk120                                    # 仅第 4 档需要
make build TARGET=vpk120 CATALYST="$CATALYST_ROOT" \
    COMPONENT="executor rt-capi rtd-null-qubit hwhs-capi-backend \
               hwhs-controller-session swhs-capi-backend rt-transport"
make bundle TARGET=vpk120 BUNDLE=vpk-bundle CATALYST="$CATALYST_ROOT"

# 7. 将部署包放到演示程序读取的目录
mkdir -p ~/bundles
cp -R build/threadripper/bundles/threadripper-bundle ~/bundles/
cp -R build/vpk120/bundles/vpk-bundle               ~/bundles/   # 仅第 4 档需要
export BACKLINE_BUNDLES=~/bundles
```

安装后按[演示指南](demos/README.md)运行对应示例。交叉编译的目标、组件、部署包（bundle）以及添加新机器的方法见[构建系统说明](config/xbuild/README.md)。

<a id="tier-1--demo-1"></a>

## 第 1 档：单机 CPU 演示 1

<a id="system-packages"></a>

### 系统软件包

```bash
sudo apt install clang lld g++ ccache make git python3-venv python3-dev
```

`cmake` 和 `ninja` 随 Catalyst 的依赖清单安装。

<a id="catalyst"></a>

### 安装 Catalyst

演示 1 支持[预编译 wheel](#from-wheel)和[源码构建](#from-source)。演示 1a、2、2a、3、4、5 均需从源码构建 Catalyst。

<a id="from-wheel"></a>

#### 使用预编译 wheel

```bash
pip install pennylane-catalyst==0.16.0b1 \
  -f https://github.com/PennyLaneAI/pennylane/releases/expanded_assets/v0.46.0b1 \
  -f https://github.com/PennyLaneAI/pennylane-lightning/releases/expanded_assets/v0.46.0b1 \
  -f https://github.com/PennyLaneAI/catalyst/releases/expanded_assets/v0.16.0b1
```

<a id="from-source"></a>

#### 从源码构建

```bash
export CATALYST_ROOT=~/catalyst          # 换成自己的路径

git clone --branch v0.16.0b1 --recurse-submodules --shallow-submodules \
    https://github.com/PennyLaneAI/catalyst.git "$CATALYST_ROOT"
```

将 `CATALYST_ROOT` 写入 shell 的启动配置。演示程序用它定位 Catalyst 编译出的解码器库。如果未设置，会读取[机器配置](config/machines.toml)中的 `catalyst` 路径。

按照 [Catalyst 源码安装说明](https://docs.pennylane.ai/projects/catalyst/en/stable/dev/installation.html)构建，并启用 Backline 使用的选项。

```bash
cd "$CATALYST_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ENABLE_TRANSPORT=ON ENABLE_EXECUTOR=ON LLVM_TARGETS_TO_BUILD="host;AArch64;X86"
make all
```

演示 1 只需启用传输。其余两个选项从演示 2 开始使用。如果后续要运行远程演示，可以在首次构建时一并设置，避免之后重新编译 LLVM。

| 构建选项 | 从哪个演示开始需要 | 作用 |
| --- | --- | --- |
| `ENABLE_TRANSPORT=ON` | 1 | 构建传输运行时及其后端 |
| `ENABLE_EXECUTOR=ON` | 2 | 构建远程节点运行的 `catalyst-executor` 进程 |
| `LLVM_TARGETS_TO_BUILD` | 2 | `host` 为本机构建，`AArch64` 用于开发板，`X86` 用于服务器，后者在非 x86 构建机上需显式指定 |

<a id="pennylane-and-triton"></a>

### 安装 PennyLane 和 Triton

`make all` 会安装 Catalyst 在 `.dep-versions` 中指定的 PennyLane 版本。演示 2、2a 和 5 使用 Triton 生成解码器。要运行这些演示，可在当前虚拟环境中直接安装：

```bash
pip install triton
```

缺少 Triton 时，这三个演示会报错 `ImportError: Triton decoders require installed 'triton' Python package`。

<a id="backline"></a>

### 获取 Backline 演示源码

```bash
git clone https://github.com/PennyLaneAI/backline.git ~/backline
```

<a id="check"></a>

### 验证本地环境

先查看 PennyLane 版本，并确认可以访问 `Controller` 和 `Backline`：

```bash
python -c "import pennylane as qp; print(qp.__version__, qp.Controller, qp.Backline)"
```

再运行演示 1，验证本机 CPU 之间的通信：

```bash
cd ~/backline/demos
./demo_1_local_cpu_to_local_cpu_memcpy.py
```

<a id="tier-2--demo-1a"></a>

## 第 2 档：单机 RDMA 演示 1a

演示 1a 的两端位于同一进程，通过 Soft-RoCE 或回环设备完成一次 RDMA 往返通信。

```bash
sudo apt install libibverbs-dev ibverbs-providers ibverbs-utils rdma-core
```

列出当前可见的 verbs 设备：

```bash
ibv_devices
```

如果列表为空，可启用 [Soft-RoCE](https://github.com/linux-rdma/rdma-core/blob/master/Documentation/rxe.md)，让普通网络接口作为 verbs 设备使用。将 `<interface>` 换成实际网卡名。

```bash
sudo modprobe rdma_rxe
sudo rdma link add rxe0 type rxe netdev <interface>
```

如果是在构建 Catalyst 后才安装 `libibverbs-dev`，需要重新构建运行时。CMake 会缓存首次配置时检测到的 RDMA 后端，因此先清除 `runtime/build`，再运行 `make runtime`。

```bash
cd "$CATALYST_ROOT"
export ENABLE_TRANSPORT=ON ENABLE_EXECUTOR=ON LLVM_TARGETS_TO_BUILD="host;AArch64;X86"
rm -rf runtime/build && make runtime
```

切换档位后如果工具链发生变化（包括新增 ROCm），也要按此方式重新构建。再次构建时，Catalyst 会重复运行补丁步骤。已经应用过的补丁可能打印 `error: patch failed` 和 `patch does not apply`，这种情况不会中止构建。

<a id="tier-3--gpu-demos-2-2a-3"></a>

## 第 3 档：远程 GPU 演示 2、2a、3

需要两台机器。本地构建机编译并启动演示。远程服务器上运行两个进程：控制器发送纠错综合征（syndrome），协处理器经该服务器的 RDMA 网卡接收数据，并在 GPU 上执行解码。

<a id="packages"></a>

### 安装构建机工具

```bash
sudo apt install wget gnupg rsync
```

`wget` 和 `gnupg` 用于添加 ROCm 软件源。`rsync` 用于复制服务器的 sysroot，缺失时 `make sysroot` 会失败。

<a id="rocm-on-this-machine"></a>

### 在构建机安装 ROCm

构建时通过配置指定目标 GPU 架构，因此构建机可以没有 GPU。编译器需要能从 `PATH` 找到 `hipcc`，并能访问设备端库。

```bash
sudo mkdir -p --mode=0755 /etc/apt/keyrings
wget -qO- https://repo.radeon.com/rocm/rocm.gpg.key \
    | sudo gpg --dearmor -o /etc/apt/keyrings/rocm.gpg
echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/latest noble main' \
    | sudo tee /etc/apt/sources.list.d/rocm.list
printf 'Package: *\nPin: origin repo.radeon.com\nPin-Priority: 900\n' \
    | sudo tee /etc/apt/preferences.d/rocm-pin-900
sudo apt update && sudo apt install -y hip-dev rocm-device-libs
export PATH=/opt/rocm/bin:$PATH
```

| 发行版 | 软件源与版本选择 |
| --- | --- |
| Debian、Ubuntu | 上述命令使用 AMD 的 apt 源。`noble` 对应 Ubuntu 24.04，22.04 使用 `jammy`。运行 `. /etc/os-release && echo $VERSION_CODENAME` 可查看本机代号，再核对 [AMD 软件源支持的代号](https://repo.radeon.com/rocm/apt/latest/dists/)。 |
| RHEL、Rocky、Alma、SLES、Azure Linux | AMD 也提供这些发行版的软件包。[ROCm 软件源](https://repo.radeon.com/rocm/)中可查看 `el8`、`el9`、`el10` 和 `azurelinux3` 等目录。 |
| 其他发行版 | 支持范围和安装方式见 [AMD 的 Linux 安装指南](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/)。 |

软件源 URL 中的 `latest` 会选择最新 ROCm。需要固定版本时可换成具体版本，例如 `.../rocm/apt/7.2.4`。保留上面的 apt 优先级设置，否则 Ubuntu 软件源中较旧的 `hipcc` 可能因软件包版本号而优先安装。CMake 通过运行 `hipconfig` 定位工具链，因此 `/opt/rocm/bin` 必须在 `PATH` 中。

目标为 NVIDIA GPU 时，安装 `hip-dev` 和 CUDA 12.8 或更新版本，并将 `/opt/rocm/bin`、`/usr/local/cuda/bin` 都加入 `PATH`。

<a id="the-server"></a>

### 配置远程服务器

交叉编译和运行演示分别读取下面两个文件。默认值对应参考硬件，使用自己的服务器时需同时修改。

| 用途 | [threadripper.conf](config/xbuild/targets/threadripper.conf) | [machines.toml](config/machines.toml) 的 `[server]` |
| --- | --- | --- |
| 读取时机 | 交叉编译时，确定目标机能运行哪种二进制文件 | 启动演示时，确定怎样连接服务器及启动哪些进程 |
| 配置内容 | CPU 目标三元组、glibc 版本、C++ ABI 上限、加载器路径、`TARGET_GPU_ARCH` 和 sysroot 来源 | SSH 地址、RDMA 网络地址、各节点端口、部署包、executor 命令和环境变量 |

两份配置不会自动同步，需要核对以下三项：

| 项目 | 如何核对 |
| --- | --- |
| SSH 地址 | 目标描述的 `SYSROOT_PROVIDER_ARGS="host=..."` 和 `machines.toml` 的 `[server.executor] host` 应指向同一台服务器。默认均为参考地址 `192.168.3.14`。 |
| 部署包 | `deploy = ["threadripper-bundle"]` 应指向使用 `TARGET=threadripper` 构建的包。其他目标机的包可能正常传输，到设备上运行时才报错。 |
| GPU 架构 | `TARGET_GPU_ARCH` 应与服务器的实际显卡匹配，例如 AMD 的 `gfx90a` 或 NVIDIA 的 `sm_80`。构建系统按架构标识选择厂商工具链。 |

`threadripper` 是构建目标名称，`[server]` 是运行节点名称。两者通过部署包名称关联。

如果还没有目标机描述文件，可通过 SSH 读取该机器的信息。将 `<name>` 和 `you@host` 换为目标名及 SSH 账号地址：

```bash
cd ~/backline/config/xbuild
make probe TARGET=<name> SSH=you@host
```

命令会生成包含 `TARGET_GPU_ARCH` 的 `targets/<name>.conf`。仍需在 `machines.toml` 中填写对应的 `[server]` 配置。

服务器上的动态加载器需要能找到厂商运行库。AMD 的默认路径是 `/opt/rocm/lib`，NVIDIA 的默认路径是 `/usr/local/cuda/lib64`。可通过 `ldconfig` 注册，或加入 `LD_LIBRARY_PATH`。加载失败时协处理器无法启动。

复现参考延迟需要在线程绑定和实时优先级下运行 executor，因此服务器使用 `NOPASSWD` sudo。若将 `config/machines.toml` 中的 `sudo` 设为 `false`，演示仍可运行，但线程绑定和调度条件会改变。

<a id="build-and-deploy-its-bundle"></a>

### 构建和部署服务器所需的包

部署包汇集为同一台目标机编译的组件。依次复制 sysroot、交叉编译组件、组装部署包，再将包放入演示程序读取的目录。

```bash
SERVER=you@192.168.3.14                  # 换成自己的服务器地址
cd ~/backline/config/xbuild

# 复制目标机的头文件和库，供构建时链接
make sysroot TARGET=threadripper SYSROOT_PROVIDER_ARGS="host=$SERVER port=22"

# 为目标机交叉编译各个组件
make build TARGET=threadripper CATALYST="$CATALYST_ROOT" \
    COMPONENT="executor rt-transport rt-capi rtd-null-qubit cpu-verbs-controller \
               cpu-verbs-coprocessor steane-coprocessor-cpu echo-coprocessor-cpu gpu-coprocessor"

# 汇集产物，逐项核对目标平台，并生成部署脚本
make bundle TARGET=threadripper BUNDLE=threadripper-bundle CATALYST="$CATALYST_ROOT"

# 将部署包放入演示程序读取的目录
mkdir -p ~/bundles
cp -R build/threadripper/bundles/threadripper-bundle ~/bundles/
export BACKLINE_BUNDLES=~/bundles
```

`make sysroot` 通过 SSH 从目标机复制头文件和库，确保链接时使用目标机上的版本。`make bundle` 收集 `make build` 生成的文件，因此需要先构建组件。`BACKLINE_BUNDLES` 指向部署包的父目录，每个包各占一项。使用相对路径时，以仓库根目录为基准。

<a id="tier-4--fpga-demos-4-5"></a>

## 第 4 档：FPGA 演示 4、5

需要三台设备：本地构建机、第 3 档的 GPU 服务器和 VPK120 开发板。控制器在开发板上运行，由硬件发送纠错综合征并检测响应，请求和响应经 RDMA 网络在开发板与服务器之间往返。

先为 VPK120 安装配套镜像并完成板卡初始化，步骤见 [VPK120 配置指南](https://github.com/PennylaneAI/backline-vpk120/tree/v0.1.0)。开发板的 sysroot 从发行版软件包生成：

```bash
cd ~/backline/config/xbuild
make sysroot TARGET=vpk120
make build TARGET=vpk120 CATALYST="$CATALYST_ROOT" \
    COMPONENT="executor rt-capi rtd-null-qubit hwhs-capi-backend \
               hwhs-controller-session swhs-capi-backend rt-transport"
make bundle TARGET=vpk120 BUNDLE=vpk-bundle CATALYST="$CATALYST_ROOT"

cp -R build/vpk120/bundles/vpk-bundle ~/bundles/
```

已配置好的开发板应有 `/dev/mem` 和由外部内核模块提供的字符设备。在[机器配置](config/machines.toml)中填写板卡地址和账号。

<a id="reference"></a>

## 交叉编译参考

[交叉编译系统说明](config/xbuild/README.md)介绍目标、组件和部署包，列出各个 make 目标，并说明如何添加机器。
