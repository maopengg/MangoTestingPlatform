# 统一部署配置

Compose 与 Kubernetes 使用同一套部署逻辑。用户只编辑根目录 `.env.example`，然后运行：

```sh
sh deploy.sh
# 只检查并生成配置，不拉代码、不启动服务
sh deploy.sh --prepare-only
# 强制重建镜像
sh deploy.sh --build
```

- `.env.example` 是唯一用户配置入口；填入真实凭据后不要提交到仓库。自动拉代码会保护本地配置，并补充上游新增选项，不覆盖自定义值。
- `.env` 是自动生成的私有状态，保存生效配置和随机密钥，无需编辑。必须备份；不要删除、提交或重新生成已有数据库的密钥。
- 首次升级会沿用已有 `.env` / `.env.deploy` 配置，模板中显式修改的选项优先；未修改的旧默认构建堆上限 2560MB 自动升级为 auto。后续只改 `.env.example`。
- 密码项留空时沿用已保存的密码；首次内置数据库部署才生成随机密码。修改配置中的密码不会修改数据库中的账号密码。
- 启动脚本首先只读校验必填项，失败时不拉代码、不生成密钥、不构建或停止服务。`PUBLIC_URL` 必须改为客户端实际访问的 IP 或域名；空值、`CHANGE_ME` 等占位符、localhost 和监听地址都会拒绝启动。MySQL、对象存储和执行器按启用模式检查，未启用的可选项可以留空。

### 必填项检查范围

默认值可直接使用；把实际依赖的字段清空或保留占位符会中断发布。错误只列字段名，不回显密码；一次列出当前模式缺少的必填项，修改 `.env.example` 后重新执行即可。

| 使用场景 | 校验内容 |
| --- | --- |
| 所有部署 | 平台地址、后端代理、数据目录、前后端及基础服务镜像、运行环境、进程与日志参数 |
| Compose | 网页监听地址和端口、构建基础镜像、包下载源、构建堆配置 |
| MySQL | 内置库名、业务账号、容量参数；外部数据库还需地址、端口和原密码；settings 模式核对所选 Python 配置 |
| MinIO / TOS | 桶名；外部存储的 endpoint、访问密钥、下载地址；TOS 还需区域，内置 MinIO 还需镜像 |
| 启用执行器 | 镜像、平台地址、账号密码、能力配置、并发与队列参数 |
| Kubernetes | 命名空间、镜像策略、运行卷容量与访问模式、DNS、等待时间；按需检查内置数据库/MinIO 容量、NodePort、TLS 对应域名 |

未启用的执行器、存储或 K8s 选项不要求填写；内置密码与平台密钥首次仍可自动生成，以后沿用保存值。`--target k8s` 同样先按 K8s 模式校验，不会绕过检查。
- 外部 MySQL 填写 `MYSQL_MODE=external`；沿用 dev/test/master.py 则填写 `MYSQL_MODE=settings`，不会改写这些底层文件。

## 前端构建内存

前端默认下载源统一为项目 `.npmrc` 中的华为镜像，Docker 和部署模板使用同一默认值；显式 `NPM_REGISTRY` 可覆盖。锁文件使用 npm 标准的 `registry.npmjs.org` 地址，由 npm 映射到配置的镜像源，避免锁死到其他镜像；不改变包版本和 integrity。CI 保留按依赖清单区分的 `node_modules` 缓存，并增加独立、跨清单复用的 `.npm/_cacache` 下载缓存，`npm ci --prefer-offline` 优先使用已下载且校验通过的内容。安装失败也保存下载缓存；首次冷缓存仍需下载，Runner 必须实际支持缓存存储。

CI 和 Docker 通过 `scripts/ci-console-build.sh` 分别输出依赖准备、前端打包的耗时及退出码；失败立即停止，不继续下一阶段。项目 `.npm` 目录不进入 Git 或 Docker 构建上下文。

`NODE_HEAP_MB=auto` 默认使用 4096MB Node 堆；需要时只在 `.env.example` 改为整数 MB。构建前检查主机可用内存与 Swap、Docker 总内存及可读取的 cgroup 限制，并为堆外内存预留至少 1536MB。检查不通过时提前退出，不停止现有服务。

