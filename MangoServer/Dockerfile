FROM python:3.10-slim AS builder
WORKDIR /app
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libpython3.10-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY . .

FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /root/.local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app
EXPOSE 8000
ARG DJANGO_ENV
ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=${DJANGO_ENV}"]