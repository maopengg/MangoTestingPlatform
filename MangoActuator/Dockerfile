ARG EXECUTOR_TYPE

#=================================================
# 1) pytest —— 独立 alpine 镜像
#=================================================
FROM python:3.10.16-alpine AS pytest
WORKDIR /app
# 换国内源
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
# pytest 只装 pytest 相关依赖
COPY linux_requirements.txt pytest_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r pytest_requirements.txt
COPY . .

#=================================================
# 2) pytest_web —— playwright + pytest
#=================================================
FROM mcr.microsoft.com/playwright/python:v1.43.0 AS pytest_web
WORKDIR /app
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY linux_requirements.txt dynamic_requirements.txt pytest_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt -r pytest_requirements.txt
COPY . .

#=================================================
# 3) web_ui —— playwright 基础镜像 + 仅 web 依赖
#=================================================
FROM mcr.microsoft.com/playwright/python:v1.43.0 AS web_ui
WORKDIR /app
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY linux_requirements.txt dynamic_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt
COPY . .

#=================================================
# 4) android_ui —— playwright 基础镜像 + 安卓依赖
#=================================================
FROM mcr.microsoft.com/playwright/python:v1.43.0 AS android_ui
WORKDIR /app
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY linux_requirements.txt dynamic_requirements.txt android_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r dynamic_requirements.txt -r android_requirements.txt
COPY . .

#=================================================
# 5) 最终阶段：只选对应阶段
#=================================================
FROM ${EXECUTOR_TYPE} AS final
ENV EXECUTOR_TYPE=${EXECUTOR_TYPE}
CMD ["python", "linux_main.py", "--env=${EXECUTOR_TYPE}"]