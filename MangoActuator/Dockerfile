ARG EXECUTOR_TYPE

RUN if [ -z "$EXECUTOR_TYPE" ]; then \
        echo "错误: EXECUTOR_TYPE 未设置，请在 .env 文件中配置 EXECUTOR_TYPE" && \
        exit 1; \
    fi

FROM python:3.10-slim-bullseye AS pytest
WORKDIR /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY linux_requirements.txt dynamic_requirements.txt pytest_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r pytest_requirements.txt -r dynamic_requirements.txt
COPY . .

FROM mcr.microsoft.com/playwright/python:v1.43.0 AS pytest_web
WORKDIR /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY linux_requirements.txt dynamic_requirements.txt pytest_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt -r pytest_requirements.txt
COPY . .

FROM mcr.microsoft.com/playwright/python:v1.43.0 AS web_ui
WORKDIR /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY linux_requirements.txt dynamic_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt
COPY . .

FROM mcr.microsoft.com/playwright/python:v1.43.0 AS android_ui
WORKDIR /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY linux_requirements.txt dynamic_requirements.txt android_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt -r android_requirements.txt
COPY . .

FROM ${EXECUTOR_TYPE} AS final
WORKDIR /app
ARG EXECUTOR_TYPE
ENV EXECUTOR_TYPE=${EXECUTOR_TYPE}
RUN echo "构建执行器：$EXECUTOR_TYPE"
CMD ["python", "linux_main.py", "--env=${EXECUTOR_TYPE}"]