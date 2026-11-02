import requests

url = "https://example.com/clm/api/login/getWatermarkUrl"

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
    "clm-isfa": "0",
    "csrf-token": "rhm57sqper00",
    "priority": "u=1, i",
    "referer": "https://example.com/admin/permissions/roles",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sso-redirect-url": "https://example.com/admin/permissions/roles",
    "tenant_id": "7270714306264580363",
    "timezone-offset": "-480",
    "traceparent": "00-8439b4db2e83d270045dd6c22d9474e1-1ceb541c6619d09d-01",
    "x-log-id": "8439b4db2e83d270045dd6c22d9474e1",
    "x-requested-with": "XMLHttpRequest",
}

cookies = {
    "i18next": "zh-CN",
    "zs_session": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mbyI6eyJ1c2VySWQiOjExODI3MDk0NjQ2MzgxNjA5ODQsInRlbmFudElkIjo3MjcwNzE0MzA2MjY0NTgwMzYzfSwiYXBwSW5mbyI6eyJwbGF0Zm9ybSI6ImxhcmsiLCJhcHBJZCI6ImNsaV9hODliMjExY2FkM2U1MDBiIiwiYXBwVHlwZSI6IkNVU1RPTSIsImFwcEtleSI6IiJ9LCJhdXRoSW5mbyI6eyJhdXRoVHlwZSI6ImxhcmsiLCJsYXJrVXNlck9wZW5JZCI6IiIsImxhcmtVbmlvbklkIjoib25fNDA4NzI5NTdkOTQ4NDEyMGJmODhmMjAyMWNhNTM2ZDAiLCJzY29wZSI6IiIsImJ1c2luZXNzVHlwZSI6ImNvbnRyYWN0In0sImlzcyI6ImNvbW1vbi1vcmdhbml6YXRpb24tdjIiLCJzdWIiOiJvYXV0aC51c2VyLmFjY2Vzc190b2tlbiIsImV4cCI6MTc5NDAzNzIwNiwibmJmIjoxNzkzMTczMjA2LCJpYXQiOjE3OTMxNzMyMDYsImp0aSI6IjE4ZTJhMTg3ZTEzNzJiODcifQ.IWJx2LDhhDSTvsOCQrcWpt9VAtoSIrfc6B1aGpeoXiBX0ZwxsSvO45X37IF2w2yXvteoK8GgF7SmyJQA9wOswzOj8CsQo8G4vhurqvvTEfh2JvGSIxqZtEXyRXbnWkbp62co1fKHmzF0qUNbNUpymvglM16-cRU_FYyUjClx9nc",
    "clm_csrf_token": "rhm57sqper00",
    "_oo_s": "aid=b81a9fdb-0945-496a-b8ce-729c879dec66&rum=2&id=2e5a69c9-7a7d-4e0b-b313-9e30a9c89d83&created=1793173206835&expire=1793174385464&logs=1",
}

response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
print(response.request.headers)
print(response.status_code)
print(response.text)