Univer、Mermaid、Excel、ECharts 和 CodeMirror 依赖先由 esbuild 独立打包，Vite/Rollup 再组装业务页面；同一套图表、编辑器的入口共享模块图，开发服务仍使用原来的依赖入口。默认堆上限维持 4096MB，低内存验收使用 `NODE_OPTIONS=--max-old-space-size=2048 npm run build:dev`，当前源码已在本地 Node 22 下通过。这只限制 Node 堆，不代表构建总进程占用不超过 2GB，也不是对所有 4GB 主机或 Linux 容器的保证。CI 构建容器保留 6GiB，Node 堆为 4096MB。

4GB 运行服务器优先只部署 CI 生成的镜像或静态产物，Nginx 不运行 Node 构建进程。若在运行服务器上源码构建，后台服务和操作系统会占用内存，仍可能需要额外可用内存/Swap 才能通过资源检查；不会自动停止现有服务或调整 Swap。堆耗尽时保留日志排查，不能靠无限重试解决。普通配置变更仍复用现有镜像。

## Git 更新与兼容

源码检查通过 Python `cwd` 指定工作目录，不使用旧版 Git 不支持的全局 `-C`。Git 检查失败时报告子命令、退出码和脱敏错误，并停止部署。

默认仅 `git pull --ff-only`，不会重置本地代码或改写历史。`.env.example` 的本地修改会临时备份在 Git 私有目录，更新失败则恢复原内容；若过程被中断，按提示运行 `python3 deploy/config_sync.py restore --failed` 恢复。其他源码冲突和历史分叉必须自行确认处理，脚本不会自动覆盖。

## 数据源性能治理版本的部署检查

部署入口和操作步骤不变：Compose 仍运行 `sh deploy.sh`，K8s 仍使用既有 `.env.example` 和部署入口，GitLab 仍走原镜像构建、配置仓库更新和 Argo 同步流程。本次只增加自动校验，不自动生成迁移、不清理历史业务数据。

- 后端 Dockerfile 从 `requirements/master.txt → base.txt` 安装依赖，并安装本地 wheel；构建额外验证 `greenlet`、`httpx` 和 Redis RESP 解析器可导入。依赖文件变化会触发后端镜像重建，不需要单独更新 scheduler 依赖。
- API、scheduler、Worker、MCP、realtime 使用同一个 `SERVER_IMAGE`。Compose 增加 scheduler healthcheck；本仓库 K8s 生成器增加同等 startup/readiness 探针，探针为 `python manage.py check_scheduler`。
- 探针只读检查当前容器的新鲜心跳、清理线程最近正常轮询及 RuntimeKV 表可读性，不执行真实清理。线程连续异常或卡住不再仅凭“进程还在”判就绪；使用 readiness 而非 liveness，不因探针失败直接杀掉在途清理。
- 本地 `start_dev_services.sh` 在 dev/dev1 也启动 scheduler，但加 `--cleanup-only`，不触发定时业务任务、系统定时维护或旧定时任务分发；test/master 保持完整调度。本地脚本会先检查新依赖，缺失时明确失败，需要按原方式安装虚拟环境依赖，不会静默带缺失依赖启动。

每个 scheduler 的清理消费线程默认 2 个，可在“系统运维 → 配置管理 → 数据源性能保护”的“连接与调度”修改（1～16）。保存后下一轮调度自动应用，不修改部署参数、不重启服务；缩容等待当前阶段结束，实例总限流不变。多个 scheduler 进程各自应用同一配置。

只有正式测试报告的清理进入后台队列；无报告的单次执行、调试及手动补清直接同步执行，同样保留执行控制和审计记录，不依赖 scheduler 在线。平台部署仍需启动 scheduler，以支持正式报告、定时任务及异常责任核查。同步不是跳过清理观察和最终验证。

