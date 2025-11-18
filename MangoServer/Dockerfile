FROM python:3.10-slim-bullseye
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .

RUN python manage.py migrate --noinput
EXPOSE 8000
ARG DJANGO_ENV

ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
RUN echo "构建后端服务：$DJANGO_ENV"

CMD ["sh", "-c", "uvicorn src.asgi:application --host 0.0.0.0 --port 8000 --workers 4"]
