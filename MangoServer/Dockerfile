FROM python:3.10.16-alpine AS builder
WORKDIR /app
COPY . /app/
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

FROM python:3.10.16-alpine
WORKDIR /app
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=PyAutoTest.settings
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=prod"]
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=prod"]
