port_available() {
  port="$1"
  "$PYTHON_BIN" - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("0.0.0.0", port))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
PY
}

port_owner_lines() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | tail -n +2 || true
}

port_owner_pids() {
  lsof -nP -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | sort -u || true
}

pattern_pids() {
  pattern="$1"
  [ -n "$pattern" ] || return
  pgrep -f "$pattern" 2>/dev/null | sort -u || true
}

child_pids() {
  pid="$1"
  children="$(pgrep -P "$pid" 2>/dev/null || true)"
  for child in $children; do
    echo "$child"
    child_pids "$child"
  done
}

related_pids() {
  port="$1"
  pattern="${2:-}"
  {
    port_owner_pids "$port"
    if [ -n "$pattern" ]; then
      pattern_pids "$pattern"
    fi
  } | sort -u | while read -r pid; do
    [ -n "$pid" ] || continue
    echo "$pid"
    child_pids "$pid"
  done | sort -u
}

wait_port_release() {
  port="$1"
  seconds="${2:-5}"
  count=0
  while [ "$count" -lt "$seconds" ]; do
    if port_available "$port"; then
      return 0
    fi
    count=$((count + 1))
    sleep 1
  done
  port_available "$port"
}

wait_pids_exit() {
  pids="$1"
  seconds="${2:-5}"
  count=0
  while [ "$count" -lt "$seconds" ]; do
    alive=""
    for pid in $pids; do
      if kill -0 "$pid" 2>/dev/null; then
        alive="$alive $pid"
      fi
    done
    [ -z "$alive" ] && return 0
    count=$((count + 1))
    sleep 1
  done
  return 1
}

cleanup_port() {
  service_name="$1"
  port="$2"
  pattern="${3:-}"
  pids="$(related_pids "$port" "$pattern")"
  if port_available "$port" && [ -z "$pids" ]; then
    return
  fi

  owner="$(port_owner_lines "$port")"
  if [ -z "$pids" ]; then
    [ -n "$owner" ] || owner="端口已被占用，但未能读取占用进程"
    die "$service_name 端口 $port 已被占用，无法自动清理：\n$owner"
  fi

  echo "$service_name 端口 $port 已存在旧进程，正在自动清理："
  if [ -n "$owner" ]; then
    echo "$owner"
  else
    ps -p $pids -o pid=,ppid=,command= 2>/dev/null || true
  fi

  for pid in $pids; do
    kill "$pid" 2>/dev/null || true
  done
  if wait_pids_exit "$pids" 5 && wait_port_release "$port" 5; then
    echo "$service_name 端口 $port 已释放。"
    return
  fi

  echo "$service_name 端口 $port 未正常释放，执行强制清理。"
  for pid in $pids; do
    kill -9 "$pid" 2>/dev/null || true
  done
  wait_pids_exit "$pids" 5 || true
  wait_port_release "$port" 5 || die "$service_name 端口 $port 清理失败，请手动检查：\n$(port_owner_lines "$port")"
  echo "$service_name 端口 $port 已释放。"
}
