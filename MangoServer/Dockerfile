FROM python:3.10.16-alpine AS builder
WORKDIR /app
RUN echo "http://mirrors.aliyun.com/alpine/v3.21/main" > /etc/apk/repositories && \
    echo "http://mirrors.aliyun.com/alpine/v3.21/community" >> /etc/apk/repositories
RUN apk update && apk add --no-cache gcc musl-dev python3 python3-dev linux-headers
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY . .

FROM python:3.10.16-alpine
WORKDIR /app
COPY --from=builder /root/.local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app
EXPOSE 8000
ARG DJANGO_ENV
ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=${DJANGO_ENV}"]