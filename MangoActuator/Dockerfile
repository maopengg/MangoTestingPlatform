FROM mcr.microsoft.com/playwright/python:latest

WORKDIR /app

COPY linux_requirements.txt .

RUN pip install --no-cache-dir --user -r linux_requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/

COPY . .

CMD ["python", "start_linux.py", "--ip=172.19.85.178", "--port=8000", "--username=admin", "--password=123456"]