<template>
  <TableBody plain class="mango-mock-detail-page mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">
            {{ form.id ? `Mock 接口配置 / ${form.id} / ${form.name || '-'}` : '新增 Mock 接口' }}
          </div>
          <div class="mango-detail-subtitle">配置请求断言、响应匹配和调用结果</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button v-if="form.id" size="small" @click="copyCurl">复制 cURL</a-button>
          <a-button  v-if="form.id" size="small" type="primary" status="success" @click="openDebug">调试调用</a-button>
          <a-button  v-if="form.id" size="small" @click="openLogs">调用记录</a-button>
          <VariableReferencePanel />
          <a-button  size="small" type="primary" :loading="saving" @click="save">保存</a-button>
          <a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <a-spin class="mango-mock-detail-spin" :loading="loading" tip="Mock 配置加载中...">
        <div class="mango-workbench-scroll-x mango-mock-workbench-scroll">
          <div class="mango-detail-workbench mango-mock-detail-workbench">
            <aside class="mango-mock-config-nav">
              <div class="mango-mock-config-nav__head">
                <div class="mango-mock-config-nav__title">配置项</div>
                <div class="mango-mock-config-nav__subtitle">按请求处理顺序维护</div>
              </div>
              <button
                v-for="item in configNavItems"
                :key="item.key"
                type="button"
                :class="['mango-mock-config-nav__item', { 'mango-mock-config-nav__item--active': activeTab === item.key }]"
                @click="activeTab = item.key"
              >
                <span class="mango-mock-config-nav__item-title">
                  <span>{{ item.title }}</span>
                  <a-tag v-if="item.count !== undefined" size="small">{{ item.count }}</a-tag>
                </span>
                <small>{{ item.description }}</small>
              </button>
            </aside>

            <section class="mango-mock-config-panel">
              <div class="mango-mock-config-panel__head">
                <div>
                  <div class="mango-mock-config-panel__title">{{ currentConfigNavItem.title }}</div>
                  <div class="mango-mock-config-panel__subtitle">{{ currentConfigNavItem.description }}</div>
                </div>
                <a-tag v-if="activeTab === 'basic' && form.id" size="small" :color="form.enabled ? 'green' : 'gray'">
                  {{ form.enabled ? '已启用' : '已停用' }}
                </a-tag>
              </div>

              <div class="mango-mock-config-panel__body">
                <div v-if="activeTab === 'basic'" class="mango-config-form-grid mango-mock-basic-grid">
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label mango-mock-required">项目/产品</label>
                    <div class="mango-config-form-control"><ProjectProductSelect v-model="form.project_product" placeholder="请选择项目/产品" /></div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label mango-mock-required">接口名称</label>
                    <div class="mango-config-form-control"><a-input v-model="form.name" placeholder="请输入接口名称" /></div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label">请求方法</label>
                    <div class="mango-config-form-control">
                      <a-select
                        v-model="form.config.methods"
                        multiple
                        allow-clear
                        :options="methodOptions"
                        placeholder="不选择则接受全部请求方法"
                      />
                    </div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label mango-mock-required">请求路径</label>
                    <div class="mango-config-form-control"><a-input v-model="requestPath" placeholder="如 /contracts/{contract_id}" /></div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label">启用接口</label>
                    <div class="mango-config-form-control mango-mock-switch-control"><a-switch v-model="form.enabled" size="small" /></div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label">记录调用</label>
                    <div class="mango-config-form-control mango-mock-switch-control">
                      <a-switch v-model="form.record_call_log" size="small" />
                      <span>记录普通调用；失败与平台异常始终记录</span>
                    </div>
                  </div>
                  <div class="mango-config-form-row mango-mock-config-row--full">
                    <label class="mango-config-form-label">请求解密</label>
                    <div class="mango-config-form-control mango-mock-decryption-mode">
                      <a-select
                        v-model="form.config.request_decryption.type"
                        class="mango-mock-decryption-mode__select"
                        :options="requestDecryptionOptions"
                      />
                      <span>解密后的 JSON 用于断言和规则匹配，密钥按填写内容保存。</span>
                    </div>
                  </div>
                  <div
                    v-if="form.config.request_decryption.type === 'lark_event'"
                    class="mango-soft-panel mango-mock-decryption mango-mock-config-row--full"
                  >
                    <a-alert v-if="form.config.request_decryption.configuration_error" type="warning">
                      {{ form.config.request_decryption.configuration_error }}
                    </a-alert>
                    <div class="mango-mock-decryption__fields">
                      <div class="mango-mock-decryption__field">
                        <label class="mango-mock-decryption__label mango-mock-required">Encrypt Key</label>
                        <div class="mango-mock-decryption__control">
                          <a-input
                            v-model="form.config.request_decryption.encrypt_key"
                            placeholder="请输入飞书 Encrypt Key"
                            allow-clear
                          />
                        </div>
                      </div>
                      <div class="mango-mock-decryption__field">
                        <label class="mango-mock-decryption__label">Verification Token</label>
                        <div class="mango-mock-decryption__control">
                          <a-input
                            v-model="form.config.request_decryption.verification_token"
                            placeholder="选填，配置后会校验解密结果"
                            allow-clear
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="mango-config-form-row mango-mock-config-row--full mango-mock-config-row--textarea">
                    <label class="mango-config-form-label">接口说明</label>
                    <div class="mango-config-form-control"><a-textarea v-model="form.description" :auto-size="{ minRows: 2, maxRows: 4 }" placeholder="请输入接口用途或使用说明" /></div>
                  </div>
                  <div v-if="requestPath" class="mango-soft-panel mango-mock-url-preview mango-mock-config-row--full">
                    <span class="mango-mock-url-preview__label">调用地址</span>
                    <code>{{ mockUrl }}</code>
                    <a-button v-if="form.id" type="text" size="small" @click="copyCurl">复制 cURL</a-button>
                  </div>
                </div>

                <div v-else-if="activeTab === 'assertions'">
                  <MockConditionEditor
                    v-model="form.config.assertions"
                    mode="assertion"
                    :assertion-methods="assertionMethods"
                    :methods-loading="assertionMethodsLoading"
                  />
                </div>

                <div v-else-if="activeTab === 'rules'">
                  <div class="mango-mock-rule-toolbar">
                    <span>按页面顺序匹配，首条命中后停止。</span>
                    <a-button size="small" type="primary" @click="addRule">增加规则</a-button>
                  </div>
                  <a-collapse v-model:active-key="activeRules" :bordered="false">
                    <a-collapse-item v-for="(rule, index) in form.config.rules" :key="rule.key" :header="rule.name || `响应规则 ${index + 1}`">
                      <template #extra>
                        <a-space @click.stop>
                          <a-switch v-model="rule.enabled" size="small" />
                          <a-button type="text" :disabled="index === 0" @click="moveRule(index, -1)">上移</a-button>
                          <a-button type="text" :disabled="index === form.config.rules.length - 1" @click="moveRule(index, 1)">下移</a-button>
                          <a-button  type="text" status="danger" @click="removeRule(index)">删除</a-button>
                        </a-space>
                      </template>
                      <a-form :model="rule" class="mango-mock-rule-form">
                        <a-form-item label="规则名称"><a-input v-model="rule.name" /></a-form-item>
                      </a-form>
                      <div class="mango-section-title mango-mock-subtitle"><div><h3>匹配条件</h3></div></div>
                      <MockConditionEditor
                        v-model="rule.matchers"
                        mode="matcher"
                        :assertion-methods="assertionMethods"
                        :methods-loading="assertionMethodsLoading"
                      />
                      <div class="mango-section-title mango-mock-subtitle"><div><h3>命中响应</h3></div></div>
                      <MockResponseEditor v-model="rule.response" />
                    </a-collapse-item>
                  </a-collapse>
                  <div v-if="form.config.rules.length === 0" class="mango-empty-state mango-mock-empty-state">
                    暂无响应规则，可新增规则或直接使用默认响应
                  </div>
                </div>

                <div v-else>
                  <a-alert class="mango-mock-default-tip" type="info">没有响应规则命中时返回此内容。</a-alert>
                  <MockResponseEditor v-model="form.config.default_response" />
                </div>
              </div>
            </section>
          </div>
        </div>
      </a-spin>
    </template>
  </TableBody>

  <a-modal v-model:visible="debug.visible" title="调用 Mock 接口" :width="760" ok-text="发送请求" cancel-text="关闭" :ok-loading="debug.loading" @ok="runDebug">
    <a-form :model="debug.form">
      <a-form-item label="请求方法">
        <a-select
          v-model="debug.form.method"
          :options="availableDebugMethodOptions"
          :disabled="availableDebugMethodOptions.length === 1"
        />
      </a-form-item>
      <a-form-item label="请求路径"><a-input v-model="debug.form.path" /></a-form-item>
      <a-form-item label="Query(JSON)"><a-textarea v-model="debug.form.query" :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item>
      <a-form-item label="请求头(JSON)"><a-textarea v-model="debug.form.headers" :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item>
      <a-form-item label="请求体"><a-textarea v-model="debug.form.body" :auto-size="{ minRows: 4, maxRows: 8 }" /></a-form-item>
    </a-form>
  </a-modal>

  <BaseSidePanel
    v-model:visible="debug.resultVisible"
    :title="debug.result ? `Mock 调用结果 · HTTP ${debug.result.status}` : 'Mock 调用结果'"
    width="1080px"
    :show-footer="false"
  >
    <div v-if="debug.result" class="mango-mock-side-panel-content mango-mock-invoke-result">
      <a-descriptions class="mango-mock-invoke-summary" :column="4" size="small" bordered>
        <a-descriptions-item label="调用结果">
          <a-tag size="small" :color="debug.result.ok ? 'green' : 'red'">{{ debug.result.ok ? '成功' : '失败' }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="HTTP 状态">{{ debug.result.status }} {{ debug.result.status_text }}</a-descriptions-item>
        <a-descriptions-item label="耗时">{{ debug.result.duration_ms }} ms</a-descriptions-item>
        <a-descriptions-item label="Trace ID">{{ debug.result.trace_id || '-' }}</a-descriptions-item>
        <a-descriptions-item label="请求方法">{{ debug.result.request_method }}</a-descriptions-item>
        <a-descriptions-item label="请求 URL" :span="3">{{ debug.result.request_url }}</a-descriptions-item>
      </a-descriptions>

      <a-tabs class="mango-section-card mango-mock-result-tabs" default-active-key="request">
        <a-tab-pane key="request" title="请求信息">
          <div class="mango-mock-result-tab-description">本次真实发送到 Mock 服务的请求内容</div>
          <div class="mango-mock-result-grid">
            <div>
              <div class="mango-mock-result-label">Query 参数</div>
              <div class="mango-mock-json-panel">
                <JsonDisplay :data="debug.result.request_query || {}" :show-drawer-button="false" :default-expanded="false" />
              </div>
            </div>
            <div>
              <div class="mango-mock-result-label">请求头</div>
              <div class="mango-mock-json-panel">
                <JsonDisplay :data="debug.result.request_headers || {}" :show-drawer-button="false" :default-expanded="false" />
              </div>
            </div>
            <div class="mango-mock-result-grid__full">
              <div class="mango-mock-result-label">请求体</div>
              <div class="mango-mock-json-panel">
                <JsonDisplay :data="debug.result.request_body || {}" :show-drawer-button="false" :default-expanded="false" />
              </div>
            </div>
          </div>
        </a-tab-pane>
        <a-tab-pane key="response" title="响应信息">
          <div class="mango-mock-result-tab-description">Mock 服务实际返回的响应内容</div>
          <div class="mango-mock-result-grid mango-mock-result-grid--fill">
            <div>
              <div class="mango-mock-result-label">响应头</div>
              <div class="mango-mock-json-panel mango-mock-json-panel--headers">
                <JsonDisplay :data="debug.result.response_headers || {}" :show-drawer-button="false" :default-expanded="false" />
              </div>
            </div>
            <div class="mango-mock-result-grid__item--fill">
              <div class="mango-mock-result-label">响应体</div>
              <div class="mango-mock-json-panel mango-mock-json-panel--fill">
                <JsonDisplay :data="debug.result.response_body ?? {}" :show-drawer-button="false" :default-expanded="false" />
              </div>
            </div>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>
  </BaseSidePanel>

  <MockCallLogsPanel v-if="form.id" v-model:visible="logsVisible" :mock-id="form.id" :mock-key="form.mock_key" />
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'

  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MockCallLogsPanel from '../components/MockCallLogsPanel.vue'
  import type { MockAssertionMethodOption, MockConfigPayload, MockRule } from '@/api/apitest/mock'
  import { createMockConfig, getMockAssertionMethods, getMockConfigDetail, getMockEndpointUrl, invokeMockEndpoint, updateMockConfig } from '@/api/apitest/mock'
  import MockConditionEditor from './components/MockConditionEditor.vue'
  import MockResponseEditor from './components/MockResponseEditor.vue'
  import { debugMethodOptions, emptyResponse, methodOptions } from './config'

  const route = useRoute()
  const router = useRouter()
  const loading = ref(false)
  const saving = ref(false)
  const assertionMethodsLoading = ref(false)
  const assertionMethods = ref<MockAssertionMethodOption[]>([])

  const activeTab = ref('basic')
  const activeRules = ref<string[]>([])
  const savedMockKey = ref('')
  const emptyRequestDecryption = () => ({
    type: 'none' as const,
    encrypt_key: '',
    verification_token: '',
    configuration_error: '',
  })
  const requestDecryptionOptions = [
    { label: '不解密', value: 'none' },
    { label: '飞书事件订阅', value: 'lark_event' },
  ]
  const form = reactive<MockConfigPayload>({
    project_product: '', name: '', mock_key: '', description: '', method: 0, path: '/', enabled: true,
    record_call_log: false,
    config: {
      methods: [0],
      assertions: [],
      rules: [],
      default_response: emptyResponse(),
      request_decryption: emptyRequestDecryption(),
    },
  })
  const debug = reactive({ visible: false, resultVisible: false, loading: false, form: { method: 'GET', path: '/', query: '{}', headers: '{}', body: '' }, result: null as any })
  const logsVisible = ref(false)
  const requestPath = computed({
    get: () => form.mock_key
      ? `/${form.mock_key}${form.path && form.path !== '/' ? form.path : ''}`
      : '',
    set: (value: string) => {
      const normalized = value.trim().replace(/^\/+/, '')
      if (!normalized) {
        form.mock_key = ''
        form.path = '/'
        return
      }
      const separatorIndex = normalized.indexOf('/')
      form.mock_key = separatorIndex === -1 ? normalized : normalized.slice(0, separatorIndex)
      form.path = separatorIndex === -1 ? '/' : `/${normalized.slice(separatorIndex + 1)}`
    },
  })
  const mockUrl = computed(() => getMockEndpointUrl(requestPath.value))
  const availableDebugMethodOptions = computed(() => {
    if (!form.config.methods.length) return debugMethodOptions
    const labels = new Set(
      methodOptions
        .filter((item) => form.config.methods.includes(item.value))
        .map((item) => item.label)
    )
    return debugMethodOptions.filter((item) => labels.has(item.value))
  })
  const executableMethodName = computed(() => availableDebugMethodOptions.value[0]?.value || 'GET')
  const configNavItems = computed(() => [
    { key: 'basic', title: '基础配置', description: '地址、方法、解密和记录策略' },
    { key: 'assertions', title: '请求断言', description: '校验请求参数是否合法', count: form.config.assertions.length },
    { key: 'rules', title: '响应规则', description: '按条件匹配返回内容', count: form.config.rules.length },
    { key: 'default', title: '默认响应', description: '没有规则命中时返回' },
  ])
  const currentConfigNavItem = computed(() => configNavItems.value.find((item) => item.key === activeTab.value) || configNavItems.value[0])

  function normalizeProduct(value: any) { return Array.isArray(value) ? value[value.length - 1] : value?.id || value }
  function applyData(data: any) {
    Object.assign(form, data, { project_product: data.project_product?.id || data.project_product })
    savedMockKey.value = data.mock_key || ''
    form.config = {
      methods: Array.isArray(data.config?.methods) ? data.config.methods : [data.method ?? 0],
      assertions: data.config?.assertions || [],
      rules: data.config?.rules || [],
      default_response: data.config?.default_response || emptyResponse(),
      request_decryption: { ...emptyRequestDecryption(), ...(data.config?.request_decryption || {}) },
    }
  }
  async function loadDetail() {
    if (!route.query.id) return
    loading.value = true
    try { applyData((await getMockConfigDetail(String(route.query.id))).data) }
    finally { loading.value = false }
  }
  async function loadAssertionMethods() {
    assertionMethodsLoading.value = true
    try { assertionMethods.value = (await getMockAssertionMethods()).data || [] }
    finally { assertionMethodsLoading.value = false }
  }
  function validate() {
    if (!normalizeProduct(form.project_product)) return Message.error('请选择项目/产品'), false
    if (!form.name.trim()) return Message.error('请输入接口名称'), false
    if (!requestPath.value) return Message.error('请输入请求路径'), false
    if (!/^\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/.*)?$/.test(requestPath.value)) {
      return Message.error('请求路径须以 / 开头，首段仅支持小写字母、数字和短横线'), false
    }
    if (form.id && savedMockKey.value && form.mock_key !== savedMockKey.value) {
      return Message.error('已保存接口不能修改请求路径首段，避免原调用地址失效'), false
    }
    const decryption = form.config.request_decryption
    if (decryption.type === 'lark_event' && !decryption.encrypt_key.trim()) {
      return Message.error('请输入飞书 Encrypt Key'), false
    }
    return true
  }
  async function save() {
    if (!validate()) return
    saving.value = true
    try {
      form.method = form.config.methods[0] ?? 0
      const payload = { ...form, project_product: normalizeProduct(form.project_product) }
      const response = form.id ? await updateMockConfig(payload) : await createMockConfig(payload)
      Message.success('保存成功')
      if (!form.id) await router.replace({ path: '/apitest/mock/details', query: { id: response.data.id } })
      await loadDetail()
    } finally { saving.value = false }
  }
  function addRule() {
    const rule: MockRule = { key: `rule-${Date.now()}`, name: `响应规则 ${form.config.rules.length + 1}`, enabled: true, matchers: [], response: emptyResponse() }
    form.config.rules.push(rule); activeRules.value = [...activeRules.value, rule.key]
  }
  function removeRule(index: number) { form.config.rules.splice(index, 1) }
  function moveRule(index: number, offset: number) { const target = index + offset; if (target < 0 || target >= form.config.rules.length) return; const [rule] = form.config.rules.splice(index, 1); form.config.rules.splice(target, 0, rule) }
  function quoteCurlValue(value: string) { return `'${value.replace(/'/g, `'"'"'`)}'` }
  async function copyCurl() {
    const command = `curl -X ${executableMethodName.value} ${quoteCurlValue(mockUrl.value)}`
    await navigator.clipboard.writeText(command)
    Message.success('cURL 已复制')
  }
  function openDebug() {
    debug.form.method = executableMethodName.value
    debug.form.path = requestPath.value.replace(/\{[^}]+\}/g, 'value')
    debug.visible = true
    debug.result = null
  }
  async function runDebug() {
    if (!form.id) return
    let query: Record<string, unknown>
    let headers: Record<string, unknown>
    try {
      query = JSON.parse(debug.form.query || '{}')
      headers = JSON.parse(debug.form.headers || '{}')
    } catch {
      Message.error('Query和请求头必须是合法JSON')
      return
    }
    debug.loading = true
    try {
      debug.result = await invokeMockEndpoint({
        method: debug.form.method,
        requestPath: debug.form.path,
        query,
        headers,
        body: debug.form.body,
      })
      debug.visible = false
      debug.resultVisible = true
      if (debug.result.ok) Message.success(`调用成功，HTTP ${debug.result.status}`)
      else Message.warning(`接口已返回，HTTP ${debug.result.status}`)
    }
    catch { Message.error('Mock 接口调用失败，请检查服务地址或网络状态') }
    finally { debug.loading = false }
  }
  function openLogs() { logsVisible.value = true }
  onMounted(async () => {
    await Promise.all([loadDetail(), loadAssertionMethods()])
    if (route.query.logs === '1' && form.id) await openLogs()
  })
