ARG PYTHON_IMAGE=python:3.10.19-slim-bookworm
FROM ${PYTHON_IMAGE}
WORKDIR /app

COPY MangoServer/requirements ./requirements
COPY MangoServer/local_packages ./local_packages
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
RUN pip install --no-cache-dir -r requirements/master.txt -i ${PIP_INDEX_URL}
RUN pip install --no-cache-dir --force-reinstall -r requirements/local.txt -i ${PIP_INDEX_URL}
COPY MangoServer/ .
COPY skill/ ./skill/

EXPOSE 8000
ARG DJANGO_ENV

ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
RUN echo "构建后端服务：$DJANGO_ENV"

CMD ["sh", "-c", "if [ \"${DJANGO_ENV:-master}\" = \"dev\" ]; then access_log_flag=''; else access_log_flag='--no-access-log'; fi; exec uvicorn src.asgi:application --host ${UVICORN_HOST:-0.0.0.0} --port ${UVICORN_PORT:-8000} --workers ${UVICORN_WORKERS:-1} --log-level ${UVICORN_LOG_LEVEL:-info} ${access_log_flag}"]
