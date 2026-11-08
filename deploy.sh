#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
ENV_FILE="$ROOT/.env.example"
PREPARE_ONLY=0
REBUILD=0
TARGET=''
parse_arguments() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --prepare-only) PREPARE_ONLY=1 ;;
            --build) REBUILD=1 ;;
            --update) REBUILD=1 ;;
            --target) shift; TARGET=${1:?--target 需要 compose 或 k8s} ;;
            *) echo '用法：sh deploy.sh [--prepare-only] [--build] [--update] [--target compose|k8s]' >&2; exit 1 ;;
        esac
        shift
    done
}
parse_arguments "$@"
command -v python3 >/dev/null || { echo '请先安装 python3' >&2; exit 1; }
configuration() {
    if [ -n "$TARGET" ]; then python3 deploy/bootstrap.py "$@" --target "$TARGET";
    else python3 deploy/bootstrap.py "$@"; fi
}
echo '校验 .env.example 必填配置...'
configuration check-inputs "$ENV_FILE"
if [ "$PREPARE_ONLY" = 0 ] && [ "${_MANGO_DEPLOY_SYNC_ROOT:-}" != "$ROOT" ]; then
    command -v git >/dev/null || { echo '请先安装 Git。' >&2; exit 1; }
    git rev-parse --is-inside-work-tree >/dev/null
    git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' >/dev/null 2>&1 || {
        echo '当前分支没有远程跟踪分支，请先配置 upstream。' >&2; exit 1;
    }
    python3 deploy/config_sync.py prepare
    echo '拉取当前分支的最新代码...'
    if git pull --ff-only; then
        python3 deploy/config_sync.py restore
    else
        python3 deploy/config_sync.py restore --failed
        echo '代码更新失败，已恢复本地部署配置；未继续构建或停止服务。请检查网络、本地源码修改或分支分歧。' >&2
        exit 1
    fi
    # Reload the fetched script once, so this deployment uses the updated implementation.
    export _MANGO_DEPLOY_SYNC_ROOT="$ROOT"
    exec sh "$ROOT/deploy.sh" "$@"
fi
unset _MANGO_DEPLOY_SYNC_ROOT
configuration init "$ENV_FILE"
[ -n "$TARGET" ] || TARGET=$(configuration get "$ENV_FILE" DEPLOY_TARGET)
case "$TARGET" in
    compose) configuration render "$ENV_FILE" ;;
    k8s) configuration render-k8s "$ENV_FILE" ;;
    *) echo 'DEPLOY_TARGET 只支持 compose / k8s' >&2; exit 1 ;;
esac
if [ "$PREPARE_ONLY" = 1 ]; then
    echo "已验证 .env.example 并生成 $TARGET 部署配置；已有配置和密码保留。"
    exit 0
fi
if [ "$TARGET" = k8s ]; then
    if [ "$REBUILD" = 1 ]; then echo 'K8s 使用预先构建并发布的镜像，请先构建/推送 .env.example 中的 SERVER_IMAGE 和 CONSOLE_IMAGE。' >&2; exit 1; fi
    exec sh deploy/k8s.sh
fi
docker info >/dev/null
docker compose version >/dev/null
compose() { docker compose --env-file /dev/null -f "$ROOT/deploy/generated/compose.json" "$@"; }
compose config --quiet
DATA_DIR=$(configuration get "$ENV_FILE" MANGO_DATA_DIR)
SERVER_IMAGE=$(configuration get "$ENV_FILE" SERVER_IMAGE)
CONSOLE_IMAGE=$(configuration get "$ENV_FILE" CONSOLE_IMAGE)
mkdir -p "$DATA_DIR/server_runtime/media" "$DATA_DIR/backups"
BUILD_BACKEND=$REBUILD
BUILD_FRONTEND=$REBUILD
if [ "$REBUILD" = 0 ]; then
    BUILD_BACKEND=$(python3 deploy/source_state.py needs-build "$ROOT" backend "$SERVER_IMAGE")
    BUILD_FRONTEND=$(python3 deploy/source_state.py needs-build "$ROOT" frontend "$CONSOLE_IMAGE")
fi
if [ "$BUILD_FRONTEND" = 1 ]; then
    FRONTEND_HEAP=$(python3 deploy/build_resources.py "$(configuration get "$ENV_FILE" NODE_HEAP_MB)")
fi
if [ "$BUILD_BACKEND" = 1 ]; then compose build mango_server; fi
if [ "$BUILD_FRONTEND" = 1 ]; then
    umask 077
    BUILD_LOG="$ROOT/deploy/generated/frontend-build.log"
    if compose build --build-arg NODE_HEAP_MB="$FRONTEND_HEAP" mango-console > "$BUILD_LOG" 2>&1; then
        cat "$BUILD_LOG"
    else
        cat "$BUILD_LOG" >&2
        if grep -Eiq 'heap out of memory|Reached heap limit|exit code: 134' "$BUILD_LOG"; then
            echo '前端构建超过 Node 堆上限：请在 .env.example 增大 NODE_HEAP_MB，并确保主机和 Docker 有足够内存；未执行迁移或停止现有服务。' >&2
        else
            echo '前端镜像构建失败，详情保存在 deploy/generated/frontend-build.log；未执行迁移或停止现有服务。' >&2
        fi
        exit 1
    fi
fi
if [ "$(configuration get "$ENV_FILE" MYSQL_MODE)" = internal ]; then
    compose up -d --wait --wait-timeout 180 db
fi
if [ "$(configuration get "$ENV_FILE" FILE_STORAGE_BACKEND)" = minio ] && [ "$(configuration get "$ENV_FILE" MINIO_MODE)" = internal ]; then
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
PROJECT=$(configuration get "$ENV_FILE" COMPOSE_PROJECT_NAME)
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
python3 deploy/source_state.py record "$ROOT" "$SERVER_IMAGE" "$CONSOLE_IMAGE"
compose ps
echo "平台入口：$(configuration get "$ENV_FILE" PUBLIC_URL)"
echo '初始管理员密码保存在 .env；已有用户密码不会被重置。'
