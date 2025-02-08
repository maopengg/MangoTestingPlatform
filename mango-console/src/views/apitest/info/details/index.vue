<template>
  <div>
    <a-card title="接口详情">
      <template #extra>
        <a-space>
          <a-button status="success" size="small" @click="onRunCase">执行</a-button>
          <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
        </a-space>
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
        <template #extra>
          <a-space>
            <a-button type="primary" size="small" @click="addData" :disabled="!data.addButton"
              >增加</a-button
            >
          </a-space>
        </template>
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
        <a-tab-pane key="5" title="后置jsonpath提取">
          <a-space direction="vertical">
            <a-space v-for="(value, index) of data.front_json_path" :key="index">
              <a-input
                placeholder="请输入缓存key"
                v-model="data.front_json_path[index].key"
                @blur="upDate('front_json_path', data.front_json_path)"
              />
              <a-input
                placeholder="请输入jsonpath语法"
                v-model="data.front_json_path[index].value"
                @blur="upDate('front_json_path', data.front_json_path)"
              />

              <a-button
                type="text"
                size="small"
                status="danger"
                @click="removeFrontSql(data.front_json_path, index, 'front_json_path')"
                >移除
              </a-button>
            </a-space>
          </a-space>
        </a-tab-pane>
        <a-tab-pane key="6" title="后置正则提取">
          <a-space direction="vertical">
            <a-space v-for="(value, index) of data.front_re" :key="index">
              <a-input
                placeholder="请输入缓存key"
                v-model="data.front_re[index].key"
                @blur="upDate('front_re', data.front_re)"
              />
              <a-input
                placeholder="请输入jsonpath语法"
                v-model="data.front_re[index].value"
                @blur="upDate('front_re', data.front_re)"
              />

              <a-button
                type="text"
                size="small"
                status="danger"
                @click="removeFrontSql(data.front_re, index, 'front_re')"
                >移除
              </a-button>
            </a-space>
          </a-space>
        </a-tab-pane>

        <a-tab-pane key="7" title="响应结果">
          <a-space direction="vertical">
            <a-space>
              <a-tag color="orange">响 应 码</a-tag>
              <span>{{ data.result_data?.status_code }}</span>
            </a-space>
            <a-space>
              <a-tag color="orange">响应时间</a-tag>
              <span>{{ data.result_data?.response_time }}</span>
            </a-space>
            <a-space>
              <a-tag color="orange">缓存数据</a-tag>
              <span>{{ data.result_data?.cache_all }}</span>
            </a-space>
            <a-space>
              <a-tag color="orange">响 应 体</a-tag>
              <pre>{{
                strJson(
                  data.result_data?.response_json
                    ? data.result_data?.response_json
                    : data.result_data?.response_text
                )
              }}</pre>
            </a-space>
          </a-space>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { getApiCaseInfoRun, getApiInfo, putApiInfo } from '@/api/apitest/info'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { strJson } from '@/utils/tools'
  const enumStore = useEnum()
  const userStore = useUserStore()

  const pageData: any = usePageData()
  const data: any = reactive({
    id: 0,
    pageType: '0',
    addButton: false,
    header: formatJson(pageData.record.header),
    params: formatJson(pageData.record.params),
    json: formatJson(pageData.record.json),
    data: formatJson(pageData.record.data),
    file: formatJson(pageData.record.file),
    front_json_path: pageData.record.front_json_path,
    front_re: pageData.record.front_re,
    result_data: pageData.record.result_data,
  })

  function switchType(key: any) {
    data.pageType = key
    if (data.pageType === '5' || data.pageType === '6') {
      data.addButton = true
    } else {
      data.addButton = false
    }
  }
  function addData() {
    if (data.pageType === '5') {
      data.front_json_path.push({ key: '', value: '' })
    } else if (data.pageType === '6') {
      data.front_re.push({ key: '', value: '' })
    }
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
  function removeFrontSql(item: any, index: number, key: string) {
    item.splice(index, 1)
    upDate(key, item)
  }
  function upDate(key: string, value1: string) {
    let value = pageData.record
    if (!(key === 'front_json_path' || key === 'front_re')) {
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
    }
    delete value.module
    delete value.project_product
    putApiInfo(value)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }
  function onRunCase() {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    Message.loading('接口开始执行中~')
    getApiCaseInfoRun(pageData.record.id, userStore.selected_environment)
      .then((res) => {
        data.caseResult = res.data
        Message.success(res.msg)

        doRefresh()
      })
      .catch(console.log)
  }
  function doRefresh() {
    getApiInfo({ id: pageData.record.id })
      .then((res) => {
        const res_data = res.data[0]
        data.header = formatJson(res_data.header)
        data.params = formatJson(res_data.params)
        data.json = formatJson(res_data.json)
        data.data = formatJson(res_data.data)
        data.file = formatJson(res_data.file)
        data.front_json_path = res_data.front_json_path
        data.front_re = res_data.front_re
        data.result_data = res_data.result_data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      switchPageType()
    })
  })
</script>
