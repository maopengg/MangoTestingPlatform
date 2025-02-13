# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-05-20 18:02
# @Author : 毛鹏

from mangokit import requests


class Curl:

    @classmethod
    def curl(cls, url, data: dict):
        # headers = {
        #     'accept': 'application/json, text/javascript, */*; q=0.01',
        #     'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        #     'cache-control': 'no-cache',
        #     'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        #     'cookie': '_session=%7B%22slim.flash%22%3A%5B%5D%7D; uuid=28c91c07-9076-48de-b851-3414ed40f4e1; Hm_lvt_0fba23df1ee7ec49af558fb29456f532=1716199231; Hm_lpvt_0fba23df1ee7ec49af558fb29456f532=1716199231; _access=048e218dde8ee823110f193ba25a2024ac8732c5e9ef811181e7865b7334ea31; _session=%7B%22slim.flash%22%3A%5B%5D%7D',
        #     'origin': 'https://tool.lu',
        #     'pragma': 'no-cache',
        #     'priority': 'u=1, i',
        #     'referer': 'https://tool.lu/curl/',
        #     'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        #     'sec-ch-ua-mobile': '?0',
        #     'sec-ch-ua-platform': '"Windows"',
        #     'sec-fetch-site': 'same-origin',
        #     'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        # }
        # payload = "command=curl+'http%3A%2F%2F172.16.90.176%3A8088%2Fportal%2Fr%2Fjd'+%5C%0A++-H+'Accept%3A+application%2Fjson%2C+text%2Fjavascript%2C+*%2F*%3B+q%3D0.01'+%5C%0A++-H+'Accept-Language%3A+zh-CN%2Czh%3Bq%3D0.9%2Cen%3Bq%3D0.8'+%5C%0A++-H+'Cache-Control%3A+no-cache'+%5C%0A++-H+'Connection%3A+keep-alive'+%5C%0A++-H+'Content-Type%3A+application%2Fx-www-form-urlencoded%3B+charset%3DUTF-8'+%5C%0A++-H+'Cookie%3A+AWSLOGINUID%3Dnull%3B+AWSLOGINPWD%3Dnull%3B+AWSLOGINRSAPWD%3Dnull%3B+JSESSIONID%3D2C82C8B9061A296DD0E50E78C34DBD5E'+%5C%0A++-H+'Origin%3A+http%3A%2F%2F172.16.90.176%3A8088'+%5C%0A++-H+'Pragma%3A+no-cache'+%5C%0A++-H+'Referer%3A+http%3A%2F%2F172.16.90.176%3A8088%2Fportal%2Fr%2Fw%3Fsid%3D6d50e0b3-54a2-4e62-8ab4-90fbe07c497a%26cmd%3Dcom.actionsoft.apps.workbench_task%26start%3D1%26boxType%3D1%26boxName%3Dtodo%26groupName%3DnoGroup%26taskInstId%3D%26queryMode%3Dmytask'+%5C%0A++-H+'User-Agent%3A+Mozilla%2F5.0+(Windows+NT+10.0%3B+Win64%3B+x64)+AppleWebKit%2F537.36+(KHTML%2C+like+Gecko)+Chrome%2F124.0.0.0+Safari%2F537.36'+%5C%0A++-H+'X-Requested-With%3A+XMLHttpRequest'+%5C%0A++--data-raw+'cmd%3Dcom.actionsoft.apps.workbench_task_datalist%26sid%3D6d50e0b3-54a2-4e62-8ab4-90fbe07c497a%26boxName%3Dtodo%26groupName%3DnoGroup%26start%3D1%26owner%3D%26title%3D%26begin%3D%26end%3D%26iobd%3D%26ior%3D%26ios%3D%26ioc%3D%26extObj%3D%257B%2522queryMode%2522%253A%2522mytask%2522%257D%26customCondition%3D'+%5C%0A++--insecure&target=json"
        #
        # encoded_data = urllib.parse.urlencode(data)
        # print(encoded_data)
        # response = requests.request("POST", url, headers=headers, data=payload)
        # print(response.text)
        # response = HTTPRequest().test_http(RequestModel(method='POST', url=url, headers=headers, data=encoded_data))
        # print(response.json())
        # response_dict = response.json()
        # data1 = json.loads(response_dict.get('code'))
        # print(data1)
        url = "https://tool.lu/curl/ajax.html"

        payload = "command=curl+'http%3A%2F%2F172.16.90.176%3A8088%2Fportal%2Fr%2Fjd'+%5C%0A++-H+'Accept%3A+application%2Fjson%2C+text%2Fjavascript%2C+*%2F*%3B+q%3D0.01'+%5C%0A++-H+'Accept-Language%3A+zh-CN%2Czh%3Bq%3D0.9%2Cen%3Bq%3D0.8'+%5C%0A++-H+'Cache-Control%3A+no-cache'+%5C%0A++-H+'Connection%3A+keep-alive'+%5C%0A++-H+'Content-Type%3A+application%2Fx-www-form-urlencoded%3B+charset%3DUTF-8'+%5C%0A++-H+'Cookie%3A+AWSLOGINUID%3Dnull%3B+AWSLOGINPWD%3Dnull%3B+AWSLOGINRSAPWD%3Dnull%3B+JSESSIONID%3D2C82C8B9061A296DD0E50E78C34DBD5E'+%5C%0A++-H+'Origin%3A+http%3A%2F%2F172.16.90.176%3A8088'+%5C%0A++-H+'Pragma%3A+no-cache'+%5C%0A++-H+'Referer%3A+http%3A%2F%2F172.16.90.176%3A8088%2Fportal%2Fr%2Fw%3Fsid%3D6d50e0b3-54a2-4e62-8ab4-90fbe07c497a%26cmd%3Dcom.actionsoft.apps.workbench_task%26start%3D1%26boxType%3D1%26boxName%3Dtodo%26groupName%3DnoGroup%26taskInstId%3D%26queryMode%3Dmytask'+%5C%0A++-H+'User-Agent%3A+Mozilla%2F5.0+(Windows+NT+10.0%3B+Win64%3B+x64)+AppleWebKit%2F537.36+(KHTML%2C+like+Gecko)+Chrome%2F124.0.0.0+Safari%2F537.36'+%5C%0A++-H+'X-Requested-With%3A+XMLHttpRequest'+%5C%0A++--data-raw+'cmd%3Dcom.actionsoft.apps.workbench_task_datalist%26sid%3D6d50e0b3-54a2-4e62-8ab4-90fbe07c497a%26boxName%3Dtodo%26groupName%3DnoGroup%26start%3D1%26owner%3D%26title%3D%26begin%3D%26end%3D%26iobd%3D%26ior%3D%26ios%3D%26ioc%3D%26extObj%3D%257B%2522queryMode%2522%253A%2522mytask%2522%257D%26customCondition%3D'+%5C%0A++--insecure&target=json"
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'cookie': '_session=%7B%22slim.flash%22%3A%5B%5D%7D; uuid=28c91c07-9076-48de-b851-3414ed40f4e1; Hm_lvt_0fba23df1ee7ec49af558fb29456f532=1716199231; Hm_lpvt_0fba23df1ee7ec49af558fb29456f532=1716199231; _access=048e218dde8ee823110f193ba25a2024ac8732c5e9ef811181e7865b7334ea31; _session=%7B%22slim.flash%22%3A%5B%5D%7D',
            'origin': 'https://tool.lu',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://tool.lu/curl/',
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        print(response.json().get('code'))


if __name__ == '__main__':
    Curl.curl()
