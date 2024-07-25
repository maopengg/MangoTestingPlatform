<template>
  <a-card>
    <a-space direction="vertical">
      <a-space>
        <a-input
          :style="{ width: '320px' }"
          default-value="cont11111ent"
          placeholder="Please enter something"
          id=""
          allow-clear
          disabled
        />
        <a-textarea v-model="value" />
        <a-button @click="postApiInfo">点击</a-button>
      </a-space>
      <a-space>
        <pre>{{ options }}</pre>
      </a-space>
    </a-space>
  </a-card>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import parseCurl from 'parse-curl'
  import qs from 'qs'

  const value: any = ref(`curl 'http://localhost:8000/api/import/api' \\
  -H 'Accept: application/json, text/plain, */*' \\
  -H 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8' \\
  -H 'Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInR5cGUiOiJqd3QifQ.eyJpZCI6MSwidXNlcm5hbWUiOiIxNzc5ODMzOTUzMyIsImV4cCI6MTcxNzUxMTYyMX0.kefcfEazrfwo5iHNRkBIVLbyY6C1_XMYPIzVOnpwLs4' \\
  -H 'Cache-Control: no-cache' \\
  -H 'Connection: keep-alive' \\
  -H 'Content-Type: application/json; charset=UTF-8' \\
  -H 'Origin: http://localhost:5173' \\
  -H 'Pragma: no-cache' \\
  -H 'Referer: http://localhost:5173/' \\
  -H 'Sec-Fetch-Dest: empty' \\
  -H 'Sec-Fetch-Mode: cors' \\
  -H 'Sec-Fetch-Site: same-site' \\
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36' \\
  -H 'project: 1' \\
  -H 'sec-ch-ua: "Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"' \\
  -H 'sec-ch-ua-mobile: ?0' \\
  -H 'sec-ch-ua-platform: "Windows"' \\
  --data-raw '{"project_product":7,"module":35,"name":"测试导入","client":0,"curl":{"method":"GET","header":{"Accept":"application/json, text/plain, */*","Accept-Language":"zh-CN,zh;q=0.9,en;q=0.8","Cache-Control":"no-cache","Content-Type":"multipart/form-data; boundary=----WebKitFormBoundaryL30SdvU0YozVLK4A","Cookie":"Hm_lvt_f93cf7bc34efb4e4c5074b754dec8a6b=1716877654","Origin":"http://test.zalldigital.cn","Pragma":"no-cache","Proxy-Connection":"keep-alive","Referer":"http://test.zalldigital.cn/login","User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},"url":"http://test.zalldigital.cn/api//auth/login"},"type":"1"}'`)
  const options: any = ref('测试')
  function parseDataRaw(curlCommand) {
    const dataRawIndex = curlCommand.indexOf('--data-raw')
    if (dataRawIndex !== -1) {
      const dataRawValue: string = curlCommand.substring(dataRawIndex + '--data-raw '.length)
      // return JSON.parse(dataRawValue)
      return dataRawValue
    }
    return {}
  }

  function postApiInfo() {
    const parsedCurl = parseCurl(value.value)
    const dataRaw = parseDataRaw(value.value)
    options.value = { ...parsedCurl, data: dataRaw }
  }
</script>
