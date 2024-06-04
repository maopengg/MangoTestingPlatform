import cgi
from email.parser import BytesParser
from io import BytesIO

# 假设这是你的multipart/form-data数据
raw_data = b"""
------WebKitFormBoundaryL30SdvU0YozVLK4A
Content-Disposition: form-data; name="username"

maopeng@zalldigital.com
------WebKitFormBoundaryL30SdvU0YozVLK4A
Content-Disposition: form-data; name="password"

dc483e80a7a0bd9ef71d8cf973673924
------WebKitFormBoundaryL30SdvU0YozVLK4A--
"""

# 移除最后的换行符，确保数据格式正确
if raw_data.endswith(b"\n"):
    raw_data = raw_data[:-1]

# 使用BytesIO将bytes数据转换为文件对象
data_stream = BytesIO(raw_data)

# 使用BytesParser解析multipart/form-data
parser = BytesParser()
message = parser.parse(data_stream)

# 创建一个空字典来存储解析后的数据
form_data = {}

# 遍历消息的部分（parts）
for part in message.walk():
    # 获取Content-Disposition头部中的name参数
    content_disposition = part.get("Content-Disposition")
    if content_disposition:
        _, params = cgi.parse_header(content_disposition)
        name = params.get("name")
        if name:
            # 将part的payload（即数据内容）添加到字典中
            form_data[name] = part.get_payload(decode=True).decode("utf-8")

print(form_data)