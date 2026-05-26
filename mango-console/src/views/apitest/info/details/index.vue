<template>
  <TableBody ref="tableBody" class="api-detail-workbench-page mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ apiDetailTitle }}</div>
          <div class="mango-detail-subtitle"> 维护请求配置、后置处理、断言和最近一次响应结果 </div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" status="success" :loading="caseRunning" @click="onRunCase">
            执行
          </a-button>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <div class="api-detail-workbench mango-detail-workbench">
        <aside class="api-detail-nav">
          <div class="api-detail-nav-head">
            <div class="api-detail-nav-title">配置项</div>
            <div class="api-detail-nav-subtitle">按执行链路维护接口配置</div>
          </div>
          <button
            v-for="item in configNavItems"
            :key="item.key"
            :class="[
              'api-detail-nav-item',
              {
                'api-detail-nav-item-active': data.pageType === item.key,
                'api-detail-nav-item-disabled': item.disabled,
              },
            ]"
            :disabled="item.disabled"
            type="button"
            @click="switchType(item.key)"
          >
            <span>{{ item.title }}</span>
            <small>{{ item.description }}</small>
          </button>
        </aside>

        <section class="api-detail-panel">
          <div class="api-request-bar">
            <a-select
              v-model="data.api_info.method"
              class="api-request-method"
              :options="methodOptions"
              placeholder="方法"
              @change="saveRequestMeta"
            />
            <a-input
              v-model="data.api_info.url"
              class="api-request-url"
              allow-clear
              placeholder="请输入接口路径，例如 /api/user/list"
              @blur="saveRequestMeta"
              @press-enter="saveRequestMeta"
            />
            <a-button
              class="api-request-save"
              type="primary"
              :loading="requestMetaSaving"
              @click="saveRequestMeta"
            >
              保存
            </a-button>
          </div>
          <div class="api-detail-panel-head">
            <div>
              <div class="api-detail-panel-title">{{ currentNavItem.title }}</div>
              <div class="api-detail-panel-subtitle">{{ currentNavItem.description }}</div>
            </div>
            <a-space v-if="data.addButton">
              <a-button size="small" type="primary" @click="addData">增加</a-button>
            </a-space>
          </div>
          <div class="api-detail-panel-body">
            <div v-if="data.pageType === '0'" class="config-pane">
              <a-space direction="vertical" fill>
                <TipMessage
                  message="请必须输入json格式的请求头，留空则默认使用请求头管理中开启的"
                />
                <a-textarea
                  v-model="data.headers"
                  :auto-size="data.textareaAutoSize"
                  allow-clear
                  placeholder="请输入请求头，字符串形式"
                  @blur="upDate('headers', data.headers)"
                />
              </a-space>
            </div>

            <div v-else-if="data.pageType === '1'" class="config-pane">
              <a-space direction="vertical" fill>
                <TipMessage message="建议输入json格式的参数" />
                <a-textarea
                  v-model="data.api_info.params"
                  :auto-size="data.textareaAutoSize"
                  allow-clear
                  placeholder='请输入json格式的数据，例如：{"key": "value"}'
                  @blur="upDate('params', data.api_info.params)"
                />
              </a-space>
            </div>

            <div v-else-if="data.pageType === '2'" class="config-pane">
              <a-space direction="vertical" fill>
                <TipMessage message="当前必须输入json格式的请求参数，否则请求时会提示错误" />

                <a-textarea
                  v-model="data.api_info.data"
                  :auto-size="data.textareaAutoSize"
                  allow-clear
                  placeholder="请输入json格式的表单"
                  @blur="upDate('data', data.api_info.data)"
                />
              </a-space>
            </div>

            <div v-else-if="data.pageType === '3'" class="config-pane">
              <a-space direction="vertical" fill>
                <TipMessage message="当前必须输入json格式的请求参数，否则请求时会提示错误" />

                <a-textarea
                  v-model="data.api_info.json"
                  :auto-size="data.textareaAutoSize"
                  allow-clear
                  placeholder="请输入json格式的JSON"
                  @blur="upDate('json', data.api_info.json)"
                />
              </a-space>
            </div>

            <div v-else-if="data.pageType === '4'" class="config-pane">
              <a-space direction="vertical" fill>
                <TipMessage message="当前必须输入json格式的请求参数，否则请求时会提示错误" />

                <a-row :gutter="16">
                  <a-col :span="12">
                    <a-textarea
                      v-model="data.file"
                      :auto-size="data.textareaAutoSize"
                      allow-clear
                      placeholder="请输入json格式的上传文件"
                      class="fill-editor"
                      @blur="upDate('file', data.file)"
                    />
                  </a-col>
                  <a-col :span="12">
                    <a-textarea
                      v-model="data.fileDemo"
                      :auto-size="data.textareaAutoSize"
                      allow-clear
                      placeholder="示例"
                      class="fill-editor"
                      disabled
                    />
                  </a-col>
                </a-row>
              </a-space>
            </div>

            <div v-else-if="data.pageType === '5'" class="config-pane">
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
            </div>

            <div v-else-if="data.pageType === '6'" class="config-pane">
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
            </div>

            <div v-else-if="data.pageType === '7'" class="config-pane">
              <CodeEditor
                v-model="data.api_info.posterior_func"
                :line-height="360"
                :code-style="{ width: '100%' }"
                placeholder="根据帮助文档，输入自定义后置函数"
                @focus="recordPosteriorFuncSnapshot"
                @blur="savePosteriorFuncIfChanged"
              />
            </div>

            <div v-else-if="data.pageType === '9'" class="config-pane">
              <a-space>
                <a-input
                  v-model="data.api_info.posterior_file"
                  placeholder="请输入保存key，后续可以通过key取到文件路径"
                  class="posterior-file-input"
                  @blur="upDate('posterior_file', data.api_info.posterior_file)"
                />
              </a-space>
            </div>

            <div v-else-if="data.pageType === '10'" class="config-pane">
              <a-space direction="vertical" fill>
                <TipMessage message="请参照帮助文档设置结构化断言配置" />
                <a-button
                  size="mini"
                  type="primary"
                  :loading="schemaLoading"
                  @click="setSchema(data.api_info.id)"
                  >自动生成</a-button
                >
                <a-textarea
                  v-model="data.ass_schema"
                  :auto-size="data.textareaAutoSize"
                  allow-clear
                  placeholder="根据帮助文档，输入结构化断言"
                  @blur="upDate('ass_schema', data.ass_schema)"
                />
              </a-space>
            </div>
          </div>
        </section>

        <aside class="api-response-panel">
          <div class="api-response-head">
            <div>
              <div class="api-response-title">调用结果</div>
              <div class="api-response-subtitle">执行后固定展示最近一次响应</div>
            </div>
            <a-button size="small" status="success" :loading="caseRunning" @click="onRunCase">
              执行
            </a-button>
          </div>
          <div class="api-response-summary">
            <div>
              <span>状态码</span>
              <strong>{{ data.api_info.result_data?.code || '-' }}</strong>
            </div>
            <div>
              <span>响应时间</span>
              <strong>{{ responseTimeText }}</strong>
            </div>
            <div>
              <span>执行状态</span>
              <a-tag size="small" :color="responseStatusColor">{{ responseStatusText }}</a-tag>
            </div>
          </div>
          <div v-if="data.api_info.result_data?.error_msg" class="api-response-error">
            {{ data.api_info.result_data.error_msg }}
          </div>
          <a-tabs default-active-key="response" class="api-response-tabs">
            <a-tab-pane key="response" title="响应">
              <div class="response-section">
                <div
                  v-if="
                    data.api_info.result_data?.headers &&
                    Object.keys(data.api_info.result_data.headers).length > 0
                  "
                  class="response-item"
                >
                  <span class="response-label">响应头</span>
                  <div class="response-value">
                    <JsonDisplay
                      :data="data.api_info.result_data.headers"
                      :default-expanded="false"
                    />
                  </div>
                </div>
                <div class="response-item">
                  <span class="response-label">响应体</span>
                  <div class="response-value">
                    <JsonDisplay
                      :data="data.api_info.result_data?.json || data.api_info.result_data?.text"
                    />
                  </div>
                </div>
              </div>
            </a-tab-pane>
            <a-tab-pane key="request" title="请求">
              <div class="response-section">
                <div v-if="data.api_info.result_data?.url" class="response-item">
                  <span class="response-label">URL</span>
                  <span class="response-value">{{ data.api_info.result_data.url }}</span>
                </div>
                <div
                  v-if="
                    data.api_info.result_data?.request_headers &&
                    Object.keys(data.api_info.result_data.request_headers).length > 0
                  "
                  class="response-item"
                >
                  <span class="response-label">请求头</span>
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
                  <span class="response-label">查询参数</span>
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
                  <span class="response-label">表单数据</span>
                  <div class="response-value">
                    <JsonDisplay :data="data.api_info.result_data.request_data" />
                  </div>
                </div>
                <div v-if="data.api_info.result_data?.request_json" class="response-item">
                  <span class="response-label">JSON</span>
                  <div class="response-value">
                    <JsonDisplay :data="data.api_info.result_data.request_json" />
                  </div>
                </div>
                <div v-if="data.api_info.result_data?.request_file" class="response-item">
                  <span class="response-label">文件</span>
                  <div class="response-value">
                    <JsonDisplay :data="data.api_info.result_data.request_file" />
                  </div>
                </div>
              </div>
            </a-tab-pane>
            <a-tab-pane key="cache" title="缓存">
              <JsonDisplay :data="data.api_info.result_data?.cache_all" />
            </a-tab-pane>
          </a-tabs>
        </aside>
      </div>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { getApiCaseInfoRun, getApiInfo, putApiInfo, putSetSchema } from '@/api/apitest/info'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import KeyValueList from '@/components/forms/KeyValueList.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'

  const userStore = useUserStore()
  const enumStore = useEnum()
  const caseRunning = ref(false)
  const requestMetaSaving = ref(false)
  const schemaLoading = ref(false)
  const requestMetaSnapshot = ref({ method: null as any, url: '' })
  const posteriorFuncSnapshot = ref('')
  const configNavItems = [
    { key: '0', title: '请求头', description: '维护接口请求 Headers' },
    { key: '1', title: '参数', description: '维护查询参数' },
    { key: '2', title: '表单', description: '维护 form-data 请求体' },
    { key: '3', title: 'JSON', description: '维护 JSON 请求体' },
    { key: '4', title: '文件', description: '维护上传文件配置' },
    { key: '5', title: '后置jsonpath提取', description: '提取响应 JSON 到缓存' },
    { key: '6', title: '后置正则提取', description: '通过正则提取响应内容' },
    { key: '7', title: '后置函数', description: '编写自定义后置函数' },
    { key: '9', title: '文件保存', description: '保存响应文件路径', disabled: true },
    { key: '10', title: '结构化断言配置', description: '维护结构化断言规则' },
  ]
  const POSTERIOR_FUNC_TEMPLATE = `def func(self, response):
    print(response.model_dump_json())
    # 可以从response中获取值，然后修改完成之后重新赋值给response，最后进行返回
    code = response.code  # 获取响应code码
    time = response.time  # 获取响应时间
    headers = response.headers  # 获取响应头
    print(response.headers.get('Set-Cookie'))
    json = response.json  # 获取响应的json
    text = response.text  # 获取响应的文本
    return response`

  const pageData: any = usePageData()
  const data: any = reactive({
    id: 0,
    pageType: '0',
    addButton: false,
    api_info: pageData.record,
    headers: formatJson(pageData.record.headers),
    file: formatJson(pageData.record.file),
    ass_schema: formatJson(pageData.record.ass_schema),
    textareaAutoSize: { minRows: 16, maxRows: 22 },
    fileDemo:
      '示例：' +
      formatJson([
        {
          file: '${{get_file(数据订阅新增模板.xlsx)}}',
        },
      ]),
  })
  const currentNavItem = computed(
    () =>
      configNavItems.find((item) => item.key === data.pageType) || {
        key: data.pageType,
        title: '接口配置',
        description: '维护接口配置',
      }
  )
  const apiDetailTitle = computed(() => {
    const id = data.api_info?.id || pageData.record?.id || '-'
    const name = data.api_info?.name || pageData.record?.name || '-'
    return `接口配置工作台 / ${id} / ${name}`
  })
  const methodOptions = computed(() => {
    const methods = Array.isArray(enumStore.method) ? enumStore.method : []
    if (methods.length > 0) {
      return methods.map((item: any) => ({
        label: item.title,
        value: item.key,
      }))
    }
    return [
      { label: 'GET', value: 0 },
      { label: 'POST', value: 1 },
      { label: 'PUT', value: 2 },
      { label: 'DELETE', value: 3 },
      { label: 'PATCH', value: 4 },
    ]
  })
  const responseTimeText = computed(() => {
    const time = data.api_info?.result_data?.time
    if (time === undefined || time === null || time === '') return '-'
    const value = Number(time)
    return Number.isFinite(value) ? `${value.toFixed(2)} 秒` : `${time} 秒`
  })
  const responseStatusText = computed(() => {
    if (data.api_info?.result_data?.error_msg) return '调用失败'
    if (data.api_info?.result_data?.code) return '调用完成'
    return '未执行'
  })
  const responseStatusColor = computed(() => {
    if (data.api_info?.result_data?.error_msg) return 'red'
    if (data.api_info?.result_data?.code) return 'green'
    return 'gray'
  })

  function switchType(key: any) {
    const navItem = configNavItems.find((item) => item.key === key)
    if (navItem?.disabled) return
    data.pageType = key
    if (key === '7' && !data.api_info.posterior_func) {
      data.api_info.posterior_func = POSTERIOR_FUNC_TEMPLATE
      recordPosteriorFuncSnapshot()
    }
    if (data.pageType === '5' || data.pageType === '6') {
      data.addButton = true
    } else {
      data.addButton = false
    }
  }

  function normalizeCodeValue(value: string | null | undefined) {
    return value || ''
  }

  function recordPosteriorFuncSnapshot() {
    posteriorFuncSnapshot.value = normalizeCodeValue(data.api_info.posterior_func)
  }

  function savePosteriorFuncIfChanged() {
    const currentValue = normalizeCodeValue(data.api_info.posterior_func)
    if (currentValue === posteriorFuncSnapshot.value) {
      return
    }
    posteriorFuncSnapshot.value = currentValue
    upDate('posterior_func', data.api_info.posterior_func)
  }

  function addData() {
    if (data.pageType === '5') {
      data.api_info.posterior_json_path.push({ key: '', value: '' })
    } else if (data.pageType === '6') {
      data.api_info.posterior_re.push({ key: '', value: '' })
    }
  }

  function hasConfigValue(value: any) {
    if (value === undefined || value === null) return false
    if (typeof value === 'string') {
      const text = value.trim()
      return text !== '' && text !== '{}' && text !== '[]'
    }
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value).length > 0
    return Boolean(value)
  }

  function switchPageType() {
    const record = data.api_info || pageData.record || {}
    if (hasConfigValue(record.params)) {
      data.pageType = '1'
    } else if (hasConfigValue(record.data)) {
      data.pageType = '2'
    } else if (hasConfigValue(record.json)) {
      data.pageType = '3'
    } else if (hasConfigValue(record.file)) {
      data.pageType = '4'
    } else {
      data.pageType = '3'
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

  function syncRequestMetaSnapshot() {
    requestMetaSnapshot.value = {
      method: data.api_info?.method,
      url: data.api_info?.url || '',
    }
  }

  function requestMetaChanged() {
    return (
      data.api_info?.method !== requestMetaSnapshot.value.method ||
      (data.api_info?.url || '') !== requestMetaSnapshot.value.url
    )
  }

  function validateRequestPath(url: string) {
    const value = (url || '').trim()
    if (!value) {
      Message.error('请输入接口路径')
      return false
    }
    if (value.toLowerCase().startsWith('http')) {
      Message.error('只允许输入 URL 的路径部分，协议和域名从测试环境中读取')
      return false
    }
    return true
  }

  async function saveRequestMeta() {
    if (requestMetaSaving.value) return
    if (!requestMetaChanged()) return
    if (
      data.api_info.method === undefined ||
      data.api_info.method === null ||
      data.api_info.method === ''
    ) {
      Message.error('请选择请求方法')
      return
    }
    if (!validateRequestPath(data.api_info.url)) return
    requestMetaSaving.value = true
    try {
      const res = await putApiInfo({
        id: pageData.record.id,
        method: data.api_info.method,
        url: data.api_info.url.trim(),
      })
      Message.success(res.msg)
      syncRequestMetaSnapshot()
      doRefresh()
    } catch (e) {
      console.log(e)
    } finally {
      requestMetaSaving.value = false
    }
  }

  function upDate(key: string, value1: string) {
    let value = ''
    if (key === 'headers' || key === 'file' || key === 'ass_schema') {
      try {
        if (value1) {
          const parsedValue = JSON.parse(value1)
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
        data.ass_schema = formatJson(res_data.ass_schema)
        syncRequestMetaSnapshot()
      })
      .catch(console.log)
  }

  function setSchema(id: number) {
    if (schemaLoading.value) return
    schemaLoading.value = true
    putSetSchema(id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
      .finally(() => {
        schemaLoading.value = false
      })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      switchPageType()
      syncRequestMetaSnapshot()
    })
  })
</script>
<style scoped>
  .api-detail-workbench {
    display: grid;
    grid-template-columns: 200px minmax(360px, 0.95fr) minmax(480px, 1.15fr);
    gap: 12px;
    height: calc(100vh - 166px);
    min-height: 0;
  }

  .api-detail-nav,
  .api-detail-panel,
  .api-response-panel {
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .api-detail-nav {
    display: flex;
    overflow: auto;
    flex-direction: column;
    padding: 12px;
  }

  .api-detail-nav-head {
    flex-shrink: 0;
    margin-bottom: 10px;
  }

  .api-detail-nav-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .api-detail-nav-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .api-detail-nav-item {
    display: block;
    width: 100%;
    margin: 0 0 8px;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    cursor: pointer;
    text-align: left;
    transition: border-color 0.2s ease, background 0.2s ease;
  }

  .api-detail-nav-item:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    background: var(--m-surface);
  }

  .api-detail-nav-item-disabled,
  .api-detail-nav-item-disabled:hover {
    border-color: var(--m-border);
    background: var(--m-surface-soft);
    cursor: not-allowed;
    opacity: 0.52;
  }

  .api-detail-nav-item-active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
  }

  .api-detail-nav-item span,
  .api-detail-nav-item small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-detail-nav-item span {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .api-detail-nav-item small {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .api-detail-panel {
    display: flex;
    overflow: hidden;
    flex-direction: column;
  }

  .api-request-bar {
    display: grid;
    grid-template-columns: 112px minmax(0, 1fr) max-content;
    gap: 8px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .api-request-method,
  .api-request-url {
    min-width: 0;
  }

  .api-request-save {
    min-width: 64px;
  }

  .api-detail-panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .api-detail-panel-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .api-detail-panel-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .api-detail-panel-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 12px;
  }

  .api-response-panel {
    display: flex;
    overflow: hidden;
    flex-direction: column;
  }

  .api-response-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .api-response-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .api-response-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .api-response-summary {
    display: grid;
    flex-shrink: 0;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    padding: 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .api-response-summary > div {
    min-width: 0;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .api-response-summary span {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .api-response-summary strong {
    display: block;
    overflow: hidden;
    margin-top: 3px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-response-error {
    flex-shrink: 0;
    margin: 12px 12px 0;
    padding: 8px 10px;
    border: 1px solid color-mix(in srgb, var(--m-danger) 28%, var(--m-border));
    border-radius: var(--m-radius-sm);
    background: color-mix(in srgb, var(--m-danger) 8%, var(--m-surface));
    color: var(--m-danger);
    font-size: 12px;
    line-height: 18px;
    word-break: break-word;
  }

  .api-response-tabs {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    padding: 0 12px 12px;
  }

  .api-response-tabs :deep(.arco-tabs-content) {
    height: calc(100% - 42px);
    min-height: 0;
    padding-top: 8px;
  }

  .api-response-tabs :deep(.arco-tabs-content-list),
  .api-response-tabs :deep(.arco-tabs-content-item),
  .api-response-tabs :deep(.arco-tabs-pane) {
    height: 100%;
    min-height: 0;
  }

  .config-pane {
    min-width: 0;
  }

  .fill-editor {
    width: 100%;
    height: 100%;
  }

  .posterior-file-input {
    width: min(500px, 100%);
  }

  .response-section {
    height: 100%;
    overflow: auto;
    padding: 0;
    background-color: var(--m-surface);
  }

  .response-item {
    display: block;
    margin-bottom: 12px;
    padding: 10px 12px;
    background-color: var(--m-surface-soft);
    border-radius: var(--m-radius-md);
    border: 1px solid var(--m-border);
    transition: all 0.2s ease;
  }

  .response-item:hover {
    background-color: var(--m-surface);
    border-color: var(--m-border-strong);
    box-shadow: var(--m-shadow);
  }

  .response-item:last-child {
    margin-bottom: 0;
  }

  .response-label {
    display: block;
    font-weight: 500;
    color: var(--m-text);
    margin-bottom: 8px;
    font-size: 13px;
    line-height: 20px;
  }

  .response-value {
    display: block;
    min-width: 0;
    word-break: break-word;
    font-size: 13px;
    color: var(--m-text-2);
  }

  .error-item {
    background-color: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface));
    border-color: color-mix(in srgb, var(--m-warning) 34%, transparent);
  }

  .error-item .response-label {
    color: var(--m-warning);
  }

  .error-item:hover {
    background-color: color-mix(in srgb, var(--m-warning) 16%, var(--m-surface));
  }

  @media (max-width: 1px) {
    .api-detail-workbench {
      grid-template-columns: 190px minmax(340px, 0.9fr) minmax(430px, 1.1fr);
    }
  }

  @media (max-width: 1px) {
    .api-detail-workbench {
      grid-template-columns: 200px minmax(0, 1fr);
      height: auto;
    }

    .api-response-panel {
      grid-column: 1 / -1;
      min-height: 520px;
    }
  }

  @media (max-width: 1px) {
    .api-detail-workbench {
      grid-template-columns: 1fr;
      height: auto;
    }

    .api-detail-nav {
      max-height: none;
    }

    .api-detail-panel {
      min-height: 520px;
    }

    .api-request-bar {
      grid-template-columns: 104px minmax(0, 1fr);
    }

    .api-request-save {
      grid-column: 1 / -1;
      width: 100%;
    }

    .api-response-panel {
      grid-column: auto;
    }

    .api-response-summary {
      grid-template-columns: 1fr;
    }
  }
</style>
