<template>
  <TableBody ref="tableBody" class="api-detail-workbench-page mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ apiDetailTitle }}</div>
          <div class="mango-detail-subtitle"> 维护请求配置、后置处理、断言和最近一次响应结果 </div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button v-permission="'api.info:execute'"
            size="small"
            status="success"
            :loading="caseRunning"
            @click="onRunCase"
            data-testid="qa-views-apitest-info-details-button-执行"
          >
            执行
          </a-button>
          <a-button
            v-if="canCopyApiInfoCurl(data.api_info)"
            size="small"
            :loading="copyingId === String(data.api_info.id)"
            @click="
              copyApiInfoCurl(
                { ...data.api_info, headers: data.headers },
                userStore.selected_environment
              )
            "
            >复制 cURL</a-button
          >
          <a-button
            size="small"
            @click="versionPanelRef?.openResultHistoryDrawer()"
            data-testid="qa-views-apitest-info-details-button-历史结果"
          >
            历史结果
          </a-button>
          <VariableReferencePanel />
          <a-button
            class="mango-back-button"
            size="small"
            @click="doResetSearch"
            data-testid="qa-views-apitest-info-details-button-返回"
            >返回</a-button
          >
        </a-space>
      </div>
    </template>
    <template #default>
      <div class="mango-workbench-scroll-x api-detail-workbench-scroll">
        <div class="api-detail-workbench mango-detail-workbench">
          <ApiInfoVersionPanel
            ref="versionPanelRef"
            :api-info-id="apiInfoId"
            :current-payload="currentApiInfoPayload"
            @select="handleApiVersionSelect"
          />
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

          <section
            class="api-detail-panel"
            :class="{ 'api-detail-panel-readonly': apiVersionReadOnly }"
          >
            <div class="api-request-bar">
              <a-select
                v-model="data.api_info.method"
                class="api-request-method"
                :options="methodOptions"
                :disabled="apiVersionReadOnly"
                placeholder="方法"
                data-testid="qa-views-apitest-info-details-select-方法"
              />
              <a-input
                v-model="data.api_info.url"
                class="api-request-url"
                allow-clear
                :disabled="apiVersionReadOnly"
                placeholder="请输入接口路径，例如 /api/user/list"
                @press-enter="saveRequestMeta"
                data-testid="qa-views-apitest-info-details-input-请输入接口路径-例如-api-user-list"
              />
              <a-button v-permission="['api.info:create', 'api.info:edit']"
                class="api-request-save"
                type="primary"
                :loading="requestMetaSaving"
                :disabled="apiVersionReadOnly"
                @click="saveRequestMeta"
                data-testid="qa-views-apitest-info-details-button-保存"
              >
                保存
              </a-button>
            </div>
            <div
              class="api-version-context"
              :class="{ readonly: apiVersionReadOnly }"
              role="status"
              aria-live="polite"
            >
              <div>
                <strong>{{ executionVersionTitle }}</strong>
                <span>{{ executionVersionDescription }}</span>
              </div>
              <a-tag size="small" :color="apiVersionReadOnly ? 'gray' : 'orange'">
                {{ apiVersionReadOnly ? '固定版本' : '编辑态' }}
              </a-tag>
            </div>
            <div class="api-detail-panel-head">
              <div>
                <div class="api-detail-panel-title">
                  <span>{{ currentNavItem.title }}</span>
                  <a-tag v-if="apiVersionReadOnly" size="small" color="gray">只读快照</a-tag>
                </div>
                <div class="api-detail-panel-subtitle">{{ currentNavItem.description }}</div>
              </div>
              <a-space v-if="data.addButton && !apiVersionReadOnly">
                <a-button
                  size="small"
                  type="primary"
                  @click="addData"
                  data-testid="qa-views-apitest-info-details-button-增加"
                  >增加</a-button
                >
              </a-space>
            </div>
            <div class="api-detail-panel-body">
              <div v-if="data.pageType === '0'" class="config-pane">
                <a-space direction="vertical" fill>
                  <TipMessage
                    message="请求头必须为 JSON 格式。留空时默认使用请求头管理中已开启的请求头；获取 Token 等授权接口请填写 {}，避免公共 Authorization 引用待生成 Token 造成循环引用。"
                  />
                  <a-textarea
                    v-model="data.headers"
                    :auto-size="data.textareaAutoSize"
                    allow-clear
                    :disabled="apiVersionReadOnly"
                    placeholder='请输入 JSON 格式的请求头，例如：{"Content-Type": "application/json"}'
                    @blur="saveHeaders"
                    data-testid="qa-views-apitest-info-details-textarea-请输入-json-格式的请求头-例如-content-type-application-json"
                  />
                  <div v-if="data.isDefaultHeadersPreview" class="default-headers-preview">
                    <div class="default-headers-preview-title">请求头管理中已开启的 Headers</div>
                    <pre>{{ data.defaultHeadersText }}</pre>
                  </div>
                </a-space>
              </div>

              <div v-else-if="data.pageType === '1'" class="config-pane">
                <a-space direction="vertical" fill>
                  <TipMessage
                    message="支持 JSON 对象/数组，也支持 query string，例如：case_id=21"
                  />
                  <a-textarea
                    v-model="data.api_info.params"
                    :auto-size="data.textareaAutoSize"
                    allow-clear
                    :disabled="apiVersionReadOnly"
                    placeholder='请输入查询参数，例如：{"key": "value"} 或 case_id=21'
                    @blur="upDate('params', data.api_info.params)"
                    data-testid="qa-views-apitest-info-details-textarea-请输入查询参数-例如-key-value-或-case_id-21"
                  />
                </a-space>
              </div>

              <div v-else-if="data.pageType === '2'" class="config-pane">
                <ApiRequestBodyEditor
                  :protocol-type="data.api_info.protocol_type"
                  :body-type="data.api_info.body_type"
                  :body-config="data.api_info.body_config"
                  :sse-config="data.api_info.sse_config"
                  :project-product-id="projectProductId"
                  :saving="requestBodySaving"
                  :readonly="apiVersionReadOnly"
                  @save="saveRequestBody"
                />
              </div>

              <div
                v-else-if="data.pageType === '5'"
                class="config-pane mango-horizontal-scroll-region mango-horizontal-scroll-region--compact"
              >
                <KeyValueList
                  :data-list="data.api_info.posterior_json_path"
                  :field-config="[
                    { field: 'key', label: '缓存key', placeholder: '请输入缓存key' },
                    { field: 'value', label: 'jsonpath语法', placeholder: '请输入jsonpath语法' },
                  ]"
                  :on-delete-item="
                    (index) =>
                      removeFrontSql(
                        data.api_info.posterior_json_path,
                        index,
                        'posterior_json_path'
                      )
                  "
                  :on-save="() => upDate('posterior_json_path', data.api_info.posterior_json_path)"
                />
              </div>

              <div
                v-else-if="data.pageType === '6'"
                class="config-pane mango-horizontal-scroll-region mango-horizontal-scroll-region--compact"
              >
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
            </div>
          </section>

          <aside class="api-response-panel">
            <div class="api-response-head">
              <div>
                <div class="api-response-title">调用结果</div>
                <div class="api-response-subtitle">执行后固定展示最近一次响应</div>
              </div>
              <a-spin v-if="resultLoading" :loading="true" />
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
              <a-tab-pane
                key="response"
                title="响应"
                data-testid="qa-views-apitest-info-details-tab-pane-响应"
              >
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
                      <JsonDisplay :data="responseBodyData" />
                    </div>
                  </div>
                </div>
              </a-tab-pane>
              <a-tab-pane
                key="request"
                title="请求"
                data-testid="qa-views-apitest-info-details-tab-pane-请求"
              >
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
                    v-if="hasValue(data.api_info.result_data?.request_body)"
                    class="response-item"
                  >
                    <span class="response-label">请求体</span>
                    <div class="response-value">
                      <JsonDisplay :data="data.api_info.result_data.request_body" />
                    </div>
                  </div>
                  <div class="response-item">
                    <span class="response-label">请求类型</span>
                    <span class="response-value">
                      {{ data.api_info.result_data?.request_protocol_type || '-' }} /
                      {{ data.api_info.result_data?.request_body_type || '-' }}
                    </span>
                  </div>
                </div>
              </a-tab-pane>
              <a-tab-pane
                v-if="hasValue(data.api_info.result_data?.sse_events)"
                key="sse"
                title="SSE"
                data-testid="qa-views-apitest-info-details-tab-pane-sse"
              >
                <JsonDisplay :data="data.api_info.result_data?.sse_events" />
              </a-tab-pane>
              <a-tab-pane
                v-if="hasValue(data.api_info.result_data?.ws_messages)"
                key="websocket"
                title="WebSocket"
                data-testid="qa-views-apitest-info-details-tab-pane-websocket"
              >
                <JsonDisplay
                  :data="{
                    stop_reason: data.api_info.result_data?.ws_stop_reason,
                    close_code: data.api_info.result_data?.ws_close_code,
                    close_reason: data.api_info.result_data?.ws_close_reason,
                    messages: data.api_info.result_data?.ws_messages,
                  }"
                />
              </a-tab-pane>
              <a-tab-pane
                v-if="data.api_info.result_data?.response_mode === 'grpc'"
                key="grpc"
                title="gRPC"
                data-testid="qa-views-apitest-info-details-tab-pane-grpc"
              >
                <JsonDisplay
                  :data="{
                    full_method: data.api_info.result_data?.grpc_full_method,
                    status_code: data.api_info.result_data?.grpc_status_code,
                    status_details: data.api_info.result_data?.grpc_status_details,
                    initial_metadata: data.api_info.result_data?.grpc_initial_metadata,
                    trailing_metadata: data.api_info.result_data?.grpc_trailing_metadata,
                    request_message: data.api_info.result_data?.request_body,
                    response_message: data.api_info.result_data?.json,
                  }"
                />
              </a-tab-pane>
              <a-tab-pane
                v-if="hasValue(data.api_info.result_data?.cache_all)"
                key="cache"
                title="缓存"
                data-testid="qa-views-apitest-info-details-tab-pane-缓存"
              >
                <JsonDisplay :data="data.api_info.result_data?.cache_all" />
              </a-tab-pane>
            </a-tabs>
          </aside>
        </div>
      </div>
    </template>
  </TableBody>
  <ApiInfoRuntimeParametersModal ref="runtimeParametersRef" />
