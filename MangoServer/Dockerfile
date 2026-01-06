FROM python:3.10-slim-bullseye
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .

EXPOSE 8000
ARG DJANGO_ENV

ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
# 添加RUN_MAIN环境变量，确保在Docker环境下也能正确启动定时任务
ENV RUN_MAIN=true
RUN echo "构建后端服务：$DJANGO_ENV"


# 使用入口脚本启动
CMD ["/app/entrypoint.sh"]