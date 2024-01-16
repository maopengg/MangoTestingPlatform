import json
from urllib.parse import parse_qs

import requests

url = "https://app-test.growknows.cn/dev-api/auth/oauth2/token"

payload = 'enterpriseName=yali008&userName=test005%40yali006.com&password=123456&code=4&uuid=2abe6ff5e94249f58605a76b57c1adb9&mode=none&grant_type=password&account_type=admin&scope=server'
headers = {
    'Authorization': 'Basic eHVleWk6eHVleWk=',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Cookie': 'SERVERCORSID=5f2c27a2826e61a65f5771b981490dee|1704191335|1704191335; SERVERID=5f2c27a2826e61a65f5771b981490dee|1704191335|1704191335'
}
r = requests.get(url="https://app-test.growknows.cn/dev-api/code")
_dict = {k: v[0] for k, v in parse_qs(payload).items()}
_dict['code'] = 'AIgc2023aiGC'
_dict['userName'] = 'test005@yali006.com'
_dict['password'] = '123456'
_dict['uuid'] = r.json()['data']['uuid']
response = requests.request("POST", url, headers=headers, data=_dict)
print(json.dumps(_dict))
print(response.text)
