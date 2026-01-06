#!/bin/sh
set -e
python manage.py migrate --noinput

python manage.py createcachetable django_cache || true

exec python start_server.py

