ARG ACTUATOR_PROFILE=standard
ARG K6_VERSION=2.2.0
ARG TARGETARCH=amd64

FROM m.daocloud.io/mcr.microsoft.com/playwright/python:v1.62.0-noble AS core_runtime
ARG K6_VERSION
ARG TARGETARCH
COPY deploy/packages/k6/k6-v${K6_VERSION}-linux-${TARGETARCH}.tar.gz /tmp/k6.tar.gz
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python-is-python3 xvfb xauth x11-utils \
    && xvfb-run -a -s '-screen 0 1440x900x24' sh -c 'xdpyinfo >/dev/null' \
    && mkdir -p /tmp/k6 \
    && tar -xzf /tmp/k6.tar.gz -C /tmp/k6 --strip-components=1 \
    && install -m 0755 /tmp/k6/k6 /usr/local/bin/k6 \
    && k6 version \
    && rm -rf /tmp/k6 /tmp/k6.tar.gz \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM core_runtime AS standard
COPY requirements/linux.txt requirements/pytest.txt requirements/linux-local.txt ./requirements/
COPY local_packages/mangotools-2.0.8-py3-none-any.whl local_packages/mangoautomation-2.1.0-py3-none-any.whl ./local_packages/
RUN python -m pip install --break-system-packages --no-cache-dir \
    -r requirements/linux.txt \
    -r requirements/pytest.txt \
    -r requirements/linux-local.txt -i https://mirrors.cloud.tencent.com/pypi/simple
COPY . .

FROM standard AS android
COPY requirements/android.txt ./requirements/
RUN python -m pip install --break-system-packages --no-cache-dir \
    -r requirements/android.txt -i https://mirrors.cloud.tencent.com/pypi/simple

# 以下别名只兼容旧流水线，不再代表不同核心版本。
FROM standard AS pytest
FROM standard AS pytest_web
FROM standard AS web_ui
FROM android AS android_ui

FROM ${ACTUATOR_PROFILE} AS final
WORKDIR /app
ARG ACTUATOR_PROFILE
ENV MANGO_ACTUATOR_PROFILE=${ACTUATOR_PROFILE}
ENV MANGO_K6_AUTO_INSTALL=0
RUN case "$ACTUATOR_PROFILE" in standard|android|pytest|pytest_web|web_ui|android_ui) ;; \
    *) echo "ACTUATOR_PROFILE 必须为 standard、android、pytest 或兼容预设 pytest_web/web_ui/android_ui" && exit 1 ;; esac
RUN echo "构建统一执行器，安装预设：$ACTUATOR_PROFILE"
CMD ["python", "headless_main.py"]
