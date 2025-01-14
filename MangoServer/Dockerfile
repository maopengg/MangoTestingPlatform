#FROM python:3.10.16-alpine AS builder
#WORKDIR /app
#COPY . /app/
#RUN apk add --no-cache gcc musl-dev python3-dev linux-headers && \
#    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
#
#FROM python:3.10.16-alpine
#WORKDIR /app
#COPY --from=builder /app /app
#COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
#EXPOSE 8000
#ENV DJANGO_SETTINGS_MODULE=PyAutoTest.settings
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=prod"]
# 使用 Alpine Linux 作为构建阶段的基础镜像
FROM python:3.10.16-alpine AS builder

# 设置工作目录
WORKDIR /app

# 设置 Alpine 国内镜像源
RUN echo "http://mirrors.aliyun.com/alpine/v3.21/main" > /etc/apk/repositories && \
    echo "http://mirrors.aliyun.com/alpine/v3.21/community" >> /etc/apk/repositories

# 安装系统依赖
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir --user -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY . .

# 使用 Alpine Linux 作为生产阶段的基础镜像
FROM python:3.10.16-alpine

# 设置工作目录
WORKDIR /app

# 从构建阶段复制 Python 依赖
COPY --from=builder /root/.local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# 从构建阶段复制项目文件
COPY --from=builder /app /app

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV DJANGO_SETTINGS_MODULE=PyAutoTest.settings

# 启动 Django 开发服务器
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]