FROM python:3.10-slim-bullseye
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://repo.huaweicloud.com/repository/pypi/simple/
COPY . .

EXPOSE 8000
ARG DJANGO_ENV

ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
RUN echo "构建后端服务：$DJANGO_ENV"

CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:8000 --env=${DJANGO_ENV}"]