**GitLab 引用的外部配置仓库不由本仓库 K8s 生成器管理。** 首次发布此版本前，需确认该仓库的 scheduler 容器与 API 使用本次同一后端镜像，并添加以下容器就绪探针；本地修改不能自动证明外部仓库已具备这些配置：

```yaml
readinessProbe:
  exec:
    command: [python, manage.py, check_scheduler]
  periodSeconds: 15
  timeoutSeconds: 30
startupProbe:
  exec:
    command: [python, manage.py, check_scheduler]
  periodSeconds: 15
  timeoutSeconds: 10
  failureThreshold: 12
```

探针继承 scheduler 容器的环境；若设置 `MANGO_SERVICE_INSTANCE`，必须与 `run_scheduler --node-name` 一致。每个调度副本应使用独立实例名，避免共享心跳行。CI 工具镜像须有 `python3`，已有 Argo 登录身份须能读取应用及工作负载详情。

流水线两个发布成功分支都会运行 `deploy/verify_runtime.py`，只读核对实际工作负载的镜像、更新代次/副本、scheduler 和探针；缺项、旧镜像或无读取权限均终止“成功”判定，不能只检查 API HTTP 健康。不会自动修改集群或外部配置仓库。只读核验使用 [Argo CD get-resource](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_get-resource/) 的 JSON 输出。

副本/代次尚未就绪时默认最多读取 4 次，间隔 5 秒，每次输出失败资源的 namespace、kind、name 以及目标、就绪、更新副本和 generation 数值；缺失状态明确标为“缺失”，不当作健康。镜像不一致、未获允许的零目标副本、缺少 scheduler/探针或读取权限错误直接失败。诊断不输出环境变量、凭据或完整 manifest。重试耗尽后，应提供这些诊断行及对应 Pod 的 Events，由此定位拉镜像、探针、调度或状态读取问题；不要通过移除校验强行判成功。

dev/dev1 流水线明确传入 `--allow-disabled-scheduler`：scheduler 目标副本为 0、控制器已处理当前代次且实际副本归零时，按主动停用通过，不要求运行就绪探针。启用到 1 个或更多副本时仍必须检查就绪副本和 `check_scheduler` 探针；其他后端工作负载不能借此跳过检查。test/master/Tag 默认不传该参数，继续要求运行中的 scheduler。该参数只影响发布判定，不会启动服务、修改副本或改写外部部署配置。

### MCP 发布排空

发布入口不变。MCP 收到 SIGTERM 后拒绝新的工具执行，readiness 返回 503；正在运行的工具（包括同步线程和其后置清理）最多等待 300 秒，然后才进入 ASGI 退出。重复 SIGTERM 不绕过排空。Compose 停止宽限期和本仓库 K8s 模板均设为 360 秒；流水线等待窗口为 420 秒，不删减原有健康/镜像校验。

使用独立 GitOps 配置仓库时，**必须在同次发布前**同步 MCP Pod 的 `terminationGracePeriodSeconds: 360`，以及指向 MCP 端口 `/health/ready` 的 `readinessProbe`、`startupProbe`；容器需显式通过 `python manage.py run_mcp_service` 启动，不能直接用 Uvicorn 命令绕过排空入口。只更新应用镜像不能修改已有 Pod 的默认 30 秒宽限期。`verify_runtime.py` 只读校验这些条件，缺少时会明确拒绝确认发布成功；不会自动改集群或配置仓库。

只有所有工具实际退出后才持久化精确进程的排空凭据。Trace/审计对账按进程身份核验凭据，不以心跳消失、Pod 名变化或租约过期推断业务成功。强制终止、超出宽限期、存储失败或缺少旧版本凭据时，原请求仍需核查，禁止自动重放、清空配额或将清理标为通过。清理补偿继续按原资源快照、完整观察窗口及最终回查执行；成功后仅清除工厂执行上的旧清理错误，保留历史失败任务和超时审计。

任务索引迁移已随源码提供；升级前请备份数据库并核对仓库已有迁移。部署脚本只应用已有迁移，不生成新迁移。RuntimeKV 既有表必须已就绪，否则健康检查拒绝通过。

## MySQL 三种模式如何选择

