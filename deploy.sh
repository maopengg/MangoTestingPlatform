#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
ENV_FILE="$ROOT/.env"
PREPARE_ONLY=0
REBUILD=0
TARGET=''
while [ "$#" -gt 0 ]; do
    case "$1" in
        --prepare-only) PREPARE_ONLY=1 ;;
        --build) REBUILD=1 ;;
        --update) git pull --ff-only; REBUILD=1 ;;
        --target) shift; TARGET=${1:?--target 需要 compose 或 k8s} ;;
        *) echo '用法：sh deploy.sh [--prepare-only] [--build] [--update] [--target compose|k8s]' >&2; exit 1 ;;
    esac
    shift
done
command -v python3 >/dev/null || { echo '请先安装 python3' >&2; exit 1; }
python3 deploy/bootstrap.py init "$ENV_FILE"
[ -n "$TARGET" ] || TARGET=$(python3 deploy/bootstrap.py get "$ENV_FILE" DEPLOY_TARGET)
case "$TARGET" in
    compose) python3 deploy/bootstrap.py render "$ENV_FILE" ;;
    k8s) python3 deploy/bootstrap.py render-k8s "$ENV_FILE" ;;
    *) echo 'DEPLOY_TARGET 只支持 compose / k8s' >&2; exit 1 ;;
esac
if [ "$PREPARE_ONLY" = 1 ]; then
    echo "已验证 .env 并生成 $TARGET 部署配置；已有配置和密码保留。"
    exit 0
fi
if [ "$TARGET" = k8s ]; then
    if [ "$REBUILD" = 1 ]; then echo 'K8s 使用预先构建并发布的镜像，请先构建/推送 .env 中的 SERVER_IMAGE 和 CONSOLE_IMAGE。' >&2; exit 1; fi
    exec sh deploy/k8s.sh
fi
docker info >/dev/null
docker compose version >/dev/null
compose() { docker compose --env-file /dev/null -f "$ROOT/deploy/generated/compose.json" "$@"; }
compose config --quiet
DATA_DIR=$(python3 deploy/bootstrap.py get "$ENV_FILE" MANGO_DATA_DIR)
SERVER_IMAGE=$(python3 deploy/bootstrap.py get "$ENV_FILE" SERVER_IMAGE)
CONSOLE_IMAGE=$(python3 deploy/bootstrap.py get "$ENV_FILE" CONSOLE_IMAGE)
mkdir -p "$DATA_DIR/server_runtime/media" "$DATA_DIR/backups"
if [ "$REBUILD" = 1 ] || ! docker image inspect "$SERVER_IMAGE" >/dev/null 2>&1; then compose build mango_server; fi
if [ "$REBUILD" = 1 ] || ! docker image inspect "$CONSOLE_IMAGE" >/dev/null 2>&1; then compose build mango-console; fi
if [ "$(python3 deploy/bootstrap.py get "$ENV_FILE" MYSQL_MODE)" = internal ]; then
    compose up -d --wait --wait-timeout 180 db
fi
if [ "$(python3 deploy/bootstrap.py get "$ENV_FILE" FILE_STORAGE_BACKEND)" = minio ] && [ "$(python3 deploy/bootstrap.py get "$ENV_FILE" MINIO_MODE)" = internal ]; then
    compose up -d minio
fi
echo '验证数据库及存储配置（不修改数据）...'
compose run -T --rm --no-deps mango_server python /app/deploy_check.py
# Configuration generation can omit optional services; stop only services in this deployment.
STOP_SERVICES=$(python3 - <<'PY'
import json
s=json.load(open('deploy/generated/compose.json'))['services']
print(' '.join(x for x in s if x.startswith('api_worker_') or x in {'scheduler_service','mcp_service','realtime_service','monitoring_service','actuator','mango_gateway','mango_server'}))
PY
)
compose stop $STOP_SERVICES
PROJECT=$(python3 deploy/bootstrap.py get "$ENV_FILE" COMPOSE_PROJECT_NAME)
# Stop only retired application services owned by this project; retain data services.
for id in $(docker ps -q --filter "label=com.docker.compose.project=$PROJECT"); do
    SERVICE=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$id")
    case "$SERVICE" in
        monitoring_service|actuator|api_worker_*)
            if ! python3 -c 'import json,sys;sys.exit(sys.argv[1] not in json.load(open("deploy/generated/compose.json"))["services"])' "$SERVICE"; then docker stop "$id" >/dev/null; fi ;;
    esac
done
BACKUP="$DATA_DIR/backups/before-deploy-$(date +%Y%m%d-%H%M%S).sql"
umask 077
if compose run -T --rm --no-deps db_tools sh -c 'exec mysqldump --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" --single-transaction --no-tablespaces "$MYSQL_DATABASE"' > "$BACKUP"; then
    gzip "$BACKUP"
else
    echo '数据库备份失败，未执行迁移；正在恢复原有应用进程。' >&2
    compose start $STOP_SERVICES || true
    exit 1
fi
echo '备份完成，应用仓库已有迁移并初始化系统数据...'
compose run -T --rm --no-deps mango_server python manage.py migrate --noinput
compose run -T --rm --no-deps mango_server python manage.py createcachetable django_cache
compose run -T --rm --no-deps mango_server python manage.py init_system_data
compose up --no-start --no-deps --force-recreate mango-console mango_gateway
compose up -d --wait --wait-timeout 180
compose exec -T mango_gateway wget -q --spider http://127.0.0.1/healthz
compose ps
echo "平台入口：$(python3 deploy/bootstrap.py get "$ENV_FILE" PUBLIC_URL)"
echo '初始管理员密码保存在 .env；已有用户密码不会被重置。'
