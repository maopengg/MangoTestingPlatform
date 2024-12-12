<template>
  <div>
    <a-card title="接口详情">
      <template #extra>
        <a-affix :offsetTop="80">
          <a-space>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </a-affix>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 25%">
          <p>接口ID：{{ pageData.record.id }}</p>
          <span>所属项目：{{ pageData.record.project_product?.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module?.name }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 25%">
          <span>接口名称：{{ pageData.record.name }}</span>
          <span>接口URL：{{ pageData.record.url }}</span>
          <span>接口方法：{{ enumStore.method[pageData.record.method].title }}</span>
        </a-space>
      </div>
    </a-card>
    <a-card>
      <a-tabs @tab-click="(key) => switchType(key)" :active-key="data.pageType">
        <a-tab-pane key="0" title="请求头">
          <a-textarea
            placeholder="请输入请求头，字符串形式"
            v-model="data.header"
            allow-clear
            auto-size
            @blur="upDate('header', data.header)"
          />
        </a-tab-pane>
        <a-tab-pane key="1" title="参数">
          <a-textarea
            placeholder="请输入json格式的数据"
            v-model="data.params"
            allow-clear
            auto-size
            @blur="upDate('params', data.params)"
          />
        </a-tab-pane>
        <a-tab-pane key="2" title="表单">
          <a-textarea
            placeholder="请输入json格式的表单"
            v-model="data.data"
            allow-clear
            auto-size
            @blur="upDate('data', data.data)"
          />
        </a-tab-pane>
        <a-tab-pane key="3" title="JSON">
          <a-textarea
            placeholder="请输入json格式的JSON"
            v-model="data.json"
            allow-clear
            auto-size
            @blur="upDate('json', data.json)"
          />
        </a-tab-pane>
        <a-tab-pane key="4" title="文件">
          <a-textarea
            placeholder="请输入json格式的文件上传数据"
            v-model="data.file"
            allow-clear
            auto-size
            @blur="upDate('file', data.file)"
          />
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { putApiInfo } from '@/api/apitest/info'
  import { useEnum } from '@/store/modules/get-enum'
  const enumStore = useEnum()

  const pageData: any = usePageData()
  const data: any = reactive({
    id: 0,
    pageType: '0',
    header: formatJson(pageData.record.header),
    params: formatJson(pageData.record.params),
    json: formatJson(pageData.record.json),
    data: formatJson(pageData.record.data),
    file: formatJson(pageData.record.file),
  })

  function switchType(key: string) {
    data.pageType = key
  }
  function switchPageType() {
    if (pageData.record.params) {
      data.pageType = '1'
    } else if (pageData.record.data) {
      data.pageType = '2'
    } else if (pageData.record.json) {
      data.pageType = '3'
    } else if (pageData.record.file) {
      data.pageType = '4'
    } else {
      data.pageType = '0'
    }
  }
  function doResetSearch() {
    window.history.back()
  }
  function formatJson(items: any) {
    if (items === null) {
      return null
    }
    return JSON.stringify(items, null, 2)
  }

  function upDate(key: string, value1: string) {
    let value = pageData.record
    try {
      if (value1) {
        const parsedValue = JSON.parse(value1)
        if (typeof parsedValue === 'object') {
          value[key] = parsedValue
        } else {
          Message.error(`请输入json格式的：${key}`)
          return
        }
      } else {
        value[key] = null
      }
    } catch (e) {
      Message.error(`请输入json格式的：${key}`)
      return
    }
    delete value.module
    delete value.project_product
    putApiInfo(value)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      switchPageType()
    })
  })
</script>
