FROM mcr.microsoft.com/playwright/python:v1.43.0
WORKDIR /app

COPY linux_requirements.txt .
RUN pip install --no-cache-dir -r linux_requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY dynamic_requirements.txt .
RUN pip install --no-cache-dir -r dynamic_requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple


COPY . .

CMD ["sh", "-c", "python linux_main.py"]
