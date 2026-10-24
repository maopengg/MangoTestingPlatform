# 单机一键部署

适用于 Debian/Ubuntu 上已安装 Docker Engine、Docker Compose 插件、Git 和 Python 3 的服务器。
建议至少 2 核 4GB、30GB 磁盘。构建前端可能需要额外内存，4GB 机器建议预留 2GB swap。

```sh
git clone https://gitee.com/mao-peng/MangoTestingPlatform.git
cd MangoTestingPlatform
sh deploy.sh
```

首次运行生成私有 `.env.deploy`（权限 600），包含数据库凭据、签名密钥和初始管理员密码；
再次运行会复用，不覆盖密码或删除数据库。原来的 `.env` 不参与此部署，避免开发配置污染服务器。
首次部署前可指定入口和数据目录：

```sh
PUBLIC_URL=https://test.example.com WEB_PORT=8000 MANGO_DATA_DIR=/mango_data sh deploy.sh
```

后续修改 `.env.deploy` 后重新执行。`PUBLIC_URL` 是浏览器实际访问的地址，NAT 外部端口可与
`WEB_PORT` 不同；在服务商控制台将分配到的公网端口转发至内部 8000。没有公网网页映射时可先用
SSH 的 `-L 18000:127.0.0.1:8000` 转发，在本机访问 `http://localhost:18000`。

流程：验证配置 → 顺序构建后端和前端 → 等待 MySQL 可用 → 备份已有数据库 → 停止消费者 →
应用已有迁移 → 创建数据库缓存表 → 幂等初始化配置/默认用户 → 启动并检查网页、数据库和实时服务。
任一步失败会返回非零退出码，修复后可重新执行；迁移失败时消费者保持停止，备份保留在数据目录。
脚本不会生成迁移文件，不执行 `makemigrations`，也不会清理数据库卷。

默认采用项目已有的本地文件存储，上传文件放在数据目录的 `server_runtime/media`，由网关只读提供访问。
不依赖 MinIO 官方镜像是否可下载。保留原 `docker-compose.yml` 供需要对象存储、更多 Worker 或执行器
的部署使用。此单机方案只部署平台；Web UI/Pytest 执行器在个人电脑或另一台机器连接平台。

管理员账号为 `admin`，初始密码见服务器 `.env.deploy` 中的 `MANGO_INITIAL_ADMIN_PASSWORD`。
仅首次创建用户时使用该值；已有账号不会因重新部署被重置。请在首次登录后修改密码。
同时备份 MySQL 数据和 `server_runtime/media`，仅备份 Git 仓库无法恢复测试数据和附件。

```sh
# 更新代码并部署（只允许快进更新，不覆盖本地改动）
sh deploy.sh --update
# 查看状态、日志
docker compose --env-file .env.deploy -f deploy/compose.single.yml ps
docker compose --env-file .env.deploy -f deploy/compose.single.yml logs --tail=100 mango_server
# 只生成或验证配置
sh deploy.sh --prepare-only
```

镜像默认来自 Docker Hub 官方 Python/Node/Nginx/MySQL 仓库，不访问火山镜像源。
构建时可通过 Docker build args 覆盖 `PYTHON_IMAGE`、`NODE_IMAGE`、`NGINX_IMAGE`；
Python/npm 包源可通过 `.env.deploy` 的 `PIP_INDEX_URL` 和 `NPM_REGISTRY` 配置。
