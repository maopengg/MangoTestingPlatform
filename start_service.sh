#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

COMPOSE="docker compose"

echo "启动数据库和对象存储..."
$COMPOSE up -d db minio

echo "执行数据库迁移..."
$COMPOSE run --rm mango_server python manage.py migrate --noinput
$COMPOSE run --rm mango_server python manage.py createcachetable django_cache || true

echo "启动全部芒果服务..."
$COMPOSE up -d --build

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
echo "最近服务日志："
$COMPOSE logs --tail=80 mango_gateway mango_server scheduler_service task_dispatcher api_worker_1 api_worker_2 mcp_service mango_actuator