`MYSQL_MODE` 控制数据库的部署方式和连接配置来源，`DJANGO_ENV` 才负责选择 dev/test/master 运行环境。
三种模式在 Compose 和 K8s 中含义一致：

| MYSQL_MODE | 是否随平台启动 MySQL | 连接参数来源 | 适用场景 |
| --- | --- | --- | --- |
| `internal`（默认） | 是：Compose 容器或 K8s StatefulSet | `.env.example` 的库名、业务账号/密码和 root 密码；内部地址固定 `db:3306` | 新部署，没有现成数据库 |
| `external` | 否 | `.env.example` 的 `MYSQL_HOST/PORT/DATABASE/USER/PASSWORD` | 已有 MySQL、云数据库或独立数据库服务 |
| `settings` | 否 | `DJANGO_ENV` 所选 `MangoServer/src/settings/dev.py`、`test.py` 或 `master.py` | 沿用公司或用户已有 Python 数据库配置 |

**internal 示例：**

```dotenv
MYSQL_MODE=internal
MYSQL_DATABASE=mango_server
MYSQL_USER=mango
MYSQL_PASSWORD=
MYSQL_ROOT_PASSWORD=
```

全新数据库的空密码由首次准备配置时生成并保存；已有数据库须填写原密码。
此模式的 `MYSQL_HOST` 和 `MYSQL_PORT` 不参与连接地址选择，始终使用内部 `db:3306`。
`MYSQL_EXPOSE_PORT` 是可选的宿主机对外端口，与内部连接端口分开。

**external 示例：**

```dotenv
MYSQL_MODE=external
MYSQL_HOST=mysql.example.com
MYSQL_PORT=3306
MYSQL_DATABASE=mango_server
MYSQL_USER=mango
MYSQL_PASSWORD='填写已有数据库密码'
```

需提前准备目标数据库及账号，并保证部署容器能访问该地址；此模式不使用 `MYSQL_ROOT_PASSWORD`。
后端、Worker、连接检查、备份及既有迁移均使用同一组外部数据库参数。

**settings 示例：**

```dotenv
MYSQL_MODE=settings
DJANGO_ENV=dev
```

此例读取 `dev.py` 中的 `MYSQL_IP`、`MYSQL_PORT`、`MYSQL_DB_NAME`、`MYSQL_USER` 和 `MYSQL_PASSWORD`。
改为 `DJANGO_ENV=master` 就读取 `master.py`，改为 `test` 则读取 `test.py`。
`.env` 中即使还留着 MYSQL_HOST 等值，也不会覆盖所选 Python 文件中的连接参数；不会启动新数据库、
不会改写 Python 文件，也不会把源文件密码复制到 `.env`。dev.py 已有的可选本地 JSON 覆盖逻辑仍生效。

这些模式只选择数据库和配置来源；切换模式不会把旧数据库的数据自动复制到新数据库。

## 外部 MySQL

在 `.env.example` 填写：

```dotenv
MYSQL_MODE=external
MYSQL_HOST=mysql.example.com
MYSQL_PORT=3306
MYSQL_DATABASE=mango_server
MYSQL_USER=mango
MYSQL_PASSWORD='填写自己的密码'
```

此模式不会启动内置 MySQL，也不会依赖或进入 db 容器。启动前验证连接，再停止应用消费者并使用
临时 MySQL 客户端备份同一个目标库；外部账号需具备备份读取与平台迁移所需权限。
验证或备份失败立即停止，不继续迁移。脚本只执行仓库已有迁移，不生成迁移文件，不清库。
真实外部数据库请自行备份验证恢复能力，不要在公司生产库试部署。

## 文件存储

- `FILE_STORAGE_BACKEND=local`：文件保存在 MANGO_DATA_DIR/server_runtime/media，网关提供下载。
- `FILE_STORAGE_BACKEND=minio`、`MINIO_MODE=internal`：自动启动 MinIO，凭据首次自动生成。
  默认桶为 mango-file，公开地址自动取 PUBLIC_URL/minio/mango-file。内置 MinIO 不对外暴露管理端口。
