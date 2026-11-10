<template>
  <TableBody ref="tableBody" class="api-detail-workbench-page mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ apiDetailTitle }}</div>
          <div class="mango-detail-subtitle"> 维护请求配置、后置处理、断言和最近一次响应结果 </div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button
            size="small"
            status="success"
            :loading="caseRunning"
            :disabled="!recordReady || configurationLoading"
            @click="onRunCase"
            data-testid="qa-views-apitest-info-details-button-执行"
          >
            执行
          </a-button>
          <a-button
            v-if="canCopyApiInfoCurl(apiRecord)"
            size="small"
            :loading="copyingId === String(apiRecord.id)"
            @click="
              copyApiInfoCurl(
                { ...apiRecord, headers: headersText },
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
            v-if="pageActive && recordReady"
            :key="apiInfoId"
            ref="versionPanelRef"
            :api-info-id="apiInfoId"
            :current-payload="currentApiInfoPayload"
            :before-action="waitForSaves"
            @select="handleApiVersionSelect"
            @checkout="initialize"
          />
          <MangoPanelSpin v-else :loading="configurationLoading" class="mango-api-version-loading">
            <div class="mango-empty-state">{{
              loadFailed ? '版本配置暂不可用' : '正在加载版本配置'
            }}</div>
          </MangoPanelSpin>
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
                  'api-detail-nav-item-active': activeSection === item.key,
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

          <MangoPanelSpin :loading="configurationLoading" class="mango-api-configuration-loading">
            <section
              class="api-detail-panel"
              :class="{ 'api-detail-panel-readonly': apiVersionReadOnly }"
            >
              <div class="api-request-bar">
                <a-select
                  v-model="apiRecord.method"
                  class="api-request-method"
                  :options="methodOptions"
                  :disabled="editingLocked"
                  placeholder="方法"
                  data-testid="qa-views-apitest-info-details-select-方法"
                />
                <a-input
                  v-model="apiRecord.url"
                  class="api-request-url"
                  allow-clear
                  :disabled="editingLocked"
                  placeholder="请输入接口路径，例如 /api/user/list"
                  @press-enter="saveRequestMeta"
                  data-testid="qa-views-apitest-info-details-input-请输入接口路径-例如-api-user-list"
                />
                <a-button
                  class="api-request-save"
                  type="primary"
                  :loading="requestMetaSaving"
                  :disabled="editingLocked"
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
              <template v-if="loadFailed"><a-button size="small" @click="initialize">重新加载</a-button></template>
              <div class="api-detail-panel-head">
                <div>
                  <div class="api-detail-panel-title">
                    <span>{{ currentNavItem.title }}</span>
                    <a-tag v-if="apiVersionReadOnly" size="small" color="gray">只读快照</a-tag>
                  </div>
                  <div class="api-detail-panel-subtitle">{{ currentNavItem.description }}</div>
                </div>
                <a-spin v-if="pendingFields.size" :loading="true" />
                <a-space v-if="canAddExtraction && !apiVersionReadOnly">
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
                <div v-if="activeSection === '0'" class="config-pane">
                  <a-space direction="vertical" fill>
                    <a-spin v-if="defaultHeadersLoading && activeSection === '0'" :loading="true" />
                    <TipMessage
                      message="请求头必须为 JSON 格式。留空时默认使用请求头管理中已开启的请求头；获取 Token 等授权接口请填写 {}，避免公共 Authorization 引用待生成 Token 造成循环引用。"
                    />
                    <a-textarea
                      v-model="headersText"
                      :auto-size="textareaAutoSize"
                      allow-clear
                      :disabled="editingLocked"
                      placeholder='请输入 JSON 格式的请求头，例如：{"Content-Type": "application/json"}'
                      @blur="saveHeaders"
                      data-testid="qa-views-apitest-info-details-textarea-请输入-json-格式的请求头-例如-content-type-application-json"
                    />
                    <div v-if="isDefaultHeadersPreview" class="default-headers-preview">
                      <div class="default-headers-preview-title">请求头管理中已开启的 Headers</div>
                      <pre>{{ defaultHeadersText }}</pre>
                    </div>
                  </a-space>
                </div>

                <div v-else-if="activeSection === '1'" class="config-pane">
                  <a-space direction="vertical" fill>
                    <TipMessage
                      message="支持 JSON 对象/数组，也支持 query string，例如：case_id=21"
                    />
                    <a-textarea
                      v-model="apiRecord.params"
                      :auto-size="textareaAutoSize"
                      allow-clear
                      :disabled="editingLocked"
                      placeholder='请输入查询参数，例如：{"key": "value"} 或 case_id=21'
                      @blur="upDate('params', apiRecord.params)"
                      data-testid="qa-views-apitest-info-details-textarea-请输入查询参数-例如-key-value-或-case_id-21"
                    />
                  </a-space>
                </div>

                <div v-else-if="activeSection === '2'" class="config-pane">
                  <ApiRequestBodyEditor
                    ref="bodyEditorRef"
                    :key="viewGeneration"
                    :protocol-type="apiRecord.protocol_type"
                    :body-type="apiRecord.body_type"
                    :body-config="apiRecord.body_config"
                    :sse-config="apiRecord.sse_config"
                    :project-product-id="projectProductId"
                    :saving="requestBodySaving"
                    :readonly="editingLocked"
                    @save="saveRequestBody"
                  />
                </div>

                <div
                  v-else-if="activeSection === '5'"
                  class="config-pane mango-horizontal-scroll-region mango-horizontal-scroll-region--compact"
                >
                  <KeyValueList
                    :disabled="
                      editingLocked ||
                      pendingFields.has(
                        activeSection === '5' ? 'posterior_json_path' : 'posterior_re'
                      )
                    "
                    :data-list="apiRecord.posterior_json_path"
                    :field-config="[
                      { field: 'key', label: '缓存key', placeholder: '请输入缓存key' },
                      { field: 'value', label: 'jsonpath语法', placeholder: '请输入jsonpath语法' },
                    ]"
                    :on-delete-item="(index) => removeExtraction(index, 'posterior_json_path')"
                    :on-save="() => upDate('posterior_json_path', apiRecord.posterior_json_path)"
                  />
                </div>

                <div
                  v-else-if="activeSection === '6'"
                  class="config-pane mango-horizontal-scroll-region mango-horizontal-scroll-region--compact"
                >
                  <KeyValueList
                    :disabled="
                      editingLocked ||
                      pendingFields.has(
                        activeSection === '5' ? 'posterior_json_path' : 'posterior_re'
                      )
                    "
                    :data-list="apiRecord.posterior_re"
                    :field-config="[
                      { field: 'key', label: '缓存key', placeholder: '请输入缓存key' },
                      { field: 'value', label: '正则表达式', placeholder: '请输入正则表达式' },
                    ]"
                    :on-delete-item="(index) => removeExtraction(index, 'posterior_re')"
                    :on-save="() => upDate('posterior_re', apiRecord.posterior_re)"
                  />
                </div>

                <div v-else-if="activeSection === '7'" class="config-pane">
                  <CodeEditor
                    v-model="apiRecord.posterior_func"
                    :line-height="360"
                    :readonly="editingLocked || pendingFields.has('posterior_func')"
                    :code-style="{ width: '100%' }"
                    placeholder="根据帮助文档，输入自定义后置函数"
                    @focus="recordPosteriorFuncSnapshot"
                    @blur="savePosteriorFuncIfChanged"
                  />
                </div>
              </div>
            </section>
          </MangoPanelSpin>

          <ApiInfoResponsePanel :result="executionResult" :loading="resultLoading || caseRunning" />
        </div>
      </div>
    </template>
  </TableBody>
  <ApiInfoRuntimeParametersModal ref="runtimeParametersRef" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, nextTick, onBeforeUnmount, onActivated, onDeactivated, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import { getApiCaseInfoRun, getApiInfo } from '@/api/apitest/info'
  import { getApiHeaders } from '@/api/apitest/headers'
  import {
    getExecutionResultDetailResolved,
    getExecutionResultLatestResolved,
  } from '@/api/system/execution_result'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getOptionId } from '@/utils/business-format'
  import { cloneLosslessJson, stringifyLosslessJson } from '@/utils/lossless-json'
  import ApiInfoRuntimeParametersModal from '@/components/business/ApiInfoRuntimeParametersModal.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import KeyValueList from '@/components/forms/KeyValueList.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import ApiInfoVersionPanel from './components/ApiInfoVersionPanel.vue'
  import ApiInfoResponsePanel from './components/ApiInfoResponsePanel.vue'
  import ApiRequestBodyEditor from '../../components/ApiRequestBodyEditor.vue'
  import { canCopyApiInfoCurl, useApiInfoCurl } from '../composables/useApiInfoCurl'
  import {
    configNavItems,
    fallbackMethodOptions,
    POSTERIOR_FUNC_TEMPLATE,
    textareaAutoSize,
  } from './config'
  import { normalizeApiInfoRecord } from './record'
  import { useApiInfoDraft } from './composables/useApiInfoDraft'
  import type {
    ApiInfoPatch,
    ApiInfoRecord,
    ApiResponseData,
    ApiVersionSelection,
    ExtractionRow,
  } from './types'

  const props = withDefaults(defineProps<{ apiInfoId?: string | number; embedded?: boolean }>(), {
    apiInfoId: '',
    embedded: false,
  })
  const emit = defineEmits<{ (event: 'close'): void }>()
  const route = useRoute(),
    userStore = useUserStore(),
    enumStore = useEnum()
  const apiInfoId = computed(
    () =>
      props.apiInfoId || (Array.isArray(route.query.id) ? route.query.id[0] : route.query.id) || ''
  )
  const pageActive = ref(true),
    recordReady = ref(false),
    configurationLoading = ref(false),
    loadFailed = ref(false)
  const selectedApiVersion = ref<Omit<ApiVersionSelection, 'payload'> | null>(null)
  const apiVersionReadOnly = computed(() => selectedApiVersion.value?.kind === 'revision')
  const editingLocked = computed(
    () => apiVersionReadOnly.value || !recordReady.value || configurationLoading.value
  )
  const {
    draft: apiRecord,
    saved: currentApiInfoPayload,
    pendingFields,
    reset,
    view,
    persist: persistApiInfo,
    invalidate: invalidateDraft,
    waitForSaves,
  } = useApiInfoDraft(
    () => apiInfoId.value,
    () => pageActive.value && !editingLocked.value
  )
  const activeSection = ref('2'),
    headersText = ref<string | null>(null),
    defaultHeadersText = ref(''),
    isDefaultHeadersPreview = ref(false),
    defaultHeadersLoading = ref(false)
  const executionResult = ref<ApiResponseData | null>(null),
    resultLoading = ref(false),
    caseRunning = ref(false)
  const requestMetaSaving = ref(false),
    requestBodySaving = ref(false)
  const posteriorFuncSnapshot = ref('')
  const viewGeneration = ref(0)
  let contextVersion = 0,
    loadRequest = 0,
    previewRequest = 0,
    resultRequest = 0
  const runtimeParametersRef = ref<InstanceType<typeof ApiInfoRuntimeParametersModal> | null>(null)
  const bodyEditorRef = ref<InstanceType<typeof ApiRequestBodyEditor> | null>(null)
  const versionPanelRef = ref<InstanceType<typeof ApiInfoVersionPanel> | null>(null)
  const { copyingId, copyApiInfoCurl } = useApiInfoCurl(
    () => `${pageActive.value}:${apiInfoId.value}:${contextVersion}`
  )
  const currentNavItem = computed(
    () => configNavItems.find((item) => item.key === activeSection.value) || configNavItems[2]
  )
  const canAddExtraction = computed(() => ['5', '6'].includes(activeSection.value))
  const apiDetailTitle = computed(
    () => `服务调用工作台 / ${apiInfoId.value || '-'} / ${apiRecord.value.name || '-'}`
  )
  const projectProductId = computed(() => getOptionId(apiRecord.value.project_product) || '')
  const methodOptions = computed(() =>
    enumStore.method?.length
      ? enumStore.method.map((item) => ({ label: item.title, value: item.key }))
      : fallbackMethodOptions
  )
  const executionVersionTitle = computed(() =>
    selectedApiVersion.value?.kind === 'revision'
      ? `当前执行：${selectedApiVersion.value.label}（Revision #${selectedApiVersion.value.id}）`
      : '当前执行：编辑态配置'
  )
  const executionVersionDescription = computed(() =>
    apiVersionReadOnly.value
      ? '本次执行使用该只读快照，不会读取编辑态的最新修改。'
      : '保存只更新编辑态；生成修订并发布后，才会形成新的正式版本。'
  )
  function isCurrent(token: number) {
    return pageActive.value && token === contextVersion
  }
  function formatJson(value: unknown) {
    return value == null ? null : stringifyLosslessJson(value, 2)
  }
  function showEditingSavedMessage() {
    Message.success('已保存到编辑态，发布版本未变更')
  }
  function switchPageType() {
    activeSection.value = apiRecord.value.params?.trim() ? '1' : '2'
  }
  function switchType(key: string) {
    activeSection.value = key
    if (key === '7' && !apiRecord.value.posterior_func) {
      apiRecord.value.posterior_func = POSTERIOR_FUNC_TEMPLATE
      recordPosteriorFuncSnapshot()
    }
  }
  function recordPosteriorFuncSnapshot() {
    posteriorFuncSnapshot.value = apiRecord.value.posterior_func || ''
  }
  async function savePosteriorFuncIfChanged() {
    const value = apiRecord.value.posterior_func || ''
    if (value === posteriorFuncSnapshot.value) return
    if (await upDate('posterior_func', value)) posteriorFuncSnapshot.value = value
  }
  function addData() {
    if (editingLocked.value) return
    if (activeSection.value === '5')
      apiRecord.value.posterior_json_path.push({ key: '', value: '' })
    if (activeSection.value === '6') apiRecord.value.posterior_re.push({ key: '', value: '' })
  }
  async function removeExtraction(index: number, key: 'posterior_json_path' | 'posterior_re') {
    if (editingLocked.value || pendingFields.has(key)) return
    const rows = cloneLosslessJson(apiRecord.value[key])
    rows.splice(index, 1)
    await upDate(key, rows)
  }
  async function upDate(
    key: 'headers' | 'params' | 'posterior_func' | 'posterior_json_path' | 'posterior_re',
    input: string | null | ExtractionRow[]
  ) {
    if (editingLocked.value || pendingFields.has(key)) return false
    let value: unknown = input === '' ? null : input
    if (key === 'headers') {
      try {
        value = input ? JSON.parse(String(input)) : null
        if (value !== null && typeof value !== 'object') throw Error()
      } catch {
        Message.error('请输入json格式的：headers')
        return false
      }
    }
    try {
      const response = await persistApiInfo({ [key]: value } as ApiInfoPatch)
      if (!response) return false
      if (key === 'headers' && headersText.value === input) {
        headersText.value = formatJson(apiRecord.value.headers)
        isDefaultHeadersPreview.value = false
      }
      showEditingSavedMessage()
      return true
    } catch {
      return false
    }
  }
  function saveHeaders() {
    if (isDefaultHeadersPreview.value && !headersText.value) return
    previewRequest++
    defaultHeadersLoading.value = false
    return upDate('headers', headersText.value)
  }
  function validateRequestPath(url: string) {
    const value = url.trim()
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
    if (editingLocked.value || requestMetaSaving.value) return
    const record = apiRecord.value,
      saved = currentApiInfoPayload.value
    if (record.method === saved.method && record.url === saved.url) return
    if (record.method == null) {
      Message.error('请选择请求方法')
      return
    }
    if (!validateRequestPath(record.url)) return
    const payload = { method: record.method, url: record.url.trim() }
    requestMetaSaving.value = true
    try {
      if (await persistApiInfo(payload)) showEditingSavedMessage()
    } catch {
      /* 保留未保存的路径和方法，允许重试。 */
    } finally {
      requestMetaSaving.value = false
    }
  }
  async function saveRequestBody(value: ApiInfoPatch) {
    if (editingLocked.value || requestBodySaving.value) return
    const token = contextVersion
    requestBodySaving.value = true
    try {
      if (await persistApiInfo(value)) showEditingSavedMessage()
    } catch {
      if (isCurrent(token)) bodyEditorRef.value?.resetSaveState()
    } finally {
      requestBodySaving.value = false
    }
  }
  async function loadDefaultHeadersPreview(record: ApiInfoRecord) {
    const request = ++previewRequest,
      token = contextVersion,
      originalText = headersText.value
    defaultHeadersText.value = ''
    isDefaultHeadersPreview.value = false
    defaultHeadersLoading.value = false
    const product = getOptionId(record.project_product)
    if (!product || record.headers != null) return
    defaultHeadersLoading.value = true
    try {
      const response = await getApiHeaders({
        project_product: product,
        status: 1,
        page: 1,
        pageSize: 1000,
      })
      if (request !== previewRequest || !isCurrent(token) || headersText.value !== originalText)
        return
      const headers: Record<string, string> = {}
      for (const row of response.data || []) if (row.key) headers[row.key] = row.value
      defaultHeadersText.value = Object.keys(headers).length
        ? stringifyLosslessJson(headers, 2)
        : ''
      isDefaultHeadersPreview.value = Boolean(defaultHeadersText.value)
    } catch {
      /* 预览失败不清空用户输入。 */
    } finally {
      if (request === previewRequest) defaultHeadersLoading.value = false
    }
  }
  function handleApiVersionSelect(selection: ApiVersionSelection) {
    if (!recordReady.value) return
    contextVersion++
    viewGeneration.value++
    resultRequest++
    executionResult.value = null
    runtimeParametersRef.value?.cancel()
    selectedApiVersion.value = { kind: selection.kind, id: selection.id, label: selection.label }
    view(normalizeApiInfoRecord(selection.payload, apiInfoId.value))
    headersText.value = formatJson(apiRecord.value.headers)
    recordPosteriorFuncSnapshot()
    switchPageType()
    void loadDefaultHeadersPreview(apiRecord.value)
    void loadLatestExecutionResult()
  }
  async function loadLatestExecutionResult() {
    if (!apiInfoId.value || !pageActive.value) return
    const request = ++resultRequest,
      token = contextVersion,
      selection = selectedApiVersion.value
    resultLoading.value = true
    try {
      const response = await getExecutionResultLatestResolved({
        source_type: 'page',
        target_type: 'api_info',
        target_id: apiInfoId.value,
        ...(selection?.kind === 'revision'
          ? { revision_id: selection.id }
          : { revision_id_isnull: 1 }),
      })
      if (request === resultRequest && isCurrent(token))
        executionResult.value = response.data?.result_data || null
    } catch {
      /* 查询失败保留当前结果。 */
    } finally {
      if (request === resultRequest) resultLoading.value = false
    }
  }
  async function onRunCase() {
    if (!apiInfoId.value || !recordReady.value || caseRunning.value) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    const token = contextVersion,
      targetId = apiInfoId.value,
      testEnv = userStore.selected_environment
    const versionParams =
      selectedApiVersion.value?.kind === 'revision'
        ? { revision_id: selectedApiVersion.value.id }
        : {}
    const request = ++resultRequest
    caseRunning.value = true
    try {
      try { await waitForSaves() }
      catch { if (isCurrent(token)) Message.warning('配置尚未保存成功，请先重试保存后再执行'); return }
      if (!isCurrent(token)) return
      const parameters = await runtimeParametersRef.value?.prepare([
        { id: targetId, ...versionParams },
      ])
      if (parameters == null || !isCurrent(token)) return
      const response = await getApiCaseInfoRun(targetId, testEnv, versionParams, parameters)
      if (!isCurrent(token) || request !== resultRequest) return
      if (response.data?.id) {
        const detail = await getExecutionResultDetailResolved(response.data.id)
        if (!isCurrent(token) || request !== resultRequest) return
        executionResult.value = detail.data?.result_data || null
      }
      if (response.data?.error_message) Message.error(response.data.error_message)
      else Message.success(response.msg)
    } catch {
      /* 公共请求层提示错误，不重新加载或覆盖未保存配置。 */
    } finally {
      caseRunning.value = false
    }
  }
  async function initialize() {
    contextVersion++
    loadRequest++
    previewRequest++
    resultRequest++
    viewGeneration.value++
    runtimeParametersRef.value?.cancel()
    versionPanelRef.value?.close()
    selectedApiVersion.value = null
    recordReady.value = false
    loadFailed.value = false
    headersText.value = null
    defaultHeadersText.value = ''
    isDefaultHeadersPreview.value = false
    defaultHeadersLoading.value = false
    executionResult.value = null
    resultLoading.value = false
    reset(normalizeApiInfoRecord(null, apiInfoId.value))
    if (!pageActive.value || !apiInfoId.value) return
    const request = loadRequest
    configurationLoading.value = true
    try {
      const response = await getApiInfo({ id: apiInfoId.value })
      if (request !== loadRequest || !pageActive.value) return
      const source = response.data?.[0]
      if (!source) {
        loadFailed.value = true
        return
      }
      reset(normalizeApiInfoRecord(source, apiInfoId.value))
      recordReady.value = true
      headersText.value = formatJson(apiRecord.value.headers)
      recordPosteriorFuncSnapshot()
      switchPageType()
      void loadDefaultHeadersPreview(apiRecord.value)
      void loadLatestExecutionResult()
    } catch (loadFailure0) {
      if (request === loadRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
    } finally {
      if (request === loadRequest) configurationLoading.value = false
    }
  }
  function doResetSearch() {
    if (props.embedded) emit('close')
    else window.history.back()
  }
  function deactivate() {
    pageActive.value = false
    contextVersion++
    loadRequest++
    previewRequest++
    resultRequest++
    invalidateDraft()
    configurationLoading.value = false
    resultLoading.value = false
    defaultHeadersLoading.value = false
    runtimeParametersRef.value?.cancel()
    versionPanelRef.value?.close()
  }
  watch(
    apiInfoId,
    () => {
      void initialize()
    },
    { immediate: true }
  )
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!pageActive.value) {
      pageActive.value = true
      void initialize()
    }
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
  .api-detail-panel {
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

  .error-item {
    background-color: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface));
    border-color: color-mix(in srgb, var(--m-warning) 34%, transparent);
  }

  .error-item:hover {
    background-color: color-mix(in srgb, var(--m-warning) 16%, var(--m-surface));
  }
  .mango-api-configuration-loading {
    display: flex;
    min-width: 0;
    min-height: 0;
  }
  .mango-api-version-loading {
    min-width: 0;
    min-height: 0;
  }
  .mango-api-configuration-loading :deep(> .mango-panel-spin__content) {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
  }
  .mango-api-configuration-loading .api-detail-panel {
    flex: 1;
  }
</style>
