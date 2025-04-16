FROM mcr.microsoft.com/playwright/python:v1.43.0

WORKDIR /app

COPY linux_requirements.txt .

RUN pip install --no-cache-dir --user -r linux_requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/

COPY . .

CMD ["python", "linux_main.py", "--ip=127.19.85.178", "--port=8000", "--username=open", "--password=123456"]