</script>

<style scoped>
  .mango-mock-detail-spin { width: 100%; height: 100%; }
  .mango-mock-workbench-scroll { --mango-workbench-min-width: 980px; height: 100%; }
  .mango-mock-detail-workbench { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: var(--m-page-gap); height: calc(100% - var(--m-page-gap)); min-height: 540px; }
  .mango-mock-config-nav, .mango-mock-config-panel { min-width: 0; min-height: 0; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); }
  .mango-mock-config-nav { overflow: auto; padding: 12px; }
  .mango-mock-config-nav__head { margin-bottom: 10px; }
  .mango-mock-config-nav__title { color: var(--m-text); font-size: 15px; font-weight: 600; line-height: 22px; }
  .mango-mock-config-nav__subtitle { margin-top: 2px; color: var(--m-muted); font-size: 12px; line-height: 18px; }
  .mango-mock-config-nav__item { display: block; width: 100%; margin: 0 0 8px; padding: 9px 10px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface-soft); color: var(--m-text-2); cursor: pointer; text-align: left; transition: border-color 0.2s ease, background 0.2s ease; }
  .mango-mock-config-nav__item:hover { border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border)); background: var(--m-surface); }
  .mango-mock-config-nav__item--active { border-color: var(--m-primary); background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface)); }
  .mango-mock-config-nav__item-title { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: 8px; color: var(--m-text); font-size: 13px; font-weight: 600; line-height: 20px; }
  .mango-mock-config-nav__item-title > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-mock-config-nav__item small { display: block; overflow: hidden; margin-top: 2px; color: var(--m-muted); font-size: 12px; line-height: 18px; text-overflow: ellipsis; white-space: nowrap; }
  .mango-mock-config-panel { display: flex; overflow: hidden; flex-direction: column; }
  .mango-mock-config-panel__head { display: flex; flex-shrink: 0; align-items: center; justify-content: space-between; gap: 12px; min-height: 58px; padding: 10px 12px; border-bottom: 1px solid var(--m-border); }
  .mango-mock-config-panel__title { color: var(--m-text); font-size: 15px; font-weight: 600; line-height: 22px; }
  .mango-mock-config-panel__subtitle { margin-top: 2px; color: var(--m-muted); font-size: 12px; line-height: 18px; }
  .mango-mock-config-panel__body { flex: 1; min-height: 0; overflow: auto; padding: 12px; }
  .mango-mock-basic-grid { width: 100%; max-width: 980px; align-content: start; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 18px; }
  .mango-mock-config-row--full { grid-column: 1 / -1; }
  .mango-mock-config-row--textarea { align-items: start; }
  .mango-mock-required::before { margin-right: 4px; color: var(--m-danger); content: '*'; }
  .mango-mock-switch-control { display: flex; min-height: 32px; align-items: center; gap: 8px; color: var(--m-muted); font-size: 12px; line-height: 18px; }
  .mango-mock-decryption-mode { display: flex; min-width: 0; align-items: center; gap: 10px; color: var(--m-muted); font-size: 12px; line-height: 18px; }
  .mango-mock-decryption-mode__select { width: 220px; flex: 0 0 220px; }
  .mango-mock-decryption { margin-left: 109px; padding: 10px 12px; }
  .mango-mock-decryption__fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 18px; }
  .mango-mock-decryption__field { display: grid; min-width: 0; grid-template-columns: 112px minmax(0, 1fr); align-items: center; gap: 9px; }
  .mango-mock-decryption__label { overflow: hidden; color: var(--m-text-2); font-size: 13px; line-height: 20px; text-align: right; text-overflow: ellipsis; white-space: nowrap; }
  .mango-mock-decryption__control { min-width: 0; }
  .mango-mock-decryption__control :deep(.arco-input-wrapper) { width: 100%; }
  .mango-mock-url-preview { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 8px 12px; word-break: break-all; }
  .mango-mock-url-preview__label { color: var(--m-muted); white-space: nowrap; }
  .mango-mock-url-preview code { min-width: 0; font-family: var(--m-font-mono); }
  .mango-mock-rule-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; color: var(--m-muted); }
  .mango-mock-rule-form { max-width: 520px; }
  .mango-mock-subtitle { margin-top: 12px; }
  .mango-mock-default-tip { margin-bottom: 10px; }
  .mango-mock-empty-state { min-height: 180px; }
  .mango-mock-side-panel-content { box-sizing: border-box; width: 100%; min-height: 100%; padding: 0; container-type: inline-size; }

  .mango-mock-invoke-result { display: flex; height: 100%; flex-direction: column; gap: var(--m-page-gap); }
  .mango-mock-invoke-summary { flex: none; }
  .mango-mock-result-tabs { min-height: 0; padding: 0 12px 12px; }
  .mango-mock-invoke-result .mango-mock-result-tabs { display: flex; flex: 1; flex-direction: column; }
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-content) { flex: 1; min-height: 0; }
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-content-list),
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-content-item-active),
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-pane) { height: 100%; }
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-pane) { display: flex; min-height: 0; flex-direction: column; overflow: auto; }
  .mango-mock-result-tabs :deep(.arco-tabs-nav) { margin-bottom: 10px; }
  .mango-mock-result-tab-description { margin-bottom: 10px; color: var(--m-muted); font-size: 12px; line-height: 18px; }
  .mango-mock-result-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .mango-mock-result-grid--fill { flex: 1; min-height: 0; grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
  .mango-mock-result-grid__item--fill { display: flex; min-height: 0; flex-direction: column; }
  .mango-mock-result-grid__full { grid-column: 1 / -1; }
  .mango-mock-result-label { margin-bottom: 5px; color: var(--m-text-2); font-size: 13px; font-weight: 600; line-height: 18px; }
  .mango-mock-json-panel { min-height: 96px; max-height: 320px; overflow: auto; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); }
  .mango-mock-json-panel--headers { max-height: 160px; }
  .mango-mock-json-panel--fill { flex: 1; min-height: 0; max-height: none; }
  .mango-mock-json-panel :deep(.mango-json-display-toolbar) { padding: 8px 10px 0; }
  .mango-mock-json-panel :deep(.mango-json-display-content) { min-height: 64px; border: 0; border-radius: 0; }
  .mango-mock-structured-panel { min-height: 96px; max-height: 300px; overflow: auto; padding: 10px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface-soft); }
  .mango-mock-structured-panel--detail { max-height: 520px; }
  .mango-mock-structured-panel :deep(.mango-structured-data__kv) { background: var(--m-surface); }

  @container (max-width: 860px) {
    .mango-mock-basic-grid { grid-template-columns: minmax(0, 1fr); }

    .mango-mock-result-grid { grid-template-columns: 1fr; }
    .mango-mock-decryption-mode { align-items: flex-start; flex-direction: column; }
    .mango-mock-decryption-mode__select { width: 100%; flex-basis: auto; }
    .mango-mock-decryption { margin-left: 0; }
    .mango-mock-decryption__fields { grid-template-columns: 1fr; }
    .mango-mock-result-grid__full { grid-column: auto; }
  }
</style>
