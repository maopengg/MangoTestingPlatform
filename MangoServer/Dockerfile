# 使用 Ubuntu 作为基础镜像
FROM ubuntu/python:3.10-22.04_stable AS builder

# 设置工作目录
WORKDIR /app

# 更新包管理器并安装依赖
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    linux-headers-generic \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY . .


FROM ubuntu/python:3.10-22.04_stable
WORKDIR /app
COPY --from=builder /root/.local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app
EXPOSE 8000
ARG DJANGO_ENV
ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=${DJANGO_ENV}"]