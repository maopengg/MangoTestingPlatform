FROM python:3.10.16-slim AS builder
WORKDIR /app
COPY linux_requirements.txt .
RUN pip install --no-cache-dir -r linux_requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
COPY . .
RUN playwright install chromium

FROM python:3.10.16-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright


CMD ["python", "start_linux.py", "--ip=121.37.174.56", "--port=8000", "--username=admin", "--password=as123456"]