ARG EXECUTOR_TYPE

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

# 设置一个无效的默认值来触发明确的错误而不是警告
FROM ${EXECUTOR_TYPE:-invalid_executor} AS final
WORKDIR /app
ARG EXECUTOR_TYPE
ENV EXECUTOR_TYPE=${EXECUTOR_TYPE}

# 验证 EXECUTOR_TYPE 是否为有效值之一
RUN case "$EXECUTOR_TYPE" in \
        pytest|pytest_web|web_ui|android_ui) ;; \
        *) \
            echo "EXECUTOR_TYPE的值在env文件中必填" && \
            exit 1 ;; \
    esac

RUN echo "构建执行器：$EXECUTOR_TYPE"
CMD ["python", "linux_main.py", "--env=${EXECUTOR_TYPE}"]