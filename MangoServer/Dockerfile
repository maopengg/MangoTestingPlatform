# 使用官方Python镜像作为基础镜像
FROM python:3.10-slim
# 设置工作目录
WORKDIR /app
# 复制项目文件到工作目录
COPY . /app/
# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt
# 暴露应用端口（Django默认端口为8000）
EXPOSE 8000
# 定义环境变量（可选）
ENV DJANGO_SETTINGS_MODULE=mydjangoapp.settings
# 运行Django开发服务器（仅用于开发环境）
# 在生产环境中，你应该使用更合适的WSGI服务器，如Gunicorn
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--env=prod"]
