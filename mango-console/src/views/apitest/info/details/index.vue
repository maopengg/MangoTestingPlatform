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
            <a-space direction="vertical" fill>
              <span class="form-tip">
                <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                提示：请必须输入json格式的请求头
              </span>
              <a-textarea
                v-model="data.headers"
                :auto-size="data.textareaAutoSize"
                allow-clear
                placeholder="请输入请求头，字符串形式"
                @blur="upDate('headers', data.headers)"
            /></a-space>
          </a-tab-pane>
          <a-tab-pane key="1" title="参数">
            <a-space direction="vertical" fill>
              <a-form layout="inline" :model="formState" style="margin-bottom: 8px">
                <a-form-item label="是否开启JSON输入：">
                  <a-switch
                    :default-checked="true"
                    disabled
                    checked-children="开启"
                    un-checked-children="关闭"
                  />
                </a-form-item>
                <a-form-item>
                  <span class="form-tip">
                    <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                    提示：当前必须输入json格式的请求参数，否则后续会提示错误
                  </span>
                </a-form-item>
              </a-form>
              <a-textarea
                v-model="data.api_info.params"
                :auto-size="data.textareaAutoSize"
                allow-clear
                placeholder='请输入json格式的数据，例如：{"key": "value"}'
                @blur="upDate('params', data.api_info.params)"
              />
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="2" title="表单">
            <a-space direction="vertical" fill>
              <a-form layout="inline" :model="formState" style="margin-bottom: 8px">
                <a-form-item label="是否开启JSON输入：">
                  <a-switch
                    :default-checked="true"
                    disabled
                    checked-children="开启"
                    un-checked-children="关闭"
                  />
                </a-form-item>
                <a-form-item>
                  <span class="form-tip">
                    <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                    提示：当前必须输入json格式的请求参数，否则后续会提示错误
                  </span>
                </a-form-item>
              </a-form>
              <a-textarea
                v-model="data.api_info.data"
                :auto-size="data.textareaAutoSize"
                allow-clear
                placeholder="请输入json格式的表单"
                @blur="upDate('data', data.api_info.data)"
              />
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="3" title="JSON">
            <a-space direction="vertical" fill>
              <a-form layout="inline" :model="formState" style="margin-bottom: 8px">
                <a-form-item label="是否开启JSON输入：">
                  <a-switch
                    :default-checked="true"
                    disabled
                    checked-children="开启"
                    un-checked-children="关闭"
                  />
                </a-form-item>
                <a-form-item>
                  <span class="form-tip">
                    <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                    提示：当前必须输入json格式的请求参数，否则后续会提示错误
                  </span>
                </a-form-item>
              </a-form>
              <a-textarea
                v-model="data.api_info.json"
                :auto-size="data.textareaAutoSize"
                allow-clear
                placeholder="请输入json格式的JSON"
                @blur="upDate('json', data.api_info.json)"
              />
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="4" title="文件">
            <a-space direction="vertical" fill>
              <a-form layout="inline" :model="formState" style="margin-bottom: 8px">
                <a-form-item label="是否开启JSON输入：">
                  <a-switch
                    :default-checked="true"
                    disabled
                    checked-children="开启"
                    un-checked-children="关闭"
                  />
                </a-form-item>
                <a-form-item>
                  <span class="form-tip">
                    <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                    提示：当前必须输入json格式的请求参数，否则后续会提示错误
                  </span>
                </a-form-item>
              </a-form>
              <a-row :gutter="16">
                <a-col :span="12">
                  <a-textarea
                    v-model="data.file"
                    :auto-size="data.textareaAutoSize"
                    allow-clear
                    placeholder="请输入json格式的上传文件"
                    style="width: 100%; height: 100%"
                    @blur="upDate('file1', data.file1)"
                  />
                </a-col>
                <a-col :span="12">
                  <a-textarea
                    v-model="data.fileDemo"
                    :auto-size="data.textareaAutoSize"
                    allow-clear
                    placeholder="示例"
                    style="width: 100%; height: 100%"
                    disabled
                  />
                </a-col>
              </a-row>
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="5" title="后置jsonpath提取">
            <a-space direction="vertical">
              <a-space v-for="(value, index) of data.api_info.posterior_json_path" :key="index">
                <a-input
                  v-model="data.api_info.posterior_json_path[index].key"
                  placeholder="请输入缓存key"
                  @blur="upDate('posterior_json_path', data.api_info.posterior_json_path)"
                />
                <a-input
                  v-model="data.api_info.posterior_json_path[index].value"
                  placeholder="请输入jsonpath语法"
                  @blur="upDate('posterior_json_path', data.api_info.posterior_json_path)"
                />

                <a-button
                  size="small"
                  status="danger"
                  type="text"
                  @click="
                    removeFrontSql(data.api_info.posterior_json_path, index, 'posterior_json_path')
                  "
                  >移除
                </a-button>
              </a-space>
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="6" title="后置正则提取">
            <a-space direction="vertical">
              <a-space v-for="(value, index) of data.api_info.posterior_re" :key="index">
                <a-input
                  v-model="data.api_info.posterior_re[index].key"
                  placeholder="请输入缓存key"
                  @blur="upDate('posterior_re', data.api_info.posterior_re)"
                />
                <a-input
                  v-model="data.api_info.posterior_re[index].value"
                  placeholder="请输入jsonpath语法"
                  @blur="upDate('posterior_re', data.api_info.posterior_re)"
                />

                <a-button
                  size="small"
                  status="danger"
                  type="text"
                  @click="removeFrontSql(data.api_info.posterior_re, index, 'posterior_re')"
                  >移除
                </a-button>
              </a-space>
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="7" title="后置函数">
            <a-textarea
              v-model="data.api_info.posterior_func"
              :auto-size="data.textareaAutoSize"
              allow-clear
              placeholder="根据帮助文档，输入自定义后置函数"
              @blur="upDate('posterior_func', data.api_info.posterior_func)"
            />
          </a-tab-pane>
          <a-tab-pane key="9" title="文件保存">
            <a-space>
              <a-input
                v-model="data.api_info.posterior_file"
                placeholder="请输入保存key，后续可以通过key取到文件路径"
                style="width: 500px"
                @blur="upDate('posterior_file', data.api_info.posterior_file)"
              />
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="8" title="响应结果">
            <a-tabs default-active-key="1">
              <a-tab-pane key="1" title="基础信息">
                <a-space direction="vertical">
                  <a-space>
                    <a-tag color="orange">响 应 码</a-tag>
                    <span>{{ data.api_info.result_data?.code }}</span>
                  </a-space>
                  <a-space>
                    <a-tag color="orange">响应时间</a-tag>
                    <span>{{ data.api_info.result_data?.time }}</span>
                  </a-space>
                  <a-space>
                    <a-tag color="orange">缓存数据</a-tag>
                    <JsonDisplay :data="data.api_info.result_data?.cache_all" />
                  </a-space>
                </a-space>
              </a-tab-pane>
              <a-tab-pane key="2" title="请求信息">
                <a-space direction="vertical">
                  <a-space v-if="data.api_info.result_data?.request_headers">
                    <a-tag color="orange">请求头</a-tag>
                    <JsonDisplay :data="data.api_info.result_data?.request_headers" />
                  </a-space>
                  <a-space v-if="data.api_info.result_data?.request_params">
                    <a-tag color="orange">参数</a-tag>
                    <JsonDisplay :data="data.api_info.result_data?.request_params" />
                  </a-space>
                  <a-space v-if="data.api_info.result_data?.request_data">
                    <a-tag color="orange">表单</a-tag>
                    <JsonDisplay :data="data.api_info.result_data?.request_data" />
                  </a-space>
                  <a-space v-if="data.api_info.result_data?.request_json">
                    <a-tag color="orange">json</a-tag>
                    <JsonDisplay :data="data.api_info.result_data?.request_json" />
                  </a-space>
                  <a-space v-if="data.api_info.result_data?.request_file">
                    <a-tag color="orange">file</a-tag>
                    <JsonDisplay :data="data.api_info.result_data?.request_file" />
                  </a-space>
                </a-space>
              </a-tab-pane>
              <a-tab-pane key="3" title="响应信息">
                <a-space direction="vertical">
                  <a-space>
                    <a-tag color="orange">响 应 体</a-tag>
                    <JsonDisplay
                      :data="
                        data.api_info.result_data?.json
                          ? data.api_info.result_data?.json
                          : data.api_info.result_data?.text
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
    api_info: pageData.record,
    headers: formatJson(pageData.record.headers),
    file: formatJson(pageData.record.file),
    textareaAutoSize: { minRows: 21, maxRows: 25 },
    fileDemo:
      '示例：' +
      formatJson([
        {
          file: '${{get_file(数据订阅新增模板.xlsx)}}',
        },
      ]),
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
      data.api_info.posterior_json_path.push({ key: '', value: '' })
    } else if (data.pageType === '6') {
      data.api_info.posterior_re.push({ key: '', value: '' })
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
        data.file = formatJson(res_data.file)
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
  .form-tip {
    color: #ff7d00;
    font-size: 12px;
    display: flex;
    align-items: center;
  }

  /* 如果需要调整表单间距 */
  :deep(.ant-form-inline .ant-form-item) {
    margin-right: 12px;
    margin-bottom: 0;
  }
</style>
