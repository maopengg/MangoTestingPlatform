# 使用 Python 官方镜像作为构建阶段的基础镜像
FROM python:3.10.16-slim AS builder

# 设置工作目录
WORKDIR /app

# 替换为阿里云的 Debian 镜像源
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt -i https://pypi.org/simple

# 复制应用程序代码
COPY . .

# 使用 Python 官方镜像作为运行时镜像
FROM python:3.10.16-slim

# 设置工作目录
WORKDIR /app

# 从构建阶段复制已安装的 Python 包
COPY --from=builder /root/.local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# 从构建阶段复制应用程序代码
COPY --from=builder /app /app

# 暴露端口
EXPOSE 8000

# 设置环境变量
ARG DJANGO_ENV
ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}

# 运行 Django 开发服务器
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=${DJANGO_ENV}"]