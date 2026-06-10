#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

COMPOSE="docker compose"
COMPOSE_SERVICES="$($COMPOSE config --services)"

has_service() {
  echo "$COMPOSE_SERVICES" | grep -qx "$1"
}

echo "拉取最新代码..."
BEFORE_REV="$(git rev-parse HEAD)"
git pull
AFTER_REV="$(git rev-parse HEAD)"

BUILD_FRONTEND="${BUILD_FRONTEND:-0}"
FRONTEND_CHANGED=0
if [ "$BEFORE_REV" != "$AFTER_REV" ] && git diff --name-only "$BEFORE_REV" "$AFTER_REV" | grep -q '^mango-console/package.json$'; then
  FRONTEND_CHANGED=1
fi

echo "停止当前芒果业务服务，释放内存..."
$COMPOSE stop mango_gateway mango_server scheduler_service api_worker_1 api_worker_2 mcp_service mango_actuator mango-console || true
TASK_DISPATCHER_CONTAINERS="$(docker ps -aq --filter name=task_dispatcher || true)"
if [ -n "$TASK_DISPATCHER_CONTAINERS" ]; then
  echo "清理旧 task_dispatcher 容器..."
  docker rm -f $TASK_DISPATCHER_CONTAINERS || true
fi

echo "启动基础依赖服务..."
BASE_SERVICES=""
if has_service db; then
  BASE_SERVICES="$BASE_SERVICES db"
fi
if has_service minio; then
  BASE_SERVICES="$BASE_SERVICES minio"
fi
if [ -n "$BASE_SERVICES" ]; then
  $COMPOSE up -d $BASE_SERVICES
else
  echo "未配置 docker-compose 基础依赖服务，跳过。"
fi

echo "构建后端和执行器镜像..."
$COMPOSE build mango_server mango_actuator

echo "执行数据库迁移..."
$COMPOSE run --rm mango_server python manage.py migrate --noinput
$COMPOSE run --rm mango_server python manage.py createcachetable django_cache || true

if [ "$BUILD_FRONTEND" = "1" ] || [ "$FRONTEND_CHANGED" = "1" ] || [ -z "$($COMPOSE images -q mango-console 2>/dev/null || true)" ]; then
  echo "构建前端镜像..."
  $COMPOSE build mango-console
else
  echo "跳过前端镜像构建。如需构建前端，请执行：BUILD_FRONTEND=1 sh start_service.sh"
fi

echo "启动全部芒果服务..."
$COMPOSE up -d --remove-orphans

echo "等待 10 秒，等待全部服务启动完成..."
sleep 10

echo "服务状态："
$COMPOSE ps

echo ""
echo "统一入口："
echo "  前端页面: http://127.0.0.1:8000/"
echo "  API接口:  http://127.0.0.1:8000/api/..."
echo "  MCP服务:  http://127.0.0.1:8000/mcp"

echo ""
echo "关键启动日志："
$COMPOSE logs --tail=120 mango_server scheduler_service api_worker_1 api_worker_2 mcp_service mango_actuator \
  | grep -E "启动：|Application startup complete|Uvicorn running|WebSocket连接成功|握手成功|Applying .* OK" \
  || echo "未找到关键启动日志，请执行：docker compose logs --tail=120 查看完整日志"

echo ""
echo "异常摘要："
$COMPOSE logs --tail=200 mango_gateway mango_server scheduler_service api_worker_1 api_worker_2 mcp_service mango_actuator \
  | grep -v 'GET /api/web/socket' \
  | grep -E "CRITICAL|ERROR|Traceback|Exception|HTTP/[0-9.]+\" 5[0-9][0-9] " \
  || echo "最近日志中未发现关键异常"
