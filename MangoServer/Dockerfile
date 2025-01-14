# 第一阶段：构建阶段
FROM python:3.10.16-alpine AS builder
WORKDIR /app

# 使用阿里云镜像源
RUN echo "http://mirrors.aliyun.com/alpine/v3.21/main" > /etc/apk/repositories && \
    echo "http://mirrors.aliyun.com/alpine/v3.21/community" >> /etc/apk/repositories

# 安装编译工具和依赖
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers g++

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

# 复制应用程序代码
COPY . .

# 第二阶段：生产阶段
FROM python:3.10.16-alpine
WORKDIR /app

# 使用阿里云镜像源
RUN echo "http://mirrors.aliyun.com/alpine/v3.21/main" > /etc/apk/repositories && \
    echo "http://mirrors.aliyun.com/alpine/v3.21/community" >> /etc/apk/repositories

# 安装运行时依赖
RUN apk add --no-cache g++

# 从构建阶段复制应用程序代码和依赖
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV DJANGO_SETTINGS_MODULE=PyAutoTest.settings

# 启动 Django 应用
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=prod"]