</template>
<script lang="ts" setup>
  import ApiInfoRuntimeParametersModal from '@/components/business/ApiInfoRuntimeParametersModal.vue'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import { usePageData } from '@/store/page-data'
  import { getApiCaseInfoRun, getApiInfo, putApiInfo } from '@/api/apitest/info'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import KeyValueList from '@/components/forms/KeyValueList.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import ApiInfoVersionPanel from './components/ApiInfoVersionPanel.vue'
  import ApiRequestBodyEditor from '../../components/ApiRequestBodyEditor.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import { getApiHeaders } from '@/api/apitest/headers'
  import { canCopyApiInfoCurl, useApiInfoCurl } from '../useApiInfoCurl'
  import {
    getExecutionResultDetailResolved,
    getExecutionResultLatestResolved,
  } from '@/api/system/execution_result'

  const userStore = useUserStore()
  const enumStore = useEnum()
  const caseRunning = ref(false)
  const runtimeParametersRef = ref<InstanceType<typeof ApiInfoRuntimeParametersModal> | null>(null)
  const { copyingId, copyApiInfoCurl } = useApiInfoCurl()
  const versionPanelRef = ref<InstanceType<typeof ApiInfoVersionPanel> | null>(null)
  const selectedApiVersion = ref<{
    kind: 'current' | 'revision'
    id: number
    label: string
  } | null>(null)
  const apiVersionReadOnly = ref(false)
  const requestMetaSaving = ref(false)
  const requestBodySaving = ref(false)
  const resultLoading = ref(false)
  const requestMetaSnapshot = ref({ method: null as any, url: '' })
  const posteriorFuncSnapshot = ref('')
  const configNavItems = [
    { key: '0', title: '请求头', description: '维护接口请求 Headers' },
    { key: '1', title: '参数', description: '维护查询参数' },
    { key: '2', title: '请求体', description: '维护 Body 配置' },
    {
      key: '5',
      title: '后置 JSONPath 提取',
      description: '从响应 JSON 提取值写入缓存，未匹配时执行失败',
    },
    {
      key: '6',
      title: '后置正则提取',
      description: '从响应文本提取首个匹配值写入缓存，未匹配时执行失败',
    },
    {
      key: '7',
      title: '后置自定义函数',
      description: '请求完成后执行自定义函数，可处理响应并操作运行缓存',
    },
  ]
  const POSTERIOR_FUNC_TEMPLATE = `def func(self, response):
    # self 是当前执行上下文，常用能力：
    # self.test_setup.test_data：变量/缓存工具，支持 get_cache、set_cache、replace 等
    test_data = self.test_setup.test_data

    # response 是本次接口响应模型，常用字段：
    code = response.code  # HTTP 状态码
    time = response.time  # 响应耗时，单位秒
    url = response.url  # 实际请求 URL
    headers = response.headers or {}  # 响应头
    json_body = response.json  # 解析后的 JSON，可能是 dict/list/str/number/bool/null
    text = response.text  # 原始响应文本，非 JSON 或文本断言可使用
    response_mode = response.response_mode  # 响应模式：http/sse/grpc/websocket
    sse_events = response.sse_events  # SSE 事件列表，仅 SSE 场景有值
    sse_stop_reason = response.sse_stop_reason  # SSE 停止原因
    request_body = response.request_body  # 实际发送的请求体
    request_headers = response.request_headers  # 实际发送的请求头

    # 提取响应数据到缓存示例
    if isinstance(json_body, dict):
        data = json_body.get('data') or {}
        if isinstance(data, dict) and data.get('id'):
            test_data.set_cache('response_id', data.get('id'))

    # 修改响应示例：追加自定义错误信息
    if code >= 400 and not response.error_msg:
        response.error_msg = text

    return response`

  const pageData: any = usePageData()
  const props = withDefaults(
    defineProps<{
      apiInfoId?: string | number
      embedded?: boolean
    }>(),
    {
      apiInfoId: '',
      embedded: false,
    }
  )
  const emit = defineEmits<{
    (event: 'close'): void
  }>()
  const route = useRoute()
  const apiInfoId = computed(() => props.apiInfoId || route.query.id || pageData.record?.id || '')
  const defaultApiInfoRecord = () => ({
    id: apiInfoId.value,
    name: '',
    method: null,
    url: '',
    headers: null,
    params: null,
    protocol_type: 'http',
    body_type: 'none',
    body_config: null,
    sse_config: null,
    posterior_json_path: [],
    posterior_re: [],
    posterior_func: '',
    result_data: null,
  })
  if (!pageData.record) {
    pageData.setRecord(defaultApiInfoRecord())
  }
  function normalizeApiInfoRecord(record: any) {
    return {
      ...defaultApiInfoRecord(),
      ...(record || {}),
      posterior_json_path: Array.isArray(record?.posterior_json_path || record?.posterior_response)
        ? record.posterior_json_path || record.posterior_response
        : [],
      posterior_re: Array.isArray(record?.posterior_re || record?.posterior_response_text)
        ? record.posterior_re || record.posterior_response_text
        : [],
    }
  }
  const initialApiInfoRecord = normalizeApiInfoRecord(pageData.record)
  const data: any = reactive({
    id: 0,
    pageType: '0',
    addButton: false,
    api_info: initialApiInfoRecord,
    headers: formatJson(initialApiInfoRecord.headers),
    defaultHeadersText: '',
    isDefaultHeadersPreview: false,
    textareaAutoSize: { minRows: 16, maxRows: 22 },
  })
  const currentApiInfoPayload = ref<any>(normalizeApiInfoRecord(initialApiInfoRecord))
  const currentNavItem = computed(
    () =>
      configNavItems.find((item) => item.key === data.pageType) || {
        key: data.pageType,
        title: '接口配置',
        description: '维护接口配置',
      }
  )
  const apiDetailTitle = computed(() => {
    const id = data.api_info?.id || apiInfoId.value || '-'
    const name = data.api_info?.name || pageData.record?.name || '-'
    return `服务调用工作台 / ${id} / ${name}`
  })
  const projectProductId = computed(() => {
    const projectProduct = data.api_info?.project_product
    return projectProduct?.id || projectProduct || ''
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
  const responseBodyData = computed(() => {
    const result = data.api_info?.result_data
    if (!result) return undefined
    if (Object.prototype.hasOwnProperty.call(result, 'json')) {
      return result.json
    }
    return result.text
  })
  const executionVersionTitle = computed(() => {
    if (selectedApiVersion.value?.kind === 'revision') {
      return `当前执行：${selectedApiVersion.value.label}（Revision #${selectedApiVersion.value.id}）`
    }
    return '当前执行：编辑态配置'
  })
  const executionVersionDescription = computed(() => {
    if (selectedApiVersion.value?.kind === 'revision') {
      return '本次执行使用该只读快照，不会读取编辑态的最新修改。'
    }
    return '保存只更新编辑态；生成修订并发布后，才会形成新的正式版本。'
  })

  function handleApiVersionSelect(selection: {
    kind: 'current' | 'revision'
    id: number
    label: string
    payload: any
  }) {
    selectedApiVersion.value = {
      kind: selection.kind,
      id: selection.id,
      label: selection.label,
    }
    apiVersionReadOnly.value = selection.kind !== 'current'
    const record = normalizeApiInfoRecord({
      ...selection.payload,
      id: apiInfoId.value,
      result_data: data.api_info?.result_data || null,
    })
    data.api_info = record
    data.headers = formatJson(record.headers)
    data.isDefaultHeadersPreview = false
    syncRequestMetaSnapshot()
    switchPageType()
  }

  let persistApiInfoQueue: Promise<unknown> = Promise.resolve()

  function showEditingSavedMessage() {
    Message.success('已保存到编辑态，发布版本未变更')
  }

  function persistApiInfo(payload: Record<string, unknown>) {
    if (apiVersionReadOnly.value) {
      Message.warning('当前正在查看只读快照，请先在版本栏迁出到编辑态后再修改')
      return Promise.resolve(null)
    }
    const request = persistApiInfoQueue
      .catch(() => undefined)
      .then(async () => {
        const response = await putApiInfo({ id: apiInfoId.value, ...payload })
        if (response?.data) {
          const record = normalizeApiInfoRecord({
            ...response.data,
            result_data: data.api_info?.result_data || null,
          })
          currentApiInfoPayload.value = record
          data.api_info = record
          if (Object.prototype.hasOwnProperty.call(payload, 'headers')) {
            data.headers = formatJson(record.headers)
            data.isDefaultHeadersPreview = false
          }
        }
        return response
      })
    persistApiInfoQueue = request.then(
      () => undefined,
      () => undefined
    )
    return request
  }

  const hasValue = (value: unknown) => {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
    return true
  }

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
    if (apiVersionReadOnly.value) {
      Message.warning('当前正在查看只读快照，请先在版本栏迁出到编辑态后再修改')
      return
    }
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
    } else if (hasConfigValue(record.body_config) || record.body_type !== 'none') {
      data.pageType = '2'
    } else {
      data.pageType = '2'
    }
  }

  function doResetSearch() {
    if (props.embedded) {
      emit('close')
      return
    }
    window.history.back()
  }

  function formatJson(items: any) {
    if (items === null) {
      return null
    }
    return JSON.stringify(items, null, 2)
  }

  function formatHeadersPreview(items: Record<string, any>) {
    const keys = Object.keys(items || {})
    if (keys.length === 0) return ''
    return JSON.stringify(items, null, 2)
  }

  function loadDefaultHeadersPreview(record: any) {
    const projectProduct = record?.project_product
    const projectProductValue = projectProduct?.id || projectProduct
    data.defaultHeadersText = ''
    data.isDefaultHeadersPreview = false
    if (!projectProductValue || (record?.headers !== null && record?.headers !== undefined)) {
      data.headers = formatJson(record?.headers)
      return Promise.resolve()
    }
    return getApiHeaders({
      project_product: projectProductValue,
      status: 1,
      page: 1,
      pageSize: 1000,
    })
      .then((res) => {
        const rows = Array.isArray(res.data) ? res.data : []
        const headers = rows.reduce((acc: Record<string, string>, item: any) => {
          if (item?.key) {
            acc[item.key] = item.value
          }
          return acc
        }, {})
        const preview = formatHeadersPreview(headers)
        data.defaultHeadersText = preview
        data.headers = null
        data.isDefaultHeadersPreview = Boolean(preview)
      })
      .catch((error) => {
        console.log(error)
        data.headers = null
      })
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
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(value) || value.startsWith('//')) {
      Message.error('只允许输入 URL 的路径部分，协议、域名和端口从测试配置-测试对象中读取')
      return false
    }
    if (!value.startsWith('/')) {
      Message.error('URL 必须以 / 开头，只保存路径部分')
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
    await nextTick()
    try {
      const res = await persistApiInfo({
        method: data.api_info.method,
        url: data.api_info.url.trim(),
      })
      if (!res) return
      showEditingSavedMessage()
      syncRequestMetaSnapshot()
    } catch (e) {
      console.log(e)
    } finally {
      requestMetaSaving.value = false
    }
  }

  function upDate(key: string, value1: string) {
    let value = ''
    if (key === 'headers') {
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
    if (!apiInfoId.value) return
    persistApiInfo({ [key]: value })
      .then((res) => {
        if (!res) return
        showEditingSavedMessage()
      })
      .catch(console.log)
  }

  function saveHeaders() {
    if (
      data.isDefaultHeadersPreview &&
      (data.headers === null || data.headers === undefined || data.headers === '')
    ) {
      return
    }
    data.isDefaultHeadersPreview = false
    upDate('headers', data.headers)
  }

  async function saveRequestBody(value: any) {
    if (!apiInfoId.value || requestBodySaving.value) return
    requestBodySaving.value = true
    try {
      const res = await persistApiInfo(value)
      if (!res) return
      showEditingSavedMessage()
    } catch (error) {
      console.log(error)
    } finally {
      requestBodySaving.value = false
    }
  }

  const onRunCase = async () => {
    if (!apiInfoId.value) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const versionParams =
        selectedApiVersion.value?.kind === 'revision'
          ? { revision_id: selectedApiVersion.value.id }
          : {}
      const targetId = apiInfoId.value
      const testEnv = userStore.selected_environment
      const parameters = await runtimeParametersRef.value?.prepare([{ id: targetId, ...versionParams }])
      if (parameters == null) return
      Message.loading('接口开始执行中~')
      const res = await getApiCaseInfoRun(
        targetId,
        testEnv,
        versionParams,
        parameters
      )
      data.caseResult = res.data
      if (res.data?.id) {
        const detailRes = await getExecutionResultDetailResolved(res.data.id)
        data.api_info.result_data = detailRes.data?.result_data || null
      }
      if (res.data?.error_message) {
        Message.error(res.data.error_message)
      } else {
        Message.success(res.msg)
      }
    } catch (e) {
      doRefresh()
    } finally {
      caseRunning.value = false
    }
  }

  async function loadLatestExecutionResult() {
    if (!apiInfoId.value) return
    resultLoading.value = true
    try {
      const res = await getExecutionResultLatestResolved({
        source_type: 'page',
        target_type: 'api_info',
        target_id: apiInfoId.value,
      })
      data.api_info.result_data = res.data?.result_data || null
    } catch (error) {
      console.log(error)
      data.api_info.result_data = null
    } finally {
      resultLoading.value = false
    }
  }

  function doRefresh() {
    if (!apiInfoId.value) return Promise.resolve()
    return getApiInfo({ id: apiInfoId.value })
      .then((res) => {
        const res_data = normalizeApiInfoRecord(res.data[0])
        if (!props.embedded) {
          pageData.setRecord(res_data)
        }
        currentApiInfoPayload.value = normalizeApiInfoRecord(res_data)
        data.api_info = res_data
        loadDefaultHeadersPreview(res_data)
        syncRequestMetaSnapshot()
        return loadLatestExecutionResult()
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      await doRefresh()
      switchPageType()
      syncRequestMetaSnapshot()
    })
  })
