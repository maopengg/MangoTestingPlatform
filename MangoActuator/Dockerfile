# 定义构建参数，设置默认值
ARG EXECUTOR_TYPE=pytest_web

#=================================================
# 各个阶段定义（保持不变）
#=================================================
FROM python:3.10-slim-bullseye AS pytest
WORKDIR /app
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY linux_requirements.txt dynamic_requirements.txt pytest_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r pytest_requirements.txt -r dynamic_requirements.txt
COPY . .

FROM mcr.microsoft.com/playwright/python:v1.43.0 AS pytest_web
WORKDIR /app
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY linux_requirements.txt dynamic_requirements.txt pytest_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt -r pytest_requirements.txt
COPY . .

FROM mcr.microsoft.com/playwright/python:v1.43.0 AS web_ui
WORKDIR /app
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY linux_requirements.txt dynamic_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt
COPY . .

FROM mcr.microsoft.com/playwright/python:v1.43.0 AS android_ui
WORKDIR /app
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY linux_requirements.txt dynamic_requirements.txt android_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt -r android_requirements.txt
COPY . .

#=================================================
# 最终阶段：使用构建参数选择阶段
#=================================================
FROM ${EXECUTOR_TYPE} AS final
WORKDIR /app

# 传递构建参数到环境变量
ARG EXECUTOR_TYPE
ENV EXECUTOR_TYPE=${EXECUTOR_TYPE}

RUN echo "构建执行器：$EXECUTOR_TYPE"

CMD ["python", "linux_main.py", "--env=${EXECUTOR_TYPE}"]