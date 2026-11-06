# Docker 构建安装包

此目录保存执行器 Docker 构建时必须使用、且不应在流水线中临时从公网下载的安装包。

## k6

固定版本为 `2.2.0`，同时提供 Linux `amd64` 与 `arm64` 安装包。Docker BuildKit 会通过自动参数 `TARGETARCH` 选择对应文件。

| 文件 | SHA-256 |
| --- | --- |
| `k6/k6-v2.2.0-linux-amd64.tar.gz` | `b5a8003c86f35f5cd5ceef1490312c48e587696c94d998cefc6d7b3b4cb1597d` |
| `k6/k6-v2.2.0-linux-arm64.tar.gz` | `4ecd64cadcc792402d16293836115480419c4447c032858f564852d98f1bf54c` |

更新版本时必须同时更新 Dockerfile、两个架构的安装包、校验值及 `src/services/perf/k6_runtime.py` 中的版本定义。

Python 内部包继续存放在项目根目录的 `local_packages/`。Playwright/Ubuntu 基础镜像仍通过公司内部 OCI 镜像仓库提供，不应作为镜像归档提交到 Git。
