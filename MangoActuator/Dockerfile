FROM mcr.microsoft.com/playwright/python:latest
WORKDIR /app

COPY . .
RUN pip install --no-cache-dir --user -r linux_requirements.txt -i https://mirror.sjtu.edu.cn/pypi/web/simple/

CMD ["python", "start_linux.py", "--ip=172.19.85.178", "--port=8000", "--username=admin", "--password=as123456"]