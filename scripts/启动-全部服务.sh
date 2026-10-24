#!/usr/bin/env sh
# 启动后端、前端、WebSocket、MCP、监控和 API 任务执行服务，不启动定时调度。
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_DIR="$ROOT_DIR/MangoServer"
CONSOLE_DIR="$ROOT_DIR/mango-console"
PYTHON_BIN="${PYTHON_BIN:-}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs/local-dev}"

ENV_NAME="${ENV_NAME:-dev}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
REALTIME_PORT="${REALTIME_PORT:-8011}"
MCP_PORT="${MCP_PORT:-8010}"
MCP_WORKERS="${MCP_WORKERS:-1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
API_WORKER_NAME="${API_WORKER_NAME:-api-worker-1}"
API_WORKER_THREAD_POOL_SIZE="${API_WORKER_THREAD_POOL_SIZE:-5}"
API_WORKER_DB_IDLE_SECONDS="${API_WORKER_DB_IDLE_SECONDS:-1800}"

pids=""

die() {
  echo "启动终止：$*" >&2
  exit 1
}

. "$ROOT_DIR/scripts/local_dev_ports.sh"
. "$ROOT_DIR/scripts/local_dev_dependencies.sh"

print_usage() {
  echo "用途: 启动芒果测试平台本地服务（后端、实时通信、MCP、监控、API任务执行器和前端，不含定时调度）"
  echo "用法: $0 [--env=dev|test] [--backend-port=8000] [--frontend-port=5173]"
}

environment_name() {
  case "$ENV_NAME" in
    dev) echo "开发环境（dev）" ;;
    test) echo "测试环境（test）" ;;
    *) echo "$ENV_NAME" ;;
  esac
}

show_full_stack_warning() {
  echo
  echo "==================== 重要提示 ===================="
  echo "该脚本会启动后端、前端、实时通信、MCP、监控和 API 任务执行服务，不启动定时调度服务。"
  echo "启动后可能消费待执行任务，并占用较多本机资源。"
  echo "日常前后端开发请优先使用：scripts/启动-后端+前端+WebSocket服务.sh"
  echo "=================================================="
  echo
}

confirm_full_stack_start() {
  printf '请输入“确认启动全部服务”继续：'
  if ! read -r confirm_text; then
    die "未收到启动确认，已取消启动全部服务。"
  fi
  [ "$confirm_text" = "确认启动全部服务" ] || die "确认内容不正确，已取消启动全部服务。"
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --env=*)
        ENV_NAME="${1#*=}"
        shift
        ;;
      --env)
        [ "$#" -ge 2 ] || die "--env 需要指定环境，例如 --env=dev"
        ENV_NAME="$2"
        shift 2
        ;;
      --backend-port=*)
        BACKEND_PORT="${1#*=}"
        shift
        ;;
      --backend-port)
        [ "$#" -ge 2 ] || die "--backend-port 需要指定端口"
        BACKEND_PORT="$2"
        shift 2
        ;;
      --frontend-port=*)
        FRONTEND_PORT="${1#*=}"
        shift
        ;;
      --frontend-port)
        [ "$#" -ge 2 ] || die "--frontend-port 需要指定端口"
        FRONTEND_PORT="$2"
        shift 2
        ;;
      -h|--help)
        print_usage
        exit 0
        ;;
      *)
        die "未知参数：$1"
        ;;
    esac
  done
}

check_local_env() {
  ensure_python_environment \
    "芒果测试平台后端" \
    "$SERVER_DIR" \
    "import django, rest_framework, channels, mcp, fastmcp, mangotools"
  ensure_frontend_dependencies "$CONSOLE_DIR"
}

cleanup_ports() {
  cleanup_port "后端" "$BACKEND_PORT" "[m]anage.py runserver .*:$BACKEND_PORT"
  cleanup_port "实时服务" "$REALTIME_PORT" "[m]anage.py run_realtime_service .*--port $REALTIME_PORT"
  cleanup_port "MCP 服务" "$MCP_PORT" "[m]anage.py run_mcp_service .*--port $MCP_PORT"
  cleanup_port "前端" "$FRONTEND_PORT" "[v]ite .*--port $FRONTEND_PORT"
}

confirm_test_env_start() {
  if [ "$ENV_NAME" != "test" ]; then
    return
  fi
  echo "即将启动 test 环境完整本地开发栈。"
  echo "API任务执行服务会消费任务数据，可能影响共享测试环境；本脚本不启动定时调度服务。"
  printf '请输入 确认启动test 继续启动：'
  read -r confirm_text
  [ "$confirm_text" = "确认启动test" ] || die "未确认启动 test 环境。"
}

start_service() {
  service_key="$1"
  display_name="$2"
  workdir="$3"
  shift 3
  log_file="$LOG_DIR/$service_key.log"
  : > "$log_file"
  (
    cd "$workdir"
    "$@"
  ) > "$log_file" 2>&1 &
  pid=$!
  pids="$pids $pid"
  printf '%s：进程号=%s，日志=%s\n' "$display_name" "$pid" "$log_file"
}

