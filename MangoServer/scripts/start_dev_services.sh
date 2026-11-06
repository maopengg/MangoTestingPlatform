#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
ENV_NAME="${ENV_NAME:-dev}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs/dev-services}"

CORE_API_HOST="${CORE_API_HOST:-127.0.0.1}"
CORE_API_PORT="${CORE_API_PORT:-8000}"
REALTIME_HOST="${REALTIME_HOST:-0.0.0.0}"
REALTIME_PORT="${REALTIME_PORT:-8011}"
SCHEDULER_NODE="${SCHEDULER_NODE:-scheduler-1}"
SCHEDULER_DISPATCH_BATCH_SIZE="${SCHEDULER_DISPATCH_BATCH_SIZE:-50}"
API_WORKER_COUNT="${API_WORKER_COUNT:-2}"
API_WORKER_THREAD_POOL_SIZE="${API_WORKER_THREAD_POOL_SIZE:-5}"
API_WORKER_DB_IDLE_SECONDS="${API_WORKER_DB_IDLE_SECONDS:-1800}"
MCP_HOST="${MCP_HOST:-0.0.0.0}"
MCP_PORT="${MCP_PORT:-8010}"
MCP_WORKERS="${MCP_WORKERS:-1}"
START_MCP="${START_MCP:-1}"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

pids=()

start_service() {
  local name="$1"
  shift
  local log_file="$LOG_DIR/$name.log"
  : > "$log_file"
  "$@" > "$log_file" 2>&1 &
  local pid=$!
  pids+=("$pid")
  printf '%-16s pid=%s log=%s\n' "$name" "$pid" "$log_file"
}

shutdown() {
  echo
  echo "Stopping MangoServer services..."
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait || true
}

trap shutdown INT TERM EXIT

echo "Starting MangoServer services..."
echo "core-api:    http://$CORE_API_HOST:$CORE_API_PORT/"
echo "realtime:    ws://$REALTIME_HOST:$REALTIME_PORT/"
echo "mcp-service: http://$MCP_HOST:$MCP_PORT/  START_MCP=$START_MCP MCP_WORKERS=$MCP_WORKERS"
echo

if ! "$PYTHON_BIN" -c 'import greenlet, httpx; from redis._parsers.resp2 import _RESP2Parser'; then
  echo '后端依赖不完整，请先使用当前虚拟环境安装 requirements/dev.txt 和 requirements/local.txt；未启动服务。' >&2
  exit 1
fi
echo "Initializing system data..."
"$PYTHON_BIN" manage.py init_system_data "--env=$ENV_NAME"

start_service core-api \
  env MANGO_SERVICE_NAME=core-api MANGO_SERVICE_INSTANCE=core-api-1 \
  "$PYTHON_BIN" manage.py runserver "$CORE_API_HOST:$CORE_API_PORT" "--env=$ENV_NAME"

start_service realtime-service \
  env MANGO_SERVICE_NAME=realtime-service MANGO_SERVICE_INSTANCE=realtime-1 \
  "$PYTHON_BIN" manage.py run_realtime_service "--env=$ENV_NAME" --host "$REALTIME_HOST" --port "$REALTIME_PORT" --workers 1

scheduler_args=(--node-name "$SCHEDULER_NODE" --dispatch-batch-size "$SCHEDULER_DISPATCH_BATCH_SIZE")
if [[ "$ENV_NAME" == "dev" || "$ENV_NAME" == "dev1" ]]; then
  echo "scheduler-service 仅执行清理：dev 环境不自动执行定时业务任务"
  scheduler_args+=(--cleanup-only)
fi
start_service scheduler-service \
  env MANGO_SERVICE_NAME=scheduler-service MANGO_SERVICE_INSTANCE="$SCHEDULER_NODE" \
  "$PYTHON_BIN" manage.py run_scheduler "--env=$ENV_NAME" "${scheduler_args[@]}"

start_service monitoring-service \
  env MANGO_SERVICE_NAME=monitoring-service MANGO_SERVICE_INSTANCE=monitoring-1 \
  "$PYTHON_BIN" manage.py run_monitoring_service "--env=$ENV_NAME" --instance-name monitoring-1 --poll-interval 2

for worker_index in $(seq 1 "$API_WORKER_COUNT"); do
  api_worker_name="api-worker-$worker_index"
  start_service "$api_worker_name" \
    env MANGO_SERVICE_NAME=api-worker MANGO_SERVICE_INSTANCE="$api_worker_name" \
    "$PYTHON_BIN" manage.py run_api_worker "--env=$ENV_NAME" --worker-name "$api_worker_name" --thread-pool-size "$API_WORKER_THREAD_POOL_SIZE" --db-idle-seconds "$API_WORKER_DB_IDLE_SECONDS"
done

if [[ "$START_MCP" == "1" || "$START_MCP" == "true" || "$START_MCP" == "yes" ]]; then
  start_service mcp-service \
    env MANGO_SERVICE_NAME=mcp-service MANGO_SERVICE_INSTANCE=mcp-1 \
    "$PYTHON_BIN" manage.py run_mcp_service "--env=$ENV_NAME" --host "$MCP_HOST" --port "$MCP_PORT" --workers "$MCP_WORKERS"
fi

echo
echo "All services started. Press Ctrl-C to stop."
echo "View logs: tail -f $LOG_DIR/*.log"

wait
