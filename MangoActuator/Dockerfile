FROM mcr.microsoft.com/playwright/python:v1.43.0
WORKDIR /app
#COPY library/mangoautomation-1.0.56-py3-none-any.whl /tmp/

COPY linux_requirements.txt .
RUN pip install --no-cache-dir -r linux_requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY dynamic_requirements.txt .
RUN pip install --no-cache-dir -r dynamic_requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

#RUN pip install /tmp/mangoautomation-1.0.56-py3-none-any.whl


COPY . .

CMD ["sh", "-c", "python linux_main.py"]
