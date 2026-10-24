#!/usr/bin/env sh
# 启动 MCP 服务。
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_DIR="$ROOT_DIR/MangoServer"
PYTHON_BIN="${PYTHON_BIN:-}"

ENV_NAME="${ENV_NAME:-dev}"
MCP_HOST="${MCP_HOST:-127.0.0.1}"
MCP_PORT="${MCP_PORT:-8010}"
MCP_WORKERS="${MCP_WORKERS:-1}"

die() {
  echo "启动终止：$*" >&2
  exit 1
}

. "$ROOT_DIR/scripts/local_dev_ports.sh"
. "$ROOT_DIR/scripts/local_dev_dependencies.sh"

print_usage() {
  echo "用途: 启动芒果测试平台 MCP 服务，为 AI 助手提供平台工具接口"
  echo "用法: $0 [--env=test|dev|master] [--host=127.0.0.1] [--port=8010] [--workers=1]"
}

environment_name() {
  case "$ENV_NAME" in
    dev) echo "开发环境（dev）" ;;
    test) echo "测试环境（test）" ;;
    master) echo "生产环境（master）" ;;
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
        [ "$#" -ge 2 ] || die "--env 需要指定环境，例如 --env=test"
        ENV_NAME="$2"
        shift 2
        ;;
      --host=*)
        MCP_HOST="${1#*=}"
        shift
        ;;
      --host)
        [ "$#" -ge 2 ] || die "--host 需要指定监听地址"
        MCP_HOST="$2"
        shift 2
        ;;
      --port=*)
        MCP_PORT="${1#*=}"
        shift
        ;;
      --port)
        [ "$#" -ge 2 ] || die "--port 需要指定端口"
        MCP_PORT="$2"
        shift 2
        ;;
      --workers=*)
        MCP_WORKERS="${1#*=}"
        shift
        ;;
      --workers)
        [ "$#" -ge 2 ] || die "--workers 需要指定进程数"
        MCP_WORKERS="$2"
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
    "芒果测试平台 MCP 服务" \
    "$SERVER_DIR" \
    "import django, mcp, fastmcp, mangotools"
}

parse_args "$@"
check_local_env
cleanup_port "芒果测试平台 MCP 服务" "$MCP_PORT" "[m]anage.py run_mcp_service .*--port $MCP_PORT"

cd "$SERVER_DIR"

echo "启动芒果测试平台 MCP 服务"
echo "用途：     为 AI 助手提供芒果测试平台工具接口"
echo "运行环境： $(environment_name)"
echo "服务地址： http://$MCP_HOST:$MCP_PORT/mcp"
echo "进程数量： $MCP_WORKERS"
echo

exec env \
  MANGO_SERVICE_NAME=mcp-service \
  MANGO_SERVICE_INSTANCE=mcp-1 \
  MANGO_MCP_ALLOWED_HOSTS="${MANGO_MCP_ALLOWED_HOSTS:-127.0.0.1:*,localhost:*,[::1]:*}" \
  MANGO_MCP_ALLOWED_ORIGINS="${MANGO_MCP_ALLOWED_ORIGINS:-http://127.0.0.1:*,http://localhost:*,http://[::1]:*}" \
  "$PYTHON_BIN" manage.py run_mcp_service "--env=$ENV_NAME" --host "$MCP_HOST" --port "$MCP_PORT" --workers "$MCP_WORKERS"
