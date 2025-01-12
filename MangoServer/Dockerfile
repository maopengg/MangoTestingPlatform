#FROM python:3.10.16-alpine
#WORKDIR /app
#COPY . /app/
## 安装编译工具和依赖
#RUN apk add --no-cache gcc musl-dev python3-dev linux-headers
## 安装项目依赖
#RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
#EXPOSE 8000
#ENV DJANGO_SETTINGS_MODULE=PyAutoTest.settings
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=prod"]
# 第一阶段：构建阶段
FROM python:3.10.16-alpine AS builder
WORKDIR /app
COPY . /app/
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 第二阶段：运行阶段
FROM python:3.10.16-alpine
WORKDIR /app
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=PyAutoTest.settings
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=prod"]
