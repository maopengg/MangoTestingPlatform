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
          <a-button v-if="form.id" size="small" :loading="copying" @click="copyCurl"
            >复制 cURL</a-button
          >
          <a-button v-if="form.id" size="small" type="primary" status="success" @click="openDebug"
            >调试调用</a-button
          >
          <a-button v-if="form.id" size="small" @click="openLogs">调用记录</a-button>
          <VariableReferencePanel />
          <a-button
            size="small"
            type="primary"
            :loading="saving"
            :disabled="!ready || loading"
            @click="save"
            >保存</a-button
          >
          <a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <MangoPanelSpin class="mango-mock-detail-spin" :loading="loading" tip="Mock 配置加载中...">
        <template v-if="loadFailed"><a-button size="small" :loading="loading" @click="loadDetail()">重新加载</a-button></template>
        <div
          v-if="ready"
          :key="viewSession"
          class="mango-workbench-scroll-x mango-mock-workbench-scroll"
        >
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
                :class="[
                  'mango-mock-config-nav__item',
                  { 'mango-mock-config-nav__item--active': activeTab === item.key },
                ]"
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
                  <div class="mango-mock-config-panel__subtitle">{{
                    currentConfigNavItem.description
                  }}</div>
                </div>
                <a-tag
                  v-if="activeTab === 'basic' && form.id"
                  size="small"
                  :color="form.enabled ? 'green' : 'gray'"
                >
                  {{ form.enabled ? '已启用' : '已停用' }}
                </a-tag>
              </div>

              <div class="mango-mock-config-panel__body">
                <template v-if="methodsFailed"><a-button
                    size="small"
                    :loading="assertionMethodsLoading"
                    @click="loadAssertionMethods"
                    >重新加载</a-button></template>
                <div
                  v-show="activeTab === 'basic'"
                  class="mango-config-form-grid mango-mock-basic-grid"
                >
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label mango-mock-required">项目/产品</label>
                    <div class="mango-config-form-control"
                      ><ProjectProductSelect
                        :disabled="editingLocked"
                        v-model="form.project_product"
                        placeholder="请选择项目/产品"
                    /></div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label mango-mock-required">接口名称</label>
                    <div class="mango-config-form-control"
                      ><a-input
                        :disabled="editingLocked"
                        v-model="form.name"
                        placeholder="请输入接口名称"
                    /></div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label">请求方法</label>
                    <div class="mango-config-form-control">
                      <a-select
                        :disabled="editingLocked"
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
                    <div class="mango-config-form-control"
                      ><a-input
                        :disabled="editingLocked"
                        v-model="requestPath"
                        placeholder="如 /contracts/{contract_id}"
                    /></div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label">启用接口</label>
                    <div class="mango-config-form-control mango-mock-switch-control"
                      ><a-switch :disabled="editingLocked" v-model="form.enabled" size="small"
                    /></div>
                  </div>
                  <div class="mango-config-form-row">
                    <label class="mango-config-form-label">记录调用</label>
                    <div class="mango-config-form-control mango-mock-switch-control">
                      <a-switch
                        :disabled="editingLocked"
                        v-model="form.record_call_log"
                        size="small"
                      />
                      <span>记录普通调用；失败与平台异常始终记录</span>
                    </div>
                  </div>
                  <div class="mango-config-form-row mango-mock-config-row--full">
                    <label class="mango-config-form-label">请求解密</label>
                    <div class="mango-config-form-control mango-mock-decryption-mode">
                      <a-select
                        :disabled="editingLocked"
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
                    <a-alert
                      v-if="form.config.request_decryption.configuration_error"
                      type="warning"
                    >
                      {{ form.config.request_decryption.configuration_error }}
                    </a-alert>
                    <div class="mango-mock-decryption__fields">
                      <div class="mango-mock-decryption__field">
                        <label class="mango-mock-decryption__label mango-mock-required"
                          >Encrypt Key</label
                        >
                        <div class="mango-mock-decryption__control">
                          <a-input
                            :disabled="editingLocked"
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
                            :disabled="editingLocked"
                            v-model="form.config.request_decryption.verification_token"
                            placeholder="选填，配置后会校验解密结果"
                            allow-clear
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  <div
                    class="mango-config-form-row mango-mock-config-row--full mango-mock-config-row--textarea"
                  >
                    <label class="mango-config-form-label">接口说明</label>
                    <div class="mango-config-form-control"
                      ><a-textarea
                        :disabled="editingLocked"
                        v-model="form.description"
                        :auto-size="{ minRows: 2, maxRows: 4 }"
                        placeholder="请输入接口用途或使用说明"
                    /></div>
                  </div>
                  <div
                    v-if="requestPath"
                    class="mango-soft-panel mango-mock-url-preview mango-mock-config-row--full"
                  >
                    <span class="mango-mock-url-preview__label">调用地址</span>
                    <code>{{ mockUrl }}</code>
                    <a-button
                      v-if="form.id"
                      type="text"
                      size="small"
                      :loading="copying"
                      @click="copyCurl"
                      >复制 cURL</a-button
                    >
                  </div>
                </div>

                <div v-show="activeTab === 'assertions'">
                  <MockConditionEditor
                    :disabled="editingLocked"
                    v-model="form.config.assertions"
                    mode="assertion"
                    :assertion-methods="assertionMethods"
                    :methods-loading="assertionMethodsLoading"
                  />
                </div>

                <div v-show="activeTab === 'rules'">
                  <div class="mango-mock-rule-toolbar">
                    <span>按页面顺序匹配，首条命中后停止。</span>
                    <a-button size="small" type="primary" :disabled="editingLocked" @click="addRule"
                      >增加规则</a-button
                    >
                  </div>
                  <a-collapse v-model:active-key="activeRules" :bordered="false">
                    <a-collapse-item
                      v-for="(rule, index) in form.config.rules"
                      :key="rule.key"
                      :header="rule.name || `响应规则 ${index + 1}`"
                    >
                      <template #extra>
                        <a-space @click.stop>
                          <a-switch :disabled="editingLocked" v-model="rule.enabled" size="small" />
                          <a-button
                            type="text"
                            :disabled="editingLocked || index === 0"
                            @click="moveRule(index, -1)"
                            >上移</a-button
                          >
                          <a-button
                            type="text"
                            :disabled="editingLocked || index === form.config.rules.length - 1"
                            @click="moveRule(index, 1)"
                            >下移</a-button
                          >
                          <a-button
                            type="text"
                            status="danger"
                            :disabled="editingLocked"
                            @click="removeRule(index)"
                            >删除</a-button
                          >
                        </a-space>
                      </template>
                      <a-form :model="rule" class="mango-mock-rule-form">
                        <a-form-item label="规则名称"
                          ><a-input :disabled="editingLocked" v-model="rule.name"
                        /></a-form-item>
                      </a-form>
                      <div class="mango-section-title mango-mock-subtitle"
                        ><div><h3>匹配条件</h3></div></div
                      >
                      <MockConditionEditor
                        :disabled="editingLocked"
                        v-model="rule.matchers"
                        mode="matcher"
                        :assertion-methods="assertionMethods"
                        :methods-loading="assertionMethodsLoading"
                      />
                      <div class="mango-section-title mango-mock-subtitle"
                        ><div><h3>命中响应</h3></div></div
                      >
                      <MockResponseEditor
                        v-model="rule.response"
                        :disabled="editingLocked"
                        @validity-change="setResponseValidity(rule.key, $event)"
                      />
                    </a-collapse-item>
                  </a-collapse>
                  <div
                    v-if="form.config.rules.length === 0"
                    class="mango-empty-state mango-mock-empty-state"
                  >
                    暂无响应规则，可新增规则或直接使用默认响应
                  </div>
                </div>

                <div v-show="activeTab === 'default'">
                  <a-alert class="mango-mock-default-tip" type="info"
                    >没有响应规则命中时返回此内容。</a-alert
                  >
                  <MockResponseEditor
                    v-model="form.config.default_response"
                    :disabled="editingLocked"
                    @validity-change="setResponseValidity('__default__', $event)"
                  />
                </div>
              </div>
            </section>
          </div>
        </div>
      </MangoPanelSpin>
    </template>
  </TableBody>

  <MockDebugPanel ref="debugPanelRef" />
  <MockCallLogsPanel
    v-if="savedRecord?.id"
    :key="savedRecord.id"
    v-model:visible="logsVisible"
    :mock-id="savedRecord.id"
    :mock-key="savedRecord.mock_key"
  />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import MockCallLogsPanel from '../components/MockCallLogsPanel.vue'
  import {
    createMockConfig,
    getMockAssertionMethods,
    getMockConfigDetail,
    getMockEndpointUrl,
    updateMockConfig,
  } from '@/api/apitest/mock'
  import type { MockAssertionMethodOption } from '@/api/apitest/mock'
  import MockConditionEditor from './components/MockConditionEditor.vue'
  import MockResponseEditor from './components/MockResponseEditor.vue'
  import MockDebugPanel from './components/MockDebugPanel.vue'
  import { configSections, methodOptions, requestDecryptionOptions } from './config'
  import {
    createMockDraft,
    createMockRule,
    mockPayload,
    mockRequestPath,
    setMockRequestPath,
  } from './form'
  import type { MockDraft } from './types'

  const route = useRoute(),
    router = useRouter()
  const form = reactive(createMockDraft())
  const savedRecord = ref<MockDraft | null>(null)
  const loading = ref(false),
    saving = ref(false),
    copying = ref(false),
    ready = ref(false),
    loadFailed = ref(false)
  const assertionMethodsLoading = ref(false),
    methodsFailed = ref(false)
  const assertionMethods = ref<MockAssertionMethodOption[]>([])
  const activeTab = ref('basic'),
    activeRules = ref<string[]>([]),
    logsVisible = ref(false)
  const debugPanelRef = ref<InstanceType<typeof MockDebugPanel>>()
  const responseErrors = reactive(new Set<string>())
  const viewSession = ref(0)
  let active = true,
    currentIdentity: string | null | undefined,
    readSequence = 0,
    catalogSequence = 0
  const routeId = computed(() => (typeof route.query.id === 'string' ? route.query.id : null))
  const editingLocked = computed(() => !ready.value || loading.value || saving.value)
  const requestPath = computed({
    get: () => mockRequestPath(form),
    set: (value: string) => setMockRequestPath(form, value),
  })
  const mockUrl = computed(() => getMockEndpointUrl(requestPath.value))
  const configNavItems = computed(() =>
    configSections.map((item) => ({
      ...item,
      count:
        item.key === 'assertions'
          ? form.config.assertions.length
          : item.key === 'rules'
          ? form.config.rules.length
          : undefined,
    }))
  )
  const currentConfigNavItem = computed(
    () =>
      configNavItems.value.find((item) => item.key === activeTab.value) || configNavItems.value[0]
  )
  function isCurrent(session: number) {
    return active && route.path === '/apitest/mock/details' && session === viewSession.value
  }
  function setResponseValidity(key: string, valid: boolean) {
    valid ? responseErrors.delete(key) : responseErrors.add(key)
  }
  function closeWindows() {
    logsVisible.value = false
    debugPanelRef.value?.close()
  }
  async function initialize() {
    const session = ++viewSession.value
    currentIdentity = routeId.value
    closeWindows()
    responseErrors.clear()
    activeRules.value = []
    activeTab.value = 'basic'
    Object.assign(form, createMockDraft())
    savedRecord.value = null
    ready.value = false
    loadFailed.value = false
    if (!currentIdentity) {
      if (typeof route.query.project_product === 'string')
        form.project_product = route.query.project_product
      loading.value = false
      ready.value = true
      return
    }
    if (active) await loadDetail(session, currentIdentity)
  }
  async function loadDetail(session = viewSession.value, id = currentIdentity) {
    if (!active || !id || loading.value) return
    const sequence = ++readSequence
    loading.value = true
    loadFailed.value = false
    try {
      const response = await getMockConfigDetail(id)
      if (!isCurrent(session) || sequence !== readSequence) return
      const draft = createMockDraft(response.data)
      Object.assign(form, draft)
      savedRecord.value = createMockDraft(response.data)
      ready.value = true
      if (route.query.logs === '1') logsVisible.value = true
    } catch (loadFailure0) {
      if (isCurrent(session) && sequence === readSequence) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
    } finally {
      if (isCurrent(session) && sequence === readSequence) loading.value = false
    }
  }
  async function loadAssertionMethods() {
    if (!active || assertionMethodsLoading.value) return
    const sequence = ++catalogSequence
    assertionMethodsLoading.value = true
    methodsFailed.value = false
    try {
      const response = await getMockAssertionMethods()
      if (active && sequence === catalogSequence) assertionMethods.value = response.data || []
    } catch (loadFailure1) {
      if (active && sequence === catalogSequence) (reportLoadError(loadFailure1, "加载失败，请重试", false), methodsFailed.value = true)
    } finally {
      if (active && sequence === catalogSequence) assertionMethodsLoading.value = false
    }
  }
  function validate() {
    const payload = mockPayload(form)
    if (payload.project_product === '' || payload.project_product == null)
      return Message.error('请选择项目/产品'), false
    if (!form.name.trim()) return Message.error('请输入接口名称'), false
    if (!/^\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/.*)?$/.test(requestPath.value))
      return Message.error('请求路径须以 / 开头，首段仅支持小写字母、数字和短横线'), false
    if (savedRecord.value && form.mock_key !== savedRecord.value.mock_key)
      return Message.error('已保存接口不能修改请求路径首段，避免原调用地址失效'), false
    if (
      form.config.request_decryption.type === 'lark_event' &&
      !form.config.request_decryption.encrypt_key.trim()
    )
      return Message.error('请输入飞书 Encrypt Key'), false
    if (responseErrors.size) return Message.error('请修正响应头 JSON 后保存'), false
    return true
  }
  async function save() {
    if (!active || editingLocked.value || !validate()) return
    const session = viewSession.value,
      payload = mockPayload(form)
    saving.value = true
    try {
      const response = payload.id
        ? await updateMockConfig(payload)
        : await createMockConfig(payload)
      if (!isCurrent(session)) return
      const id = payload.id ?? response.data.id
      savedRecord.value = createMockDraft({ ...payload, ...response.data, id })
      form.id = id
      form.update_time = savedRecord.value.update_time
      Message.success('保存成功')
      if (!payload.id) {
        currentIdentity = String(id)
        await router.replace({ path: '/apitest/mock/details', query: { id } })
      }
    } catch {
      /* 公共请求层展示接口错误，保留当前草稿供重试。 */
    } finally {
      saving.value = false
    }
  }
  function addRule() {
    if (editingLocked.value) return
    const rule = createMockRule(form.config.rules.length)
    form.config.rules.push(rule)
    activeRules.value = [...activeRules.value, rule.key]
  }
  function removeRule(index: number) {
    if (editingLocked.value) return
    const [rule] = form.config.rules.splice(index, 1)
    if (rule) {
      responseErrors.delete(rule.key)
      activeRules.value = activeRules.value.filter((key) => key !== rule.key)
    }
  }
  function moveRule(index: number, offset: number) {
    const target = index + offset
    if (
      editingLocked.value ||
      index < 0 ||
      index >= form.config.rules.length ||
      target < 0 ||
      target >= form.config.rules.length
    )
      return
    const [rule] = form.config.rules.splice(index, 1)
    form.config.rules.splice(target, 0, rule)
  }
  async function copyCurl() {
    if (!savedRecord.value?.id || copying.value) return
    const session = viewSession.value,
      record = savedRecord.value
    const method =
      methodOptions.find((item) => item.value === record.config.methods[0])?.label || 'GET'
    const url = getMockEndpointUrl(mockRequestPath(record)).replace(/'/g, `'"'"'`)
    copying.value = true
    try {
      await navigator.clipboard.writeText(`curl -X ${method} '${url}'`)
      if (isCurrent(session)) Message.success('cURL 已复制')
    } catch {
      if (isCurrent(session)) Message.error('复制失败，请检查剪贴板权限')
    } finally {
      copying.value = false
    }
  }
  function openDebug() {
    const record = savedRecord.value
    if (active && record?.id)
      debugPanelRef.value?.open({
        id: record.id,
        requestPath: mockRequestPath(record),
        methods: [...record.config.methods],
      })
  }
  function openLogs() {
    if (active && savedRecord.value?.id) logsVisible.value = true
  }
  function suspend() {
    active = false
    ++viewSession.value
    ++readSequence
    ++catalogSequence
    loading.value = false
    assertionMethodsLoading.value = false
    closeWindows()
  }
  watch(
    [() => route.path, routeId],
    () => {
      if (route.path !== '/apitest/mock/details') return
      if (routeId.value !== currentIdentity) {
        ++readSequence
        loading.value = false
        void initialize()
      }
    },
    { immediate: true }
  )
  void loadAssertionMethods()
  onDeactivated(suspend)
  onBeforeUnmount(suspend)
  onActivated(() => {
    active = true
    if (currentIdentity !== routeId.value || !ready.value) void initialize()
    if (!assertionMethods.value.length) void loadAssertionMethods()
  })
</script>

<style scoped>
  .mango-mock-detail-spin {
    width: 100%;
    height: 100%;
  }
  .mango-mock-workbench-scroll {
    --mango-workbench-min-width: 980px;
    height: 100%;
  }
  .mango-mock-detail-workbench {
    display: grid;
    grid-template-columns: 210px minmax(0, 1fr);
    gap: var(--m-page-gap);
    height: calc(100% - var(--m-page-gap));
    min-height: 540px;
  }
  .mango-mock-config-nav,
  .mango-mock-config-panel {
    min-width: 0;
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }
  .mango-mock-config-nav {
    overflow: auto;
    padding: 12px;
  }
  .mango-mock-config-nav__head {
    margin-bottom: 10px;
  }
  .mango-mock-config-nav__title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }
  .mango-mock-config-nav__subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
  .mango-mock-config-nav__item {
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
  .mango-mock-config-nav__item:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    background: var(--m-surface);
  }
  .mango-mock-config-nav__item--active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
  }
  .mango-mock-config-nav__item-title {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }
  .mango-mock-config-nav__item-title > span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-mock-config-nav__item small {
    display: block;
    overflow: hidden;
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-mock-config-panel {
    display: flex;
    overflow: hidden;
    flex-direction: column;
  }
  .mango-mock-config-panel__head {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-mock-config-panel__title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }
  .mango-mock-config-panel__subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
  .mango-mock-config-panel__body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 12px;
  }
  .mango-mock-basic-grid {
    width: 100%;
    max-width: 980px;
    align-content: start;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 18px;
  }
  .mango-mock-config-row--full {
    grid-column: 1 / -1;
  }
  .mango-mock-config-row--textarea {
    align-items: start;
  }
  .mango-mock-required::before {
    margin-right: 4px;
    color: var(--m-danger);
    content: '*';
  }
  .mango-mock-switch-control {
    display: flex;
    min-height: 32px;
    align-items: center;
    gap: 8px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
  .mango-mock-decryption-mode {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 10px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
  .mango-mock-decryption-mode__select {
    width: 220px;
    flex: 0 0 220px;
  }
  .mango-mock-decryption {
    margin-left: 109px;
    padding: 10px 12px;
  }
  .mango-mock-decryption__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 18px;
  }
  .mango-mock-decryption__field {
    display: grid;
    min-width: 0;
    grid-template-columns: 112px minmax(0, 1fr);
    align-items: center;
    gap: 9px;
  }
  .mango-mock-decryption__label {
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
    text-align: right;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-mock-decryption__control {
    min-width: 0;
  }
  .mango-mock-decryption__control :deep(.arco-input-wrapper) {
    width: 100%;
  }
  .mango-mock-url-preview {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    word-break: break-all;
  }
  .mango-mock-url-preview__label {
    color: var(--m-muted);
    white-space: nowrap;
  }
  .mango-mock-url-preview code {
    min-width: 0;
    font-family: var(--m-font-mono);
  }
  .mango-mock-rule-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--m-muted);
  }
  .mango-mock-rule-form {
    max-width: 520px;
  }
  .mango-mock-subtitle {
    margin-top: 12px;
  }
  .mango-mock-default-tip {
    margin-bottom: 10px;
  }
  .mango-mock-empty-state {
    min-height: 180px;
  }
  .mango-mock-detail-spin :deep(> .mango-panel-spin__content) {
    height: 100%;
  }
  .mango-mock-config-panel {
    container-type: inline-size;
  }
  @container (max-width: 860px) {
    .mango-mock-basic-grid,
    .mango-mock-decryption__fields {
      grid-template-columns: minmax(0, 1fr);
    }
    .mango-mock-decryption-mode {
      align-items: flex-start;
      flex-direction: column;
    }
    .mango-mock-decryption-mode__select {
      width: 100%;
      flex-basis: auto;
    }
    .mango-mock-decryption {
      margin-left: 0;
    }
  }
</style>
