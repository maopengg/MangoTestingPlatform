FROM python:3.10.16-alpine
WORKDIR /app
COPY . /app/
# 安装编译工具和依赖
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers
# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=PyAutoTest.settings
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=prod"]