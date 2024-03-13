import requests

url = "http://127.0.0.1:8000/system/socket/all/user/list"

payload = {}
headers = {
  'Authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInR5cGUiOiJqd3QifQ.eyJpZCI6MSwidXNlcm5hbWUiOiIxNzc5ODMzOTUzMyIsImV4cCI6MTcwOTczMjg4MX0.WflG-dhuS7Jc2HLdlgT3ouB6O7YdVTc6NPuKKM3KNb4'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)
