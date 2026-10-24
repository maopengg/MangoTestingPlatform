#!/usr/bin/env sh
# 启动后端、前端和 WebSocket 实时通信服务。
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
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

pids=""

die() {
  echo "启动终止：$*" >&2
  exit 1
}

. "$ROOT_DIR/scripts/local_dev_ports.sh"
. "$ROOT_DIR/scripts/local_dev_dependencies.sh"

print_usage() {
  echo "用途: 启动芒果测试平台核心后端、实时通信服务和前端页面"
  echo "用法: $0 [--env=dev|test] [--backend-port=8000] [--realtime-port=8011] [--frontend-port=5173]"
}

environment_name() {
  case "$ENV_NAME" in
    dev) echo "开发环境（dev）" ;;
    test) echo "测试环境（test）" ;;
    *) echo "$ENV_NAME" ;;
  esac
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
      --realtime-port=*)
        REALTIME_PORT="${1#*=}"
        shift
        ;;
      --realtime-port)
        [ "$#" -ge 2 ] || die "--realtime-port 需要指定端口"
        REALTIME_PORT="$2"
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
    "import django, rest_framework, channels, mangotools"
  ensure_frontend_dependencies "$CONSOLE_DIR"
}

cleanup_ports() {
  cleanup_port "后端" "$BACKEND_PORT" "[m]anage.py runserver .*:$BACKEND_PORT"
  cleanup_port "实时服务" "$REALTIME_PORT" "[m]anage.py run_realtime_service .*--port $REALTIME_PORT"
  cleanup_port "前端" "$FRONTEND_PORT" "[v]ite .*--port $FRONTEND_PORT"
}

confirm_test_env_start() {
  if [ "$ENV_NAME" != "test" ]; then
    return
  fi
  echo "即将启动 test 环境本地开发服务。"
  echo "test 环境连接共享测试数据，启动前请确认不会影响其他人。"
  read -r -p "请输入 确认启动test 继续启动：" confirm_text
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
    exec "$@"
  ) > "$log_file" 2>&1 &
  pid=$!
  pids="$pids $pid"
  printf '%s：进程号=%s，日志=%s\n' "$display_name" "$pid" "$log_file"
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
check_local_env
confirm_test_env_start
cleanup_ports
mkdir -p "$LOG_DIR"
trap shutdown INT TERM EXIT

echo "启动芒果测试平台（基础本地开发服务）"
echo "运行环境：       $(environment_name)"
echo "核心后端地址：   http://127.0.0.1:$BACKEND_PORT/"
echo "实时通信地址：   ws://127.0.0.1:$REALTIME_PORT/"
echo "前端页面地址：   http://127.0.0.1:$FRONTEND_PORT/"
echo "代码热更新：     后端和前端均已启用"
echo "服务日志目录：   $LOG_DIR"
echo

start_service core-api "芒果测试平台核心后端服务" "$SERVER_DIR" \
  env MANGO_SERVICE_NAME=core-api MANGO_SERVICE_INSTANCE=core-api-1 \
  "$PYTHON_BIN" manage.py runserver "$BACKEND_HOST:$BACKEND_PORT" "--env=$ENV_NAME"

start_service realtime-service "芒果测试平台实时通信服务" "$SERVER_DIR" \
  env MANGO_SERVICE_NAME=realtime-service MANGO_SERVICE_INSTANCE=realtime-1 \
  "$PYTHON_BIN" manage.py run_realtime_service "--env=$ENV_NAME" --host "$BACKEND_HOST" --port "$REALTIME_PORT" --workers 1

start_service web "芒果测试平台前端页面" "$CONSOLE_DIR" \
  env MANGO_VITE_AUTO_OPEN=false npm run dev -- --port "$FRONTEND_PORT"

echo
echo "芒果测试平台基础本地开发服务已全部启动，按 Ctrl+C 停止。"
echo "查看全部服务日志：tail -f $LOG_DIR/*.log"

wait
