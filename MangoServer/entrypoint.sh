#!/bin/sh
set -e
set -x  # 打印每一步，便于排查

# 确保数据库可用，migrate 失败则重试
for i in $(seq 1 30); do
  if python manage.py migrate --noinput; then
    break
  fi
  echo "migrate 重试 $i/30 ..."
  sleep 2
done

# 缓存表已存在时允许继续
python manage.py createcachetable django_cache || true

# 交给 uvicorn 启动 Django ASGI
exec python start_server.py

