#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
ENV_FILE=${MANGO_ENV_FILE:-$ROOT/.env.deploy}
PREPARE_ONLY=0
UPDATE=0
for argument in "$@"; do
    case "$argument" in
        --prepare-only) PREPARE_ONLY=1 ;;
        --update) UPDATE=1 ;;
        *) echo "用法：sh deploy.sh [--prepare-only] [--update]" >&2; exit 1 ;;
    esac
done
if [ "$UPDATE" = 1 ]; then
    git pull --ff-only
fi
command -v python3 >/dev/null || { echo '请先安装 python3' >&2; exit 1; }
python3 deploy/bootstrap.py init "$ENV_FILE"
if [ "$PREPARE_ONLY" = 1 ]; then
    echo "部署配置已准备：$ENV_FILE（保留已有凭据）"
    exit 0
fi
docker info >/dev/null
docker compose version >/dev/null
compose() {
    docker compose --env-file "$ENV_FILE" -f "$ROOT/deploy/compose.single.yml" "$@"
}
compose config --quiet
DATA_DIR=$(python3 deploy/bootstrap.py get "$ENV_FILE" MANGO_DATA_DIR)
mkdir -p "$DATA_DIR/server_runtime/media" "$DATA_DIR/backups"

echo '构建前后端镜像（顺序构建，降低内存峰值）...'
compose build mango_server
compose build mango-console

echo '启动数据库并检查连接...'
compose up -d --wait --wait-timeout 180 db
TABLE_COUNT=$(compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" -D"$MYSQL_DATABASE" -Nse "SHOW TABLES"' | wc -l | tr -d ' ')
if [ "$TABLE_COUNT" -gt 0 ]; then
    echo '备份现有数据库...'
    BACKUP="$DATA_DIR/backups/before-deploy-$(date +%Y%m%d-%H%M%S).sql"
    umask 077
    compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --no-tablespaces "$MYSQL_DATABASE"' > "$BACKUP"
    gzip "$BACKUP"
fi

# 先停止消费者，避免旧进程在新表结构上继续领取任务。
compose stop scheduler_service api_worker_1 mcp_service realtime_service monitoring_service mango_gateway mango_server
echo '应用仓库已有迁移并初始化系统数据...'
compose run --rm --no-deps mango_server python manage.py migrate --noinput
compose run --rm --no-deps mango_server python manage.py createcachetable django_cache
compose run --rm --no-deps mango_server python manage.py init_system_data

echo '启动平台并等待健康检查...'
compose up -d --wait --wait-timeout 180
compose exec -T mango_gateway wget -q --spider http://127.0.0.1/
compose exec -T mango_gateway wget -qO- http://127.0.0.1/healthz
echo
compose ps
echo "平台入口：$(python3 deploy/bootstrap.py get "$ENV_FILE" PUBLIC_URL)"
echo "初始管理员：admin；密码保存在 $ENV_FILE 的 MANGO_INITIAL_ADMIN_PASSWORD。"
echo '文件持久化目录：'"$DATA_DIR/server_runtime/media"
echo 'NAT 服务器需将公网 HTTP 端口转发到 WEB_PORT；数据库无需公网映射。'
