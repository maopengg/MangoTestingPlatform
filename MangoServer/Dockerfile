FROM python:3.10.16-alpine
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY dynamic_requirements.txt .
RUN pip install --no-cache-dir -r dynamic_requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

COPY . .

EXPOSE 8000
ARG DJANGO_ENV
ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}

CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:8000 --env=${DJANGO_ENV}"]
