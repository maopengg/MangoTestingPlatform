FROM mcr.microsoft.com/playwright/python:v1.43.0
WORKDIR /app
COPY linux_requirements.txt .
RUN pip install --no-cache-dir --user -r linux_requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY . .
CMD ["sh", "-c", "python lnux_main.py"]