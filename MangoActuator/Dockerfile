FROM python:3.10.16-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r linux_requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY . .

FROM python:3.10.16-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app
EXPOSE 8000

CMD ["python", "start_linux.py", "--ip=121.37.174.56", "--port=8000", "--username=admin", "--password=as123456"]