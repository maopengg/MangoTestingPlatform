<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="接口详情">
        <template #extra>
          <a-space>
            <a-button size="small" status="success" :loading="caseRunning" @click="onRunCase"
              >执行</a-button
            >
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
              />
            </a-space>
          </a-tab-pane>
          <a-tab-pane key="1" title="参数">
            <a-space direction="vertical" fill>
              <div class="form-tip">
                <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                提示：当前必须输入json格式的请求参数，否则后续会提示错误
              </div>
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
              <div class="form-tip">
                <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                提示：当前必须输入json格式的请求参数，否则后续会提示错误
              </div>
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
              <div class="form-tip">
                <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                提示：当前必须输入json格式的请求参数，否则后续会提示错误
              </div>
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
              <div class="form-tip">
                <icon-info-circle style="margin-right: 4px; color: #ff7d00" />
                提示：当前必须输入json格式的请求参数，否则后续会提示错误
              </div>
              <a-row :gutter="16">
                <a-col :span="12">
                  <a-textarea
                    v-model="data.file"
                    :auto-size="data.textareaAutoSize"
                    allow-clear
                    placeholder="请输入json格式的上传文件"
                    style="width: 100%; height: 100%"
                    @blur="upDate('file', data.file)"
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
            <KeyValueList
              :data-list="data.api_info.posterior_json_path"
              :field-config="[
                { field: 'key', label: '缓存key', placeholder: '请输入缓存key' },
                { field: 'value', label: 'jsonpath语法', placeholder: '请输入jsonpath语法' },
              ]"
              :on-delete-item="
                (index) =>
                  removeFrontSql(data.api_info.posterior_json_path, index, 'posterior_json_path')
              "
              :on-save="() => upDate('posterior_json_path', data.api_info.posterior_json_path)"
            />
          </a-tab-pane>
          <a-tab-pane key="6" title="后置正则提取">
            <KeyValueList
              :data-list="data.api_info.posterior_re"
              :field-config="[
                { field: 'key', label: '缓存key', placeholder: '请输入缓存key' },
                { field: 'value', label: '正则表达式', placeholder: '请输入正则表达式' },
              ]"
              :on-delete-item="
                (index) => removeFrontSql(data.api_info.posterior_re, index, 'posterior_re')
              "
              :on-save="() => upDate('posterior_re', data.api_info.posterior_re)"
            />
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
            <a-tabs default-active-key="3">
              1
              <a-tab-pane key="2" title="请求信息">
                <div class="response-section">
                  <div
                    v-if="
                      data.api_info.result_data?.request_headers &&
                      Object.keys(data.api_info.result_data.request_headers).length > 0
                    "
                    class="response-item"
                  >
                    <span class="response-label">请求头：</span>
                    <div class="response-value">
                      <JsonDisplay :data="data.api_info.result_data.request_headers" />
                    </div>
                  </div>
                  <div
                    v-if="
                      data.api_info.result_data?.request_params &&
                      Object.keys(data.api_info.result_data.request_params).length > 0
                    "
                    class="response-item"
                  >
                    <span class="response-label">查询参数：</span>
                    <div class="response-value">
                      <JsonDisplay :data="data.api_info.result_data.request_params" />
                    </div>
                  </div>
                  <div
                    v-if="
                      data.api_info.result_data?.request_data &&
                      Object.keys(data.api_info.result_data.request_data).length > 0
                    "
                    class="response-item"
                  >
                    <span class="response-label">表单数据：</span>
                    <div class="response-value">
                      <JsonDisplay :data="data.api_info.result_data.request_data" />
                    </div>
                  </div>
                  <div v-if="data.api_info.result_data?.request_json" class="response-item">
                    <span class="response-label">JSON数据：</span>
                    <div class="response-value">
                      <JsonDisplay :data="data.api_info.result_data.request_json" />
                    </div>
                  </div>
                  <div v-if="data.api_info.result_data?.request_file" class="response-item">
                    <span class="response-label">文件数据：</span>
                    <div class="response-value">
                      <JsonDisplay :data="data.api_info.result_data.request_file" />
                    </div>
                  </div>
                  <div v-if="data.api_info.result_data?.url" class="response-item">
                    <span class="response-label">请求URL：</span>
                    <span class="response-value">{{ data.api_info.result_data.url }}</span>
                  </div>
                </div>
              </a-tab-pane>
              <a-tab-pane key="3" title="响应信息">
                <div class="response-section">
                  <div class="response-item">
                    <span class="response-label">响应状态：</span>
                    <span class="response-value">{{ data.api_info.result_data?.code }}</span>
                  </div>
                  <div class="response-item">
                    <span class="response-label">响应时间：</span>
                    <span class="response-value">{{ data.api_info.result_data?.time }} 秒</span>
                  </div>
                  <div v-if="data.api_info.result_data?.error_msg" class="response-item error-item">
                    <span class="response-label">失败提示：</span>
                    <span class="response-value">{{ data.api_info.result_data.error_msg }}</span>
                  </div>
                  <div
                    v-if="
                      data.api_info.result_data?.headers &&
                      Object.keys(data.api_info.result_data.headers).length > 0
                    "
                    class="response-item"
                  >
                    <span class="response-label">响应头：</span>
                    <div class="response-value">
                      <JsonDisplay :data="data.api_info.result_data.headers" />
                    </div>
                  </div>
                  <div class="response-item">
                    <span class="response-label">响应体：</span>
                    <div class="response-value">
                      <JsonDisplay
                        :data="data.api_info.result_data?.json || data.api_info.result_data?.text"
                      />
                    </div>
                  </div>
                </div>
              </a-tab-pane>
              <a-tab-pane key="4" title="缓存数据">
                <div class="response-section">
                  <div class="response-item">
                    <span class="response-label">缓存内容：</span>
                    <div class="response-value">
                      <JsonDisplay :data="data.api_info.result_data?.cache_all" />
                    </div>
                  </div>
                </div>
              </a-tab-pane>
            </a-tabs>
          </a-tab-pane>
        </a-tabs>
      </a-card>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { getApiCaseInfoRun, getApiInfo, putApiInfo } from '@/api/apitest/info'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import KeyValueList from '@/components/KeyValueList.vue'

  const enumStore = useEnum()
  const userStore = useUserStore()
  const caseRunning = ref(false)

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

  const onRunCase = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    Message.loading('接口开始执行中~')
    try {
      const res = await getApiCaseInfoRun(pageData.record.id, userStore.selected_environment)
      data.caseResult = res.data
      if (res.data.error_msg) {
        Message.error(res.data.error_msg)
      } else {
        Message.success(res.msg)
      }
    } catch (e) {
      doRefresh()
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  function doRefresh() {
    getApiInfo({ id: pageData.record.id })
      .then((res) => {
        const res_data = res.data[0]
        data.api_info = res_data
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

  /* 响应信息样式 */
  .response-section {
    padding: 16px;
    background-color: var(--color-bg-2);
    border-radius: 4px;
  }

  .response-item {
    display: flex;
    margin-bottom: 12px;
    padding: 12px 16px;
    background-color: var(--color-fill-1);
    border-radius: 4px;
    border: 1px solid var(--color-neutral-3);
    transition: all 0.2s ease;
  }

  .response-item:hover {
    background-color: var(--color-fill-2);
    border-color: var(--color-neutral-4);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .response-item:last-child {
    margin-bottom: 0;
  }

  .response-label {
    font-weight: 500;
    color: var(--color-text-1);
    min-width: 100px;
    margin-right: 16px;
    flex-shrink: 0;
    font-size: 14px;
  }

  .response-value {
    flex: 1;
    word-break: break-word;
    font-size: 14px;
    color: var(--color-text-2);
  }

  .error-item {
    background-color: #fff7e6;
    border-color: #ffdfb8;
  }

  .error-item .response-label {
    color: #ff7d00;
  }

  .error-item:hover {
    background-color: #fff2e8;
  }

  /* 如果需要调整表单间距 */
  :deep(.ant-form-inline .ant-form-item) {
    margin-right: 12px;
    margin-bottom: 0;
  }

  /* 确保KeyValueList中的所有元素都在一行 */
  :deep(.key-value-row) {
    flex-wrap: nowrap;
    align-items: flex-start;
    width: 100%;
    min-width: 0; /* 允许子元素收缩 */
    overflow-x: hidden; /* 防止水平滚动 */
  }

  :deep(.key-value-field) {
    flex: 1;
    min-width: 100px; /* 减小最小宽度 */
    overflow: hidden; /* 防止内容溢出 */
  }

  :deep(.button-container) {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    flex-shrink: 0;
    white-space: nowrap; /* 防止按钮内文字换行 */
    min-width: fit-content; /* 确保按钮容器不会收缩 */
  }

  :deep(.remove-btn) {
    flex-shrink: 0;
    margin-top: 18px;
    min-width: fit-content; /* 确保按钮不会收缩 */
  }

  /* 响应式处理：在小屏幕上允许换行，但保持按钮在同一行 */
  @media (max-width: 768px) {
    :deep(.key-value-row) {
      flex-wrap: wrap;
    }

    :deep(.key-value-field) {
      min-width: 120px;
    }

    :deep(.button-container) {
      width: 100%;
      justify-content: flex-end;
      margin-top: 8px;
    }

    :deep(.remove-btn) {
      margin-top: 0;
      align-self: center;
    }
  }
</style>
