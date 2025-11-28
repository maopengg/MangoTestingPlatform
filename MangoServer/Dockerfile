FROM python:3.10-slim-bullseye
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .

EXPOSE 8000
ARG DJANGO_ENV

ENV DJANGO_SETTINGS_MODULE=src.settings
ENV DJANGO_ENV=${DJANGO_ENV}
RUN echo "构建后端服务：$DJANGO_ENV"

# CMD ["sh", "-c", "daphne -b 0.0.0.0 -p 8000 src.asgi:application"]
CMD ["uvicorn", "src.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
