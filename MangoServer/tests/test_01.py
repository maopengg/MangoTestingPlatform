import json

data_list = []
with open(r"C:\Users\Administrator\Desktop\默认模块.openapi.json", 'r', encoding='utf-8') as f:
    data = json.load(f)
    for url, v in data.get('paths').items():
        for method, data in v.items():
            data_list.append({'url': url, 'method': method, 'name': data.get('summary')})
print(json.dumps(data_list, ensure_ascii=False))
