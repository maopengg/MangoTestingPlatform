#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
ENV_NAME="${ENV_NAME:-dev}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs/dev-services}"

CORE_API_HOST="${CORE_API_HOST:-127.0.0.1}"
CORE_API_PORT="${CORE_API_PORT:-8000}"
SCHEDULER_NODE="${SCHEDULER_NODE:-scheduler-1}"
DISPATCHER_NODE="${DISPATCHER_NODE:-dispatcher-1}"
API_WORKER_COUNT="${API_WORKER_COUNT:-2}"
API_WORKER_CONCURRENCY="${API_WORKER_CONCURRENCY:-5}"
API_WORKER_DB_IDLE_SECONDS="${API_WORKER_DB_IDLE_SECONDS:-1800}"
MCP_HOST="${MCP_HOST:-0.0.0.0}"
MCP_PORT="${MCP_PORT:-8010}"
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
echo "mcp-service: http://$MCP_HOST:$MCP_PORT/  START_MCP=$START_MCP"
echo

start_service core-api \
  "$PYTHON_BIN" manage.py runserver "$CORE_API_HOST:$CORE_API_PORT" "--env=$ENV_NAME"

start_service scheduler-service \
  "$PYTHON_BIN" manage.py run_scheduler "--env=$ENV_NAME" --node-name "$SCHEDULER_NODE"

start_service task-dispatcher \
  "$PYTHON_BIN" manage.py run_dispatcher "--env=$ENV_NAME" --node-name "$DISPATCHER_NODE"

for worker_index in $(seq 1 "$API_WORKER_COUNT"); do
  api_worker_name="api-worker-$worker_index"
  start_service "$api_worker_name" \
    "$PYTHON_BIN" manage.py run_api_worker "--env=$ENV_NAME" --worker-name "$api_worker_name" --concurrency "$API_WORKER_CONCURRENCY" --db-idle-seconds "$API_WORKER_DB_IDLE_SECONDS"
done

if [[ "$START_MCP" == "1" || "$START_MCP" == "true" || "$START_MCP" == "yes" ]]; then
  start_service mcp-service \
    "$PYTHON_BIN" manage.py run_mcp_service "--env=$ENV_NAME" --host "$MCP_HOST" --port "$MCP_PORT"
fi

echo
echo "All services started. Press Ctrl-C to stop."
echo "View logs: tail -f $LOG_DIR/*.log"

wait
