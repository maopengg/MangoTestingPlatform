for i in range(100):
    import requests

    url = "http://172.16.100.47:8000/system/socket/all/user/list"

    payload = {}
    headers = {
        'authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInR5cGUiOiJqd3QifQ.eyJpZCI6MSwidXNlcm5hbWUiOiJtYW9wZW5nIiwibmFtZSI6Ilx1NmJkYlx1OWU0ZiIsImV4cCI6MTc2NTMzODMwOH0.tMUskkXjLtcMKYjNmolN7Cb6dPuHGSCboFK4JNLROPo'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.text)
