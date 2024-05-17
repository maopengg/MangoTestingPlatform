import requests

url = "http://localhost:8000/user/file"

payload = {'type': '0',
'price': '105501',
'name': '576_1024.jpeg',
'project': '1'}
files=[
  ('file',('file',open("D:\GitCode\MangoTestingPlatform\MangoActuator\logs\screenshot\C端-账号144822.jpg",'rb'),'application/octet-stream'))
]
headers = {
  'Accept': 'application/json, text/plain, */*',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'Authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInR5cGUiOiJqd3QifQ.eyJpZCI6MSwidXNlcm5hbWUiOiIxNzc5ODMzOTUzMyIsImV4cCI6MTcxNTk2MDk5M30.xwxTlfv4vJP9dt9NTdRZhk9XFKvYiOXHtsW7RADNCDQ',
  'Cache-Control': 'no-cache',
  'Connection': 'keep-alive',
  'Origin': 'http://localhost:5173',
  'Pragma': 'no-cache',
  'Referer': 'http://localhost:5173/',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-site',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'project': '1',
  'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"'
}

response = requests.request("POST", url, headers=headers, data=payload, files=files)

print(response.text)
