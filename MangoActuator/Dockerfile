FROM mcr.microsoft.com/playwright/python:v1.43.0
WORKDIR /app
COPY linux_requirements.txt .
RUN pip install --no-cache-dir --user -r linux_requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
COPY . .
CMD ["sh", "-c", "python linux_main.py --ip=${ACTUATOR_IP} --port=${ACTUATOR_PORT} --username=${ACTUATOR_USERNAME} --password=${ACTUATOR_PASSWORD}"]