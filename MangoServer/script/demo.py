import json
from urllib import parse

data = parse.parse_qs(
    "id=1749732204080648194&sort=-1&name=&status=1&remark=&createBy=1&createTime=2024-01-23+17:54:00&updateBy=1&updateTime=&createName=admin%40aigc.com&updateName=&workFlowName=api%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B5%8B%E8%AF%95-%E6%96%B0%E5%BB%BAFlow-%E5%89%AF%E6%9C%AC39&version=&workFlowStatus=2&workFlowType=1&tenantId=1&applicationTemplate=0")

print(json.dumps({key:value[0] for key, value in data.items()}, ensure_ascii=False))