- `FILE_STORAGE_BACKEND=minio`、`MINIO_MODE=external`：填写 S3_ENDPOINT、S3_BUCKET、S3_ACCESS_KEY、
  S3_SECRET_KEY、S3_PUBLIC_BASE_URL，以及 S3_USE_HTTPS。公开地址应包含桶路径或桶域名。
- `FILE_STORAGE_BACKEND=tos`：填写相同 S3 参数，另外填写 S3_REGION，通常启用
  S3_USE_HTTPS=true、S3_VIRTUAL_HOST_STYLE=true、S3_PRESIGNED=true、S3_AUTO_CREATE_BUCKET=false。
  TOS 桶需预先创建，S3_ENDPOINT 使用 S3 兼容服务地址，不使用控制台地址；公开桶地址必须能被浏览器访问。

所有存储参数会传递给 API、Worker、调度与实时服务。启动前检查桶访问，下载签名在后端生成；
浏览器运行时配置只有 API、WebSocket 与公开存储地址，不包含数据库密码或对象存储密钥。
切换存储不自动迁移历史附件，切换数据库也不自动复制旧库数据。

## 同源与跨域

同源代理（默认）：

```dotenv
PUBLIC_URL=http://platform.example.com:8001
WEB_PORT=8001
FRONTEND_API_BASE=/api
BACKEND_UPSTREAM=http://mango_server:8000
API_PORT=
```

后端内部端口8000、前端端口8001不妨碍同源；浏览器通过8001/api访问后端。
后端在其他机器时，仅修改 BACKEND_UPSTREAM。WebSocket 与 MCP 在本机服务时仍由本地网关代理；
若使用另一台平台的实时服务，需要显式设置 FRONTEND_SOCKET_URL 为那台平台对外的 ws(s) 地址。

跨域直连（浏览器访问独立 API 入口）：

```dotenv
PUBLIC_URL=http://web.example.com:8001
WEB_PORT=8001
API_PORT=8000
FRONTEND_API_BASE=http://api.example.com:8000/api
CORS_ALLOWED_ORIGINS=http://web.example.com:8001
FRONTEND_SOCKET_URL=
```

API_PORT 可选，会额外发布完整网关（含 API/WebSocket/MCP/媒体），不是把浏览器指向前端静态容器。
API 在另一台服务器时留空 API_PORT，填那台服务器真实的 API 地址。
WebSocket 留空会从 FRONTEND_API_BASE（同源时从 PUBLIC_URL）推导，特殊映射可显式设置。
HTTPS 前端必须配 HTTPS API / WSS；证书由外部反向代理终止，并转发到 WEB_PORT。
内部 BACKEND_UPSTREAM 可以使用 HTTP，与浏览器访问的 HTTPS 地址分开。

修改地址后 `sh deploy.sh` 即可，前端从 runtime-config.js 读取公开配置并禁用缓存，不需要重新构建。
Vite 本地开发仍沿用 mango-console/.env.dev 等文件，Docker 部署由根目录 .env.example 生成的运行时配置覆盖。

## 运维

要求 Docker Engine、Docker Compose V2、Python3。首次拉取镜像需要可用镜像源；前端构建需足够内存。
实际使用的 Compose 是 deploy/generated/compose.json（文件格式为 Compose 支持的 JSON）。
根目录 docker-compose.yml 只是同一配置的 include 入口（需 Compose 2.20+）。旧根 Compose 不再保留独立配置。

```sh
# 先生成配置后查看状态或日志，不输出完整配置，以免泄漏密码
# 使用 /dev/null 避免 Compose 再次解析 .env 中的特殊字符。
docker compose --env-file /dev/null -f deploy/generated/compose.json ps
docker compose --env-file /dev/null -f deploy/generated/compose.json logs --tail=100 mango_server
```

生成文件含部署密码，权限600；只有网关配置和浏览器公开配置权限644供Nginx读取。
备份位于 MANGO_DATA_DIR/backups。请同时备份 .env、数据库与本地附件或对象存储。
切换部署模式不会删除旧数据库容器、卷或对象数据；旧部署容器需要确认不再使用后自行停用。