run_reloadable_server_command() {
  service_key="$1"
  display_name="$2"
  shift 2
  stamp_file="$LOG_DIR/.$service_key.reload.stamp"
  child_pid=""

  trap 'if [ -n "$child_pid" ] && kill -0 "$child_pid" 2>/dev/null; then
      kill "$child_pid" 2>/dev/null || true
      wait "$child_pid" 2>/dev/null || true
    fi
    exit 0' INT TERM
  touch "$stamp_file"

  while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动：${display_name}"
    "$@" &
    child_pid=$!

    while kill -0 "$child_pid" 2>/dev/null; do
      if find "$SERVER_DIR/src" "$SERVER_DIR/manage.py" -type f -name '*.py' -newer "$stamp_file" -print -quit | grep -q .; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 检测到后端代码变化，重启：${display_name}"
        touch "$stamp_file"
        kill "$child_pid" 2>/dev/null || true
        wait "$child_pid" 2>/dev/null || true
        child_pid=""
        break
      fi
      sleep 1
    done

    if [ -n "$child_pid" ]; then
      wait "$child_pid" 2>/dev/null || true
      child_pid=""
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${display_name} 已退出，1 秒后重新启动"
    fi
    sleep 1
  done
}

shutdown() {
  trap - INT TERM EXIT
  echo
  echo "正在停止本地服务..."
  if [ -z "$pids" ]; then
    return
  fi
  for pid in $pids; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
    wait "$pid" 2>/dev/null || true
  done
}

parse_args "$@"
show_full_stack_warning
confirm_full_stack_start
check_local_env
confirm_test_env_start
cleanup_ports
mkdir -p "$LOG_DIR"
trap shutdown INT TERM EXIT

echo "启动芒果测试平台（完整本地服务）"
echo "运行环境：             $(environment_name)"
echo "核心后端地址：         http://127.0.0.1:$BACKEND_PORT/"
echo "实时通信地址：         ws://127.0.0.1:$REALTIME_PORT/"
echo "MCP 服务地址：         http://127.0.0.1:$MCP_PORT/mcp"
echo "前端页面地址：         http://127.0.0.1:$FRONTEND_PORT/"
echo "定时调度服务：         不启动"
echo "API任务执行器名称：    $API_WORKER_NAME"
echo "代码热更新：           所有本地开发服务均已启用"
echo "服务日志目录：         $LOG_DIR"
echo

echo "正在初始化芒果测试平台系统数据..."
(
  cd "$SERVER_DIR"
  "$PYTHON_BIN" manage.py init_system_data "--env=$ENV_NAME"
)

start_service core-api "芒果测试平台核心后端服务" "$SERVER_DIR" \
  env MANGO_SERVICE_NAME=core-api MANGO_SERVICE_INSTANCE=core-api-1 \
  "$PYTHON_BIN" manage.py runserver "$BACKEND_HOST:$BACKEND_PORT" "--env=$ENV_NAME"

start_service realtime-service "芒果测试平台实时通信服务" "$SERVER_DIR" \
  run_reloadable_server_command realtime-service "芒果测试平台实时通信服务" \
  env MANGO_SERVICE_NAME=realtime-service MANGO_SERVICE_INSTANCE=realtime-1 \
  "$PYTHON_BIN" manage.py run_realtime_service "--env=$ENV_NAME" --host "$BACKEND_HOST" --port "$REALTIME_PORT" --workers 1

start_service mcp-service "芒果测试平台 MCP 服务" "$SERVER_DIR" \
  run_reloadable_server_command mcp-service "芒果测试平台 MCP 服务" \
  env MANGO_SERVICE_NAME=mcp-service MANGO_SERVICE_INSTANCE=mcp-1 \
  MANGO_MCP_ALLOWED_HOSTS="${MANGO_MCP_ALLOWED_HOSTS:-127.0.0.1:*,localhost:*,[::1]:*}" \
  MANGO_MCP_ALLOWED_ORIGINS="${MANGO_MCP_ALLOWED_ORIGINS:-http://127.0.0.1:*,http://localhost:*,http://[::1]:*}" \
  "$PYTHON_BIN" manage.py run_mcp_service "--env=$ENV_NAME" --host 127.0.0.1 --port "$MCP_PORT" --workers "$MCP_WORKERS"

start_service monitoring-service "芒果测试平台监控服务" "$SERVER_DIR" \
  run_reloadable_server_command monitoring-service "芒果测试平台监控服务" \
  env MANGO_SERVICE_NAME=monitoring-service MANGO_SERVICE_INSTANCE=monitoring-1 \
  "$PYTHON_BIN" manage.py run_monitoring_service "--env=$ENV_NAME" --instance-name monitoring-1 --poll-interval 2

start_service api-worker "芒果测试平台API任务执行服务" "$SERVER_DIR" \
  run_reloadable_server_command api-worker "芒果测试平台API任务执行服务" \
  env MANGO_SERVICE_NAME=api-worker MANGO_SERVICE_INSTANCE="$API_WORKER_NAME" \
  "$PYTHON_BIN" manage.py run_api_worker "--env=$ENV_NAME" --worker-name "$API_WORKER_NAME" --thread-pool-size "$API_WORKER_THREAD_POOL_SIZE" --db-idle-seconds "$API_WORKER_DB_IDLE_SECONDS"

start_service web "芒果测试平台前端页面" "$CONSOLE_DIR" \
  env MANGO_VITE_AUTO_OPEN=false npm run dev -- --port "$FRONTEND_PORT" --strictPort

echo
echo "芒果测试平台完整本地服务已全部启动，按 Ctrl+C 停止。"
echo "查看全部服务日志：tail -f $LOG_DIR/*.log"

wait
