# 统一部署配置

两种平台使用同一套部署逻辑，只编辑仓库根目录 `.env`，不需要修改 Compose、Nginx 或 Python。
仓库提供 `.env.example` 作为带注释的公开模板，真实 `.env` 和生成配置包含凭据，必须备份且不能提交。

```sh
# 首次只生成本地配置和随机密钥，不拉代码、不启动容器
sh deploy.sh --prepare-only
# 编辑 .env，再部署；默认先 git pull --ff-only
sh deploy.sh
# 远程源码未变化、仅修改 .env：复用镜像，刷新运行配置
sh deploy.sh
# 强制重新构建镜像（默认已自动检测相关源码变化）
sh deploy.sh --build
```

首次运行默认使用内置 MySQL 和本地文件存储。已有 `.env` 的值不会被覆盖；缺失选项会补齐。
原 `.env.deploy` 在没有 `.env` 时自动迁移；两者都有时以 `.env` 为准，缺失的应用签名密钥继承旧文件。
已有数据库必须沿用原数据库密码；修改 MYSQL_PASSWORD 不会修改 MySQL 中的密码。
不要删除配置后重新生成密码或删除数据库卷来解决连接错误。

## 外部 MySQL

在 `.env` 填写：

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
Vite 本地开发仍沿用 mango-console/.env.dev 等文件，Docker 部署由根目录 .env 的运行时配置覆盖。

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

两个仓库的部署脚本、配置模板、生成器与 Dockerfile 保持一致。环境差异只放在各部署的 `.env`，
不使用“公司专用 YAML”或“开源专用脚本”。Compose 与 Kubernetes 都消费同一份校验后的配置；
资源清单各自生成，不能直接把 Compose 文件交给 Kubernetes。

配置分层只有三层：`.env.example` 定义默认值和说明；私有 `.env` 定义环境差异；
`deploy/generated/` 为可重新生成的结果。不要手工修改生成文件，也不要提交真实 `.env`。

### Kubernetes

```sh
# 修改 .env：DEPLOY_TARGET=k8s；填写集群可拉取的镜像地址、存储与入口配置
sh deploy.sh --prepare-only
# 确认 kubectl 当前上下文和 K8S_NAMESPACE 后执行
sh deploy.sh
# 也可临时选择目标，不修改 .env
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

### 检查与升级

```sh
python3 -m unittest discover -s deploy -p 'test*.py'
node --test deploy/test_frontend_runtime.mjs
# 只修改 .env 后部署会复用已有镜像，重新生成网关/前端运行时配置。
sh deploy.sh
# 更新源码后重新构建：需要足够内存，低配置服务器建议先构建镜像再填写镜像标签。
sh deploy.sh --update
```

当前两个目标的设计与自动化校验共用同一套测试；实际集群网络、Ingress 与存储权限仍需在目标
Kubernetes 集群验收。不要把结构校验等同于真实集群部署成功。


## 沿用已有 Python 数据库配置

已有公司环境或曾修改底层配置的用户，在根目录 `.env` 中设置：

```dotenv
MYSQL_MODE=settings
DJANGO_ENV=dev
VUE_ENV=dev
PUBLIC_URL=https://platform-dev.example.com
```

`settings` 模式读取所选 `MangoServer/src/settings/dev.py`、`test.py` 或 `master.py` 的数据库值，
不启动内置 MySQL，也不改写这些文件；dev.py 中已有的可选 database.json 覆盖规则仍然生效。
`.env` 中 MYSQL_HOST/PORT/DATABASE/USER/PASSWORD 在此模式下不覆盖 Python 配置，也不会把数据库密码
复制回 `.env`。生成的私有部署文件会统一给后端、Worker、备份和迁移任务传递读取到的实际参数。
修改 Python 配置后再次运行 `sh deploy.sh` 即可刷新连接参数，不需要重新构建镜像。

明确选择 `MYSQL_MODE=external` 时才采用 `.env` 中的外部数据库值；选择 internal 时才启动内置数据库。
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
K8s 模式也会先同步代码，镜像仍由 CI/镜像仓库准备，按 `.env` 的镜像标签发布。

前端源码变化且需要本地构建镜像时，主机仍需足够内存；此改造不会消除前端编译的资源要求。