</script>
<style scoped>
  .api-detail-workbench {
    display: grid;
    grid-template-columns: 230px 190px minmax(360px, 34fr) minmax(480px, 52fr);
    gap: var(--m-page-gap);
    height: calc(100% - var(--m-page-gap));
    min-height: 0;
  }

  .api-detail-workbench-scroll {
    --mango-workbench-min-width: 1332px;
  }

  .api-detail-panel-readonly .api-request-bar,
  .api-detail-panel-readonly .api-detail-panel-body,
  .api-detail-panel-readonly :deep(.arco-switch) {
    pointer-events: none;
  }

  .api-detail-panel-readonly .api-request-bar,
  .api-detail-panel-readonly .api-detail-panel-body {
    opacity: 0.78;
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

  .api-version-context {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--m-border);
    background: color-mix(in srgb, var(--m-warning) 6%, var(--m-surface));
  }

  .api-version-context.readonly {
    background: var(--m-surface-soft);
  }

  .api-version-context > div {
    min-width: 0;
  }

  .api-version-context strong,
  .api-version-context span {
    display: block;
  }

  .api-version-context strong {
    color: var(--m-text);
    font-size: 12px;
    font-weight: 600;
    line-height: 18px;
  }

  .api-version-context span {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
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
    display: inline-flex;
    align-items: center;
    gap: 8px;
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

  .default-headers-preview {
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .default-headers-preview-title {
    padding: 8px 10px;
    border-bottom: 1px solid var(--m-border);
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .default-headers-preview pre {
    overflow: auto;
    max-height: 220px;
    margin: 0;
    padding: 10px;
    color: var(--m-text);
    font-size: 12px;
    line-height: 18px;
    white-space: pre-wrap;
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
