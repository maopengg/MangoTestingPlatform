FROM ubuntu/python:3.10-22.04 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY . .

FROM ubuntu/python:3.10-22.04
WORKDIR /app

# 替换为清华大学的 Ubuntu 镜像源
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb-src https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list

# 安装 Git 和其他依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制 Python 依赖和应用程序代码
COPY --from=builder /root/.local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app

# 暴露端口
EXPOSE 8000

# 设置环境变量
ARG DJANGO_ENV
ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}

# 启动 Django 开发服务器
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=${DJANGO_ENV}"]