#!/usr/bin/python高级
# -*- coding: UTF-8 -*-
import json

import requests

url = 'https://cdxp.growknows.cn/backend/api-data/portrait/v2/user/list'
headers = {'Host': 'cdxp.growknows.cn', 'Connection': 'keep-alive', 'Content-Length': '31', 'currentProject': 'z7adds',
           'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Microsoft Edge";v="114"', 'service': 'zall',
           'sec-ch-ua-mobile': '?0', 'Authorization': 'Bearer 39c2a856-1b3a-4d74-8520-6d076585f8aa',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.43',
           'Content-Type': 'application/json;charset=UTF-8', 'Accept': 'application/json, text/plain, */*',
           'userId': '201', 'X-Sign': '68f7837324a90cc3c4a59102af11b1e273d8d4c82915c01a2a7420e53fdcdd09',
           'X-Time': '1686564611816', 'X-Nonce': '2ZLMkAs3bS6TALUb2cBYhscTFx7mFgs2', 'sec-ch-ua-platform': '"Windows"',
           'Origin': 'https://cdxp.growknows.cn', 'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'cors',
           'Sec-Fetch-Dest': 'empty',
           'Referer': 'https://cdxp.growknows.cn/customerAndCustomerGroup/tag/userListMain?projectName=z7adds',
           'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
           }
data = {
    "currentPage": 1,
    "pageSize": 30000
}
html = requests.post(url, headers=headers, json=data)
for i in html.json().get('data').get('data'):
    if i.get("user_id") == "4-62d9fb54-b48f-4158-ad7e-a8b4d671a06a":
        print(json.dumps(i).encode('utf-8').decode())
#
# user_id = html.json().get('data').get('data')[0].get("user_id")
# print(user_id)
