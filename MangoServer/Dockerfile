FROM python:3.10-slim-bullseye
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
COPY . .

EXPOSE 8000
ARG DJANGO_ENV

ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
RUN echo "构建后端服务：$DJANGO_ENV"

CMD ["sh", "-c", "uvicorn src.asgi:application --host ${UVICORN_HOST:-0.0.0.0} --port ${UVICORN_PORT:-8000} --workers ${UVICORN_WORKERS:-1} --log-level ${UVICORN_LOG_LEVEL:-info}"]