## Compose 与 Kubernetes 共用配置

两个仓库的部署脚本、配置模板、生成器与 Dockerfile 保持一致。环境差异只放在各部署的 `.env.example`，
不使用“公司专用 YAML”或“开源专用脚本”。Compose 与 Kubernetes 都消费同一份校验后的配置；
资源清单各自生成，不能直接把 Compose 文件交给 Kubernetes。

配置分层：`deploy/defaults.env` 保存程序默认值；`.env.example` 是用户配置；私有 `.env` 保存生效输入和自动密钥；
`deploy/generated/` 为可重新生成的结果。不要手工修改生成文件，也不要提交真实 `.env`。

### Kubernetes

```sh
# 修改 .env.example：DEPLOY_TARGET=k8s；填写集群可拉取的镜像地址、存储与入口配置
sh deploy.sh --prepare-only
# 确认 kubectl 当前上下文和 K8S_NAMESPACE 后执行
sh deploy.sh
# 也可临时选择目标，不修改 .env.example
sh deploy.sh --target k8s
```

Kubernetes 使用与 Compose 相同的 SERVER_IMAGE / CONSOLE_IMAGE / ACTUATOR_IMAGE。
请提前构建并推送这些镜像到集群可访问的仓库；K8s 模式不在节点上编译源码。
私有仓库需在目标命名空间准备 imagePullSecret，再填写 K8S_IMAGE_PULL_SECRET。
切换公司/开源源码版本时构建对应的镜像，部署脚本保持相同。

集群需准备可用 StorageClass，内置 MySQL / MinIO 使用独立 PVC。
多个应用 Pod 共享 runtime，默认 K8S_RUNTIME_ACCESS_MODE=ReadWriteMany，要求存储类支持 RWX；
仅有 RWO 存储的集群需填写 ReadWriteOnce，并保证相关 Pod 可以在同一节点使用该卷。
这份模板是单实例部署，不自动提供数据库高可用，也不搬迁现有 Compose 数据。

K8S_SERVICE_TYPE 可选择 ClusterIP / NodePort / LoadBalancer；Ingress 可配置
K8S_INGRESS_HOST、K8S_INGRESS_CLASS、K8S_TLS_SECRET，证书 Secret 需提前准备。
公网地址仍由 PUBLIC_URL 表示。非默认集群 DNS 需调整 K8S_DNS_RESOLVER。

生成内容包含 Namespace、ConfigMap、Secret、PVC、Deployment、Service，按需包含
MySQL/MinIO StatefulSet 和 Ingress。预检查、备份、迁移使用独立 Job，顺序为：
基础资源就绪 → 只读连接检查 → 停止应用写入进程 → 备份 → 既有迁移和初始化 → 启动应用。
任一步失败即停止后续步骤；迁移失败需检查日志并按备份恢复，不自动逆向数据库迁移。
生成文件含 Secret，权限 600；不要把整个生成目录上传到公开仓库。
Kubernetes 容器日志轮转由节点 kubelet 管理，LOG_MAX_SIZE/LOG_MAX_FILE 只控制 Docker 日志。

### 常用可选项

- MYSQL_BINLOG=false 默认关闭内置 MySQL binlog；外部数据库的 binlog 由数据库管理员配置。
- LOG_MAX_SIZE=10m、LOG_MAX_FILE=1：Docker 单容器日志保留上限。
- MYSQL_EXPOSE_PORT 留空不暴露数据库；需要 DBX 时填写端口和 MYSQL_EXPOSE_BIND。
- MINIO_CONSOLE_PORT 留空不暴露控制台；需要时填写并选择绑定地址。
- API_WORKER_COUNT、API_THREAD_POOL_SIZE、UVICORN_WORKERS 控制服务进程和并发。
- ACTUATOR_ENABLED=true 时填写登录账号密码和镜像；已有独立执行器可保持 false。
  执行器镜像须包含本次环境变量入口更新，升级后确认设备中心显示已登录。
