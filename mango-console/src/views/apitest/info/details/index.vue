<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="接口详情">
        <template #extra>
          <a-space>
            <a-button size="small" status="success" @click="onRunCase">执行</a-button>
            <a-button size="small" status="danger" @click="doResetSearch">返回</a-button>
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
    </template>
    <template #default>
      <a-card :bordered="false">
        <a-tabs :active-key="data.pageType" @tab-click="(key) => switchType(key)">
          <template #extra>
            <a-space v-if="data.addButton">
              <a-button size="small" type="primary" @click="addData">增加</a-button>
            </a-space>
          </template>
          <a-tab-pane key="0" title="请求头">
            <a-textarea
              v-model="data.headers"
              :auto-size="{ minRows: 28, maxRows: 28 }"
              allow-clear
              placeholder="请输入请求头，字符串形式"
              @blur="upDate('headers', data.headers)"
            />
          </a-tab-pane>
          <a-tab-pane key="1" title="参数">
            <a-textarea
              v-model="data.params"
              :auto-size="{ minRows: 28, maxRows: 28 }"
              allow-clear
              placeholder="请输入json格式的数据"
              @blur="upDate('params', data.params)"
            />
          </a-tab-pane>
          <a-tab-pane key="2" title="表单">
            <a-textarea
              v-model="data.data"
              :auto-size="{ minRows: 28, maxRows: 28 }"
              allow-clear
              placeholder="请输入json格式的表单"
              @blur="upDate('data', data.data)"
            />
          </a-tab-pane>
          <a-tab-pane key="3" title="JSON">
            <a-textarea
              v-model="data.json"
              :auto-size="{ minRows: 28, maxRows: 28 }"
              allow-clear
              placeholder="请输入json格式的JSON"
              @blur="upDate('json', data.json)"
            />
          </a-tab-pane>
          <a-tab-pane key="4" title="文件">
            <a-textarea
              v-model="data.file"
              :auto-size="{ minRows: 28, maxRows: 28 }"
              allow-clear
              placeholder="请输入json格式的文件上传数据"
              @blur="upDate('file', data.file)"
            />
          </a-tab-pane>
          <a-tab-pane key="5" title="后置jsonpath提取">
            <a-space direction="vertical">
              <a-space v-for="(value, index) of data.posterior_json_path" :key="index">
                <a-input
                  v-model="data.posterior_json_path[index].key"
                  placeholder="请输入缓存key"
                  @blur="upDate('posterior_json_path', data.posterior_json_path)"
                />
                <a-input
                  v-model="data.posterior_json_path[index].value"
                  placeholder="请输入jsonpath语法"
                  @blur="upDate('posterior_json_path', data.posterior_json_path)"
                />

                <a-button
                  size="small"
                  status="danger"
                  type="text"
                  @click="removeFrontSql(data.posterior_json_path, index, 'posterior_json_path')"
                  >移除
                </a-button>
              </a-space>
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="6" title="后置正则提取">
            <a-space direction="vertical">
              <a-space v-for="(value, index) of data.posterior_re" :key="index">
                <a-input
                  v-model="data.posterior_re[index].key"
                  placeholder="请输入缓存key"
                  @blur="upDate('posterior_re', data.posterior_re)"
                />
                <a-input
                  v-model="data.posterior_re[index].value"
                  placeholder="请输入jsonpath语法"
                  @blur="upDate('posterior_re', data.posterior_re)"
                />

                <a-button
                  size="small"
                  status="danger"
                  type="text"
                  @click="removeFrontSql(data.posterior_re, index, 'posterior_re')"
                  >移除
                </a-button>
              </a-space>
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="7" title="后置函数">
            <a-textarea
              v-model="data.posterior_func"
              :auto-size="{ minRows: 28, maxRows: 28 }"
              allow-clear
              placeholder="根据帮助文档，输入自定义后置函数"
              @blur="upDate('posterior_func', data.posterior_func)"
            />
          </a-tab-pane>
          <a-tab-pane key="8" title="响应结果">
            <a-tabs default-active-key="1">
              <a-tab-pane key="1" title="基础信息">
                <a-space direction="vertical">
                  <a-space>
                    <a-tag color="orange">响 应 码</a-tag>
                    <span>{{ data.result_data?.code }}</span>
                  </a-space>
                  <a-space>
                    <a-tag color="orange">响应时间</a-tag>
                    <span>{{ data.result_data?.time }}</span>
                  </a-space>
                  <a-space>
                    <a-tag color="orange">缓存数据</a-tag>
                    <JsonDisplay :data="data.result_data?.cache_all" />
                  </a-space>
                </a-space>
              </a-tab-pane>
              <a-tab-pane key="2" title="请求信息">
                <a-space direction="vertical">
                  <a-space v-if="data.result_data?.request_headers">
                    <a-tag color="orange">请求头</a-tag>
                    <JsonDisplay :data="data.result_data?.request_headers" />
                  </a-space>
                  <a-space v-if="data.result_data?.request_params">
                    <a-tag color="orange">参数</a-tag>
                    <JsonDisplay :data="data.result_data?.request_params" />
                  </a-space>
                  <a-space v-if="data.result_data?.request_data">
                    <a-tag color="orange">表单</a-tag>
                    <JsonDisplay :data="data.result_data?.request_data" />
                  </a-space>
                  <a-space v-if="data.result_data?.request_json">
                    <a-tag color="orange">json</a-tag>
                    <JsonDisplay :data="data.result_data?.request_json" />
                  </a-space>
                  <a-space v-if="data.result_data?.request_file">
                    <a-tag color="orange">file</a-tag>
                    <JsonDisplay :data="data.result_data?.request_file" />
                  </a-space>
                </a-space>
              </a-tab-pane>
              <a-tab-pane key="3" title="响应信息">
                <a-space direction="vertical">
                  <a-space>
                    <a-tag color="orange">响 应 体</a-tag>
                    <JsonDisplay
                      :data="
                        data.result_data?.json ? data.result_data?.json : data.result_data?.text
                      "
                    />
                  </a-space>
                </a-space>
              </a-tab-pane>
            </a-tabs>
          </a-tab-pane>
        </a-tabs>
      </a-card>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { getApiCaseInfoRun, getApiInfo, putApiInfo } from '@/api/apitest/info'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'

  const enumStore = useEnum()
  const userStore = useUserStore()

  const pageData: any = usePageData()
  const data: any = reactive({
    id: 0,
    pageType: '0',
    addButton: false,
    headers: formatJson(pageData.record.headers),
    params: pageData.record.params,
    json: pageData.record.json,
    data: pageData.record.data,
    file: formatJson(pageData.record.file),
    posterior_func: pageData.record.posterior_func,
    posterior_json_path: pageData.record.posterior_json_path,
    posterior_re: pageData.record.posterior_re,
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
      data.posterior_json_path.push({ key: '', value: '' })
    } else if (data.pageType === '6') {
      data.posterior_re.push({ key: '', value: '' })
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
    let value = ''
    if (key === 'headers' || key === 'file') {
      try {
        if (value1) {
          const parsedValue = JSON.parse(value1)
          console.log(value1)
          if (typeof parsedValue === 'object') {
            value = parsedValue
          } else {
            Message.error(`请输入json格式的：${key}`)
            return
          }
        } else {
          value = null
        }
      } catch (e) {
        console.log(e)
        Message.error(`请输入json格式的：${key}`)
        return
      }
    } else {
      if (value1 === '') {
        value = null
      } else {
        value = value1
      }
    }
    putApiInfo({ id: pageData.record.id, [key]: value })
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
        data.headers = formatJson(res_data.headers)
        data.params = res_data.params
        data.json = res_data.json
        data.data = res_data.data
        data.file = formatJson(res_data.file)
        data.posterior_func = res_data.posterior_func
        data.posterior_json_path = res_data.posterior_json_path
        data.posterior_re = res_data.posterior_re
        data.result_data = res_data.result_data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      switchPageType()
    })
  })
</script>
<style scoped>
  .container .a-space span {
    font-size: 14px !important;
    display: block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
