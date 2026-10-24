#!/usr/bin/env sh

python_version_supported() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

find_python_command() {
  for command_name in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$command_name" >/dev/null 2>&1 && python_version_supported "$command_name"; then
      command -v "$command_name"
      return 0
    fi
  done
  return 1
}

install_python_dependencies() {
  project_name="$1"
  project_dir="$2"
  python_bin="$3"

  echo "$project_name Python 依赖不完整，正在自动安装..."
  (
    cd "$project_dir"
    requirements_file="requirements/dev.txt"
    local_requirements_file="requirements/local.txt"
    if [ -f requirements/desktop.txt ]; then
      requirements_file="requirements/desktop.txt"
      local_requirements_file="requirements/desktop-local.txt"
    fi
    "$python_bin" -m pip install -r "$requirements_file"
    if [ -f "$local_requirements_file" ]; then
      "$python_bin" -m pip install -r "$local_requirements_file"
    fi
  ) || die "$project_name Python 依赖安装失败，请检查网络、依赖文件和本地安装包。"
}

ensure_python_environment() {
  project_name="$1"
  project_dir="$2"
  import_check="$3"
  configured_python="${PYTHON_BIN:-}"
  project_python="$project_dir/.venv/bin/python"

  if [ -n "$configured_python" ]; then
    if [ -x "$configured_python" ]; then
      PYTHON_BIN="$configured_python"
    elif command -v "$configured_python" >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "$configured_python")"
    else
      die "$project_name 指定的 Python 不可执行：$configured_python"
    fi
  elif [ -x "$project_python" ]; then
    PYTHON_BIN="$project_python"
  else
    bootstrap_python="$(find_python_command || true)"
    [ -n "$bootstrap_python" ] || die "$project_name 未找到 Python 3.10 或更高版本，请先安装 Python。"
    echo "$project_name 未检测到独立虚拟环境，正在使用 $bootstrap_python 创建 $project_dir/.venv ..."
    "$bootstrap_python" -m venv "$project_dir/.venv" || die "$project_name 虚拟环境创建失败，请检查 Python venv 组件。"
    PYTHON_BIN="$project_python"
  fi

  python_version_supported "$PYTHON_BIN" || die "$project_name 需要 Python 3.10 或更高版本：$PYTHON_BIN"
  if ! "$PYTHON_BIN" -c "$import_check" >/dev/null 2>&1; then
    install_python_dependencies "$project_name" "$project_dir" "$PYTHON_BIN"
  fi
  "$PYTHON_BIN" -c "$import_check" >/dev/null 2>&1 || die "$project_name Python 依赖校验失败，请检查依赖安装日志。"
  echo "$project_name Python 环境已就绪：$PYTHON_BIN"
}

ensure_frontend_dependencies() {
  project_dir="$1"
  command -v node >/dev/null 2>&1 || die "未找到 Node.js，请先安装 Node.js。"
  command -v npm >/dev/null 2>&1 || die "未找到 npm，请先安装 npm。"
  node -e 'const major = Number(process.versions.node.split(".")[0]); process.exit(major >= 16 ? 0 : 1)' \
    >/dev/null 2>&1 || die "芒果测试平台前端需要 Node.js 16 或更高版本。"

  if [ ! -x "$project_dir/node_modules/.bin/vite" ]; then
    echo "芒果测试平台前端依赖未安装，正在自动安装..."
    (
      cd "$project_dir"
      if [ -f package-lock.json ]; then
        npm ci
      else
        npm install
      fi
    ) || die "芒果测试平台前端依赖安装失败，请检查 Node.js 版本、网络和 npm 配置。"
  fi

  [ -x "$project_dir/node_modules/.bin/vite" ] || die "芒果测试平台前端依赖校验失败：未找到 Vite。"
  echo "芒果测试平台前端依赖已就绪。"
}