- EXTRA_HTTP_ROUTES='{"/attendance/":"http://attendance-workbench:80"}' 可保留附加服务入口；
  上游需在相同 Docker 网络或集群中可解析，此项不会增加登录验证。
- MONITORING_ENABLED=false 默认不启动独立监控进程。
  启用时只需将根目录 `.env.example` 中该值改为 `true`，再运行 `sh deploy.sh`；
  不需要编辑 `.env` 或手工启动容器。部署输出会提示 `monitoring-service：已纳入部署`。

### 检查与升级

```sh
python3 -m unittest discover -s deploy -p 'test*.py'
node --test deploy/test_frontend_runtime.mjs
# 只修改 .env.example 后部署会复用已有镜像，重新生成网关/前端运行时配置。
sh deploy.sh
# 更新源码后重新构建：需要足够内存，低配置服务器建议先构建镜像再填写镜像标签。
sh deploy.sh --update
```

当前两个目标的设计与自动化校验共用同一套测试；实际集群网络、Ingress 与存储权限仍需在目标
Kubernetes 集群验收。不要把结构校验等同于真实集群部署成功。


## 沿用已有 Python 数据库配置

已有环境或曾修改底层配置的用户，在根目录 `.env.example` 中设置：

```dotenv
MYSQL_MODE=settings
DJANGO_ENV=dev
VUE_ENV=dev
PUBLIC_URL=https://platform-dev.example.com
```

`settings` 模式读取所选 `MangoServer/src/settings/dev.py`、`test.py` 或 `master.py` 的数据库值，
不启动内置 MySQL，也不改写这些文件；dev.py 中已有的可选 database.json 覆盖规则仍然生效。
`.env.example` 中 MYSQL_HOST/PORT/DATABASE/USER/PASSWORD 在此模式下不覆盖 Python 配置，也不会把数据库密码
复制回 `.env`。生成的私有部署文件会统一给后端、Worker、备份和迁移任务传递读取到的实际参数。
修改 Python 配置后再次运行 `sh deploy.sh` 刷新连接参数；脚本会检测源码变化并按需重建镜像，不会改写配置文件。

明确选择 `MYSQL_MODE=external` 时才采用 `.env.example` 中的外部数据库值；选择 internal 时才启动内置数据库。
部署脚本不生成、不覆盖 dev.py/test.py/master.py，也不修改用户的 database.json。
`git pull` 仍遵循 Git 自身的冲突规则，不使用 reset、checkout 或强制覆盖配置的命令。

公司原有 GitLab CI / Argo CD 流程继续使用 DJANGO_ENV 选择 Python 配置；未传入 MYSQL_* 环境变量时，
后端仍使用对应配置文件的原有值。本次提交不替换既有集群发布方式。


## 唯一启动入口与代码同步

只保留根目录 `deploy.sh`；旧 `start_service.sh` 已删除。正常部署统一执行：

```sh
sh deploy.sh
```

脚本默认先执行 `git pull --ff-only`，使用当前分支的远程跟踪分支；拉取失败、存在合并冲突或未配置
upstream 时立即停止，不会继续停止服务。不会执行 reset、强制 checkout，也不会覆盖 `.env` 或本地
Python 配置文件；发生冲突时需自行处理后重试。拉取成功后会重新加载刚拉到的部署脚本。

Compose 模式比较实际源码和镜像状态，仅重建有变化的后端/前端；即使事先手动 git pull，随后执行
脚本也能检测到待构建的源码。只有健康检查通过后才记录成功状态，文件位于私有的
`deploy/generated/last-success.json`。镜像缺失或来源无法确认时会构建，避免误用旧镜像。

`--build` 强制构建前后端，`--update` 保留为同义兼容参数；两者都会先拉取代码。
`--prepare-only` 只校验、生成本地配置，不进行拉取、构建、备份或服务启停。
K8s 模式也会先同步代码，镜像仍由 CI/镜像仓库准备，按 `.env.example` 的镜像标签发布。

前端源码变化且需要本地构建镜像时，主机仍需足够内存；此改造不会消除前端编译的资源要求。
