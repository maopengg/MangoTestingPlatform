#!/bin/sh
set -eu

# 默认跟随项目 .npmrc；部署时仍允许显式指定内部镜像源。
if [ -n "${NPM_REGISTRY:-}" ]; then
  export npm_config_registry="$NPM_REGISTRY"
fi

run_timed() {
  stage=$1
  shift
  started_at=$(date +%s)
  printf '%s开始\n' "$stage"
  if "$@"; then
    result=0
  else
    result=$?
  fi
  finished_at=$(date +%s)
  printf '%s耗时：%s 秒（退出码 %s）\n' "$stage" "$((finished_at - started_at))" "$result"
  return "$result"
}

install_dependencies() {
  if [ -f node_modules/.package-lock.json ] && [ -x node_modules/.bin/vite ]; then
    printf '复用 node_modules 缓存\n'
  else
    printf '安装依赖，优先复用 npm 下载缓存\n'
    npm ci --cache .npm --prefer-offline --no-audit --no-fund --timing
  fi
}

case "${1:-all}" in
  install) run_timed '依赖准备（缓存检查/安装）' install_dependencies ;;
  build) run_timed '前端打包' npm run "build:${2:-dev}" ;;
  all)
    run_timed '依赖准备（缓存检查/安装）' install_dependencies
    run_timed '前端打包' npm run "build:${2:-dev}"
    ;;
  *) printf '用法：sh scripts/ci-console-build.sh [install|build|all] [环境]\n' >&2; exit 2 ;;
esac
