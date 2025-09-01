ARG EXECUTOR_TYPE=pytest_web
ENV EXECUTOR_TYPE=${EXECUTOR_TYPE}
RUN echo "构建执行器：$EXECUTOR_TYPE"

#=================================================
# 1) pytest —— python:3.10-slim-bullseye
#=================================================
FROM python:3.10-slim-bullseye AS pytest
WORKDIR /app
# 换国内源
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
# pytest 只装 pytest 相关依赖
COPY linux_requirements.txt dynamic_requirements.txt pytest_requirements.txt ./
RUN pip install --no-cache-dir -r linux_requirements.txt -r pytest_requirements.txt -r dynamic_requirements.txt
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
FROM python:3.10-slim-bullseye AS final
WORKDIR /app

# 根据 EXECUTOR_TYPE 选择对应的构建阶段
RUN if [ "$EXECUTOR_TYPE" = "pytest" ]; then \
        echo "选择 pytest 阶段"; \
        COPY --from=pytest . .; \
    elif [ "$EXECUTOR_TYPE" = "pytest_web" ]; then \
        echo "选择 pytest_web 阶段"; \
        COPY --from=pytest_web . .; \
    elif [ "$EXECUTOR_TYPE" = "web_ui" ]; then \
        echo "选择 web_ui 阶段"; \
        COPY --from=web_ui . .; \
    elif [ "$EXECUTOR_TYPE" = "android_ui" ]; then \
        echo "选择 android_ui 阶段"; \
        COPY --from=android_ui . .; \
    else \
        echo "未指定有效的 EXECUTOR_TYPE，使用默认的 pytest_web 阶段"; \
        COPY --from=pytest_web . .; \
    fi

# 设置默认的 CMD
CMD ["python", "linux_main.py", "--env=${EXECUTOR_TYPE}"]