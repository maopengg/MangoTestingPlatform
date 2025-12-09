for i in range(100):
    import requests

    url = "http://172.16.100.47:8000/system/socket/all/user/list"

    payload = {}
    headers = {
        'authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInR5cGUiOiJqd3QifQ.eyJpZCI6MSwidXNlcm5hbWUiOiJtYW9wZW5nIiwibmFtZSI6Ilx1NmJkYlx1OWU0ZiIsImV4cCI6MTc2NTI1MTg1N30.1MlS-UWyBQHaRMUjPhT20eTGnjIJFuhzB_pEbUHePl0'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.text)
