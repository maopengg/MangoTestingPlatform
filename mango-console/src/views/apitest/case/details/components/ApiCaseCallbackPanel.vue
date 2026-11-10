<template>
  <div v-if="true" class="mango-callback-panel">
    <a-alert v-if="view !== 'results' && configurationBlock" class="mango-callback-panel__notice" type="warning">{{
      configurationBlock
    }}</a-alert>
    <a-alert v-if="view !== 'results'" class="mango-callback-panel__notice"
      >先配置独立测试应用的 Mock 回调地址。触发请求可使用
      <code v-text="'${{callback_run_id}}'"></code
      >，每次执行自动生成；回调须透传此标识。触发场景需关闭失败重试。</a-alert
    >
    <template v-if="view !== 'results'">
      <a-button
        v-if="!editLocked"
        size="small"
        type="primary"
        :disabled="!canConfigure || rules.length >= 5 || savePending"
        :loading="saving"
        @click="editRule()"
        >新增回调验证</a-button
      >
      <a-table
        :columns="ruleColumns"
        :data="scopedRules"
        :pagination="false"
        :scroll="{ x: 520 }"
        row-key="key"
      >
        <template #name="{ record }">
          {{ record.name }}
          <a-tag v-if="record.enabled === false" size="small" color="orange">旧规则未启用</a-tag>
        </template>
        <template #actions="{ record }">
          <MangoTableActions
            :actions="[
              {
                label: canConfigure ? '编辑' : '查看',
                disabled: saving || savePending,
                onClick: () => editRule(record),
              },
              {
                label: '删除',
                danger: true,
                hidden: editLocked,
                loading: saving,
                disabled: savePending,
                onClick: () => removeRule(record.key),
              },
            ]"
          />
        </template>
        <template #empty>
          <div class="mango-empty-state">当前接口暂无回调断言，点击“新增回调验证”配置。</div>
        </template>
      </a-table>
    </template>
    <ApiCaseCallbackAssertions
      v-else
      :case-id="caseId"
      :runs="archivedResults || []"
      @evidence="openDeliveries"
    />

    <BaseSidePanel
      v-model:visible="editorVisible"
      :width="1100"
      :title="`回调断言 · ${triggerLabel}`"
      :mask-closable="!saving"
    >
      <a-alert v-if="form.enabled === false" type="warning" class="mango-callback-legacy-hint">
        该历史规则未启用。{{
          canConfigure
            ? '保存后将启用并参与执行；不需要此规则可取消后删除。'
            : '当前仅查看，不会改变其执行状态。'
        }}
      </a-alert>
      <a-form
        :model="form"
        class="mango-callback-form"
        layout="horizontal"
        :disabled="!canConfigure || saving || savePending"
        auto-label-width
      >
        <section class="mango-callback-form-section">
          <header class="mango-section-title"><h2>回调关联</h2></header>
          <div class="mango-config-form-grid mango-callback-form-fields">
            <a-form-item label="Mock 接口" class="mango-callback-form-wide" required>
              <a-select
                v-model="form.mock_config_id"
                :loading="mockLoading"
                allow-search
                :options="mockOptions"
                @search="searchMocks"
              />
            </a-form-item>
            <a-form-item label="关联来源" required>
              <a-select v-model="form.correlation.source" :options="sourceOptions" />
            </a-form-item>
            <a-form-item label="关联字段" required
              ><a-input v-model="form.correlation.field" placeholder="$.header.event_id"
            /></a-form-item>
            <a-form-item label="匹配缓存键" class="mango-callback-form-wide" required>
              <a-input
                v-model="form.correlation.expected.cache_key"
                placeholder="callback_run_id"
              />
              <template #extra>
                <span class="mango-callback-hint"
                  >从关联字段取出的回调值，须等于本次 Case 中该缓存键的值。默认 callback_run_id
                  由平台每次执行自动生成；填写键名，不填实际值。</span
                >
              </template>
            </a-form-item>
            <a-form-item label="事件ID来源" required>
              <a-select v-model="form.event_id_source" :options="sourceOptions" />
            </a-form-item>
            <a-form-item label="事件ID字段" required>
              <a-input v-model="form.event_id_field" placeholder="$.header.event_id" />
              <template #extra
                ><span class="mango-callback-hint"
                  >用于区分不同事件；相同事件 ID 的多次回调按重复投递统计，不用于匹配本次
                  Case。</span
                ></template
              >
            </a-form-item>
            <a-form-item label="等待超时（秒）"
              ><a-input-number v-model="form.timeout_seconds" :min="1" :max="300"
            /></a-form-item>
          </div>
        </section>
        <section class="mango-callback-form-section">
          <div class="mango-section-title mango-callback-check-toolbar">
            <h2>断言内容（{{ form.checks.length }} 项）</h2>
            <a-button
              v-if="canConfigure"
              size="small"
              :disabled="saving || savePending || form.checks.length >= 30"
              @click="addCheck"
              >增加检查项</a-button
            >
          </div>
          <div class="mango-callback-check-table">
            <a-table
              class="mango-native-scroll-table"
              v-model:expanded-keys="expandedCheckKeys"
              :columns="checkColumns"
              :data="form.checks"
              :pagination="false"
              :scroll="{ x: 1100, y: '100%' }"
              row-key="key"
              size="small"
            >
              <template #index="{ rowIndex }">{{ rowIndex + 1 }}</template>
              <template #type="{ record: check }">
                <a-select
                  v-model="check.type"
                  :options="checkTypes"
                  :disabled="!canConfigure || saving || savePending"
                  aria-label="检查类型"
                  @change="changeCheckType(check)"
                />
              </template>
              <template #source="{ record: check }">
                <span v-if="check.type.includes('signature')">原始正文</span>
                <a-select
                  v-else
                  v-model="check.source"
                  :options="check.type === 'json_compact' ? compactSources : fieldSources"
                  :disabled="!canConfigure || saving || savePending"
                  aria-label="检查来源"
                />
              </template>
              <template #field="{ record: check }">
                <a-tooltip
                  v-if="check.type === 'field'"
                  :content="check.field || '填写回调字段的 JSONPath'"
                >
                  <a-input
                    v-model="check.field"
                    :disabled="!canConfigure || saving || savePending"
                    aria-label="回调字段"
                    placeholder="JSONPath，例如 $.event.id"
                  />
                </a-tooltip>
                <span v-else>—</span>
              </template>
              <template #summary="{ record: check }">
                <a-tooltip :content="callbackCheckSummary(check)">
                  <span class="mango-callback-check-summary">{{
                    callbackCheckSummary(check)
                  }}</span>
                </a-tooltip>
              </template>
              <template #actions="{ record: check }">
                <MangoTableActions
                  :actions="[
                    {
                      label: expandedCheckKeys.includes(check.key)
                        ? '收起'
                        : check.type === 'field'
                        ? '配置断言'
                        : '说明',
                      disabled: saving || savePending,
                      onClick: () => toggleCheck(check.key),
                    },
                    {
                      label: '移除',
                      danger: true,
                      hidden: !canConfigure,
                      disabled: saving || savePending,
                      onClick: () => removeCheck(check.key),
                    },
                  ]"
                />
              </template>
              <template #expand-row="{ record: check }">
                <div class="mango-callback-check-editor">
                  <template v-if="check.type === 'field'">
                    <template v-if="!check.general_editor">
                      <a-form-item label="判断"
                        ><a-select
                          v-model="check.operator"
                          :options="[
                            { label: '等于', value: 'equals' },
                            { label: '包含', value: 'contains' },
                            { label: '存在', value: 'exists' },
                          ]"
                      /></a-form-item>
                      <a-form-item v-if="check.operator !== 'exists'" label="期望值"
                        ><a-input
                          v-model="check.expected_text"
                          placeholder='JSON 值，例如 "approved"、200、true'
                      /></a-form-item>
                      <a-button
                        size="small"
                        :disabled="!canConfigure || saving || savePending"
                        @click="useGeneralAssertions(check)"
                        >改用通用断言</a-button
                      >
                    </template>
                    <template v-else>
                      <p class="mango-callback-hint"
                        >实际值取自上方回调字段；预期值可使用本次 Case
                        缓存变量。关系与外部通用断言一致。</p
                      >
                      <div class="mango-horizontal-scroll-region"
                        ><GeneralAssertionEditor
                          v-model="check.assertions"
                          :methods="generalMethods || []"
                          :edit-locked="!canConfigure || saving || savePending"
                          show-actions
                          callback-actual
                      /></div>
                    </template>
                  </template>
                  <p v-if="check.type === 'lark_signature'" class="mango-callback-hint"
                    >使用 Mock 的飞书 Encrypt Key，按原始正文验证 X-Lark-Signature。密钥不写入 Case
                    或报告。</p
                  >
                  <p
                    v-if="check.type === 'lark_compact_signature_simulation'"
                    class="mango-callback-hint"
                    >仅模拟去掉 JSON 格式空白后验签；结果不决定 Case
                    成败，也不能证明客户实际实现如此。</p
                  >
                  <p v-if="check.type === 'json_compact'" class="mango-callback-hint">
                    检查 JSON 是否采用紧凑格式；字符串内容中的空格、换行不受影响。
                  </p>
                </div>
              </template>
              <template #empty
                ><div class="mango-empty-state">暂无检查项，点击“增加检查项”配置。</div></template
              >
            </a-table>
          </div>
        </section>
        <a-collapse
          v-model:active-key="advancedKeys"
          :bordered="false"
          class="mango-callback-advanced"
        >
          <a-collapse-item
            key="advanced"
            :header="hasCustomSettings ? '高级配置（已自定义）' : '高级配置（可选）'"
          >
            <div class="mango-config-form-grid mango-callback-form-fields">
              <a-form-item label="观察窗口（秒）">
                <a-input-number v-model="form.observation_seconds" :min="0" :max="299" />
              </a-form-item>
              <a-form-item label="事件数量">
                <a-input-group class="mango-callback-event-count">
                  <a-select v-model="form.events.mode" :options="eventModeOptions" />
                  <a-input-number v-model="form.events.count" :min="1" :max="100" />
                </a-input-group>
              </a-form-item>
              <a-form-item label="投递判定">
                <a-select v-model="form.delivery_policy" :options="deliveryPolicyOptions" />
              </a-form-item>
              <a-form-item label="最少投递次数">
                <a-input-number v-model="form.min_deliveries" :min="1" :max="100" />
              </a-form-item>
              <a-form-item label="最多投递次数">
                <a-input-number v-model="form.max_deliveries" :min="1" :max="100" />
              </a-form-item>
              <a-form-item label="重试最小间隔(ms)">
                <a-input-number v-model="form.min_retry_interval_ms" :min="0" :max="300000" />
              </a-form-item>
              <a-form-item label="重试最大间隔(ms)">
                <a-input-number
                  v-model="form.max_retry_interval_ms"
                  :min="0"
                  :max="300000"
                  placeholder="留空不限制"
                  allow-clear
                />
              </a-form-item>
              <a-form-item label="检查失败响应" class="mango-callback-form-wide">
                <a-select v-model="form.response_mode" :options="responseModeOptions" />
              </a-form-item>
              <a-form-item v-if="form.response_mode === 'strict'" label="失败HTTP状态">
                <a-input-number v-model="form.failure_status" :min="400" :max="599" />
              </a-form-item>
              <p v-if="form.response_mode === 'strict'" class="mango-callback-hint">
                严格模式可能触发发送端重试，请使用独立测试应用并配置观察窗口。
              </p>
            </div>
          </a-collapse-item>
        </a-collapse>
      </a-form>
      <template #footer-buttons
        ><a-button size="small" :disabled="saving" @click="editorVisible = false">取消</a-button
        ><a-button
          v-if="canConfigure"
          size="small"
          type="primary"
          :loading="saving"
          :disabled="savePending && !saving"
          @click="saveRule"
          >{{ form.enabled === false ? '保存并启用' : '保存' }}</a-button
        ></template
      >
    </BaseSidePanel>

    <a-drawer
      v-model:visible="evidenceVisible"
      :width="'70%'"
      title="回调投递证据"
      :footer="false"
      unmount-on-close
    >
      <a-table
        :columns="deliveryColumns"
        :data="deliveries"
        :loading="evidenceLoading"
        :pagination="{ current: deliveryPage, total: deliveryTotal, pageSize: 10 }"
        :scroll="{ x: 780 }"
        row-key="id"
        @page-change="loadDeliveries"
      >
        <template #passed="{ record }"
          ><a-tag :color="record.passed ? 'green' : 'red'" size="small">{{
            record.passed ? '通过' : '失败'
          }}</a-tag></template
        >
        <template #actions="{ record }"
          ><MangoTableActions
            :actions="[
              {
                label: '查看内容',
                onClick: () => showEvidence(record.id),
              },
            ]"
        /></template>
      </a-table>
      <mango-panel-spin :loading="detailLoading">
        <template v-if="evidence">
          <a-button
            size="small"
            :loading="downloading"
            :disabled="!evidence.evidence_complete || evidence.evidence_expired"
            @click="downloadEvidence"
            >下载原始报文</a-button
          >
          <p class="mango-callback-hint"
            >SHA-256：{{ evidence.body_sha256 }} · {{ evidence.body_length }} 字节 ·
            {{
              evidence.evidence_expired
                ? '原始证据已到期清理'
                : evidence.evidence_complete
                ? '证据完整'
                : '证据不完整'
            }}</p
          >
          <div v-for="check in evidence.checks" :key="check.key" class="mango-callback-check-result"
            ><a-tag
              :color="check.passed ? 'green' : check.diagnostic ? 'orange' : 'red'"
              size="small"
              >{{ check.diagnostic ? '诊断' : check.passed ? '通过' : '失败' }}</a-tag
            >{{ check.key }} {{ check.message }}
            <div
              v-for="(assertion, index) in check.assertions || []"
              :key="index"
              class="mango-callback-hint"
            >
              {{ assertion.method }} · {{ assertion.status === 1 ? '通过' : '失败' }}
              <span v-if="assertion.group_name">
                · {{ assertion.group_name }}（{{ assertion.group_logic }}）：组{{
                  assertion.group_result ? '通过' : '失败'
                }}</span
              >
            </div></div
          >
          <a-tabs
            ><a-tab-pane key="raw" title="原始正文">
              <pre class="mango-code-panel">{{ evidence.raw_body }}</pre></a-tab-pane
            ><a-tab-pane key="business" title="解密正文">
              <pre class="mango-code-panel">{{ evidence.business_body }}</pre></a-tab-pane
            ><a-tab-pane key="headers" title="协议请求头">
              <pre class="mango-code-panel">{{ JSON.stringify(evidence.headers, null, 2) }}</pre>
            </a-tab-pane></a-tabs
          >
        </template>
      </mango-panel-spin>
    </a-drawer>
  </div>
  <a-alert v-else>查看回调配置和证据需要用例详情及 Mock 详情权限。</a-alert>
</template>

<script setup lang="ts">
  import { computed, ref, watch, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import GeneralAssertionEditor from '@/components/forms/GeneralAssertionEditor.vue'
  import ApiCaseCallbackAssertions from './ApiCaseCallbackAssertions.vue'
  import { getMockConfigs } from '@/api/apitest/mock'
  import { getCallbackDeliveries, downloadCallbackEvidence } from '@/api/apitest/callback'

  import { useEnum } from '@/store/modules/get-enum'
  import type { CallbackRuleDraft, CallbackDelivery } from '../types'
  import {
    createCallbackRuleDraft,
    ruleColumns,
    deliveryColumns,
    callbackRulesForStep,
    callbackConfigurationBlock,
    callbackRuleName,
    hasCustomCallbackSettings,
    checkColumns,
    callbackCheckSummary,
    callbackRequiredConfigError,
  } from './callback-config'

  const props = defineProps<{
    caseId: number | string
    productId: number | string
    rules: CallbackRuleDraft[]
    triggerStep: any
    scenarioCount: number
    scenarioRetry?: number
    active: boolean
    savePending: boolean
    persistRules: (rules: CallbackRuleDraft[]) => Promise<boolean>
    editLocked: boolean
    traceId?: string
    generalMethods?: any[]
    view?: 'config' | 'results'
    archivedResults?: any[]
  }>()

  const canEdit = computed(() => !props.editLocked)
  const stepKey = computed(() => (props.triggerStep?.id ? `step-${props.triggerStep.id}` : ''))
  const scopedRules = computed(() => callbackRulesForStep(props.rules, props.triggerStep?.id))
  const configurationBlock = computed(() =>
    callbackConfigurationBlock(props.triggerStep, props.scenarioCount, props.scenarioRetry)
  )
  const canConfigure = computed(() => canEdit.value && !configurationBlock.value)
  const triggerLabel = computed(() =>
    String(
      props.triggerStep?.api_info?.name || props.triggerStep?.name || props.triggerStep?.id || ''
    )
  )
  const enumStore = useEnum()
  const options = (key: string): Array<{ label: string; value: string }> =>
    ((enumStore as any)[key] || []).map((item: any) => ({ label: item.title, value: item.key }))
  const sourceOptions = computed(() =>
    options('api_callback_source').filter((item) => item.value !== 'raw_body')
  )
  const fieldSources = computed(() => options('api_callback_source'))
  const compactSources = computed(() =>
    fieldSources.value.filter((item) => ['raw_body', 'business_json'].includes(item.value))
  )
  const checkTypes = computed(() => options('api_callback_check_type'))
  const eventModeOptions = computed(() => options('api_callback_event_mode'))
  const deliveryPolicyOptions = computed(() => options('api_callback_delivery_policy'))
  const responseModeOptions = computed(() => options('api_callback_response_mode'))

  const editorVisible = ref(false)
  const saving = ref(false)
  const mockLoading = ref(false)
  const mockOptions = ref<Array<{ value: number; label: string }>>([])
  let mockRequest = 0
  const form = ref<CallbackRuleDraft>(createCallbackRuleDraft('', '', ''))
  const advancedKeys = ref<string[]>([])
  const expandedCheckKeys = ref<string[]>([])
  const hasCustomSettings = computed(() => hasCustomCallbackSettings(form.value))
  const evidenceVisible = ref(false)
  const evidenceLoading = ref(false)
  const detailLoading = ref(false)
  const deliveries = ref<CallbackDelivery[]>([])
  const deliveryPage = ref(1)
  const deliveryTotal = ref(0)
  const runId = ref(0)
  const evidence = ref<CallbackDelivery | null>(null)
  const downloading = ref(false)
  let deliveryRequest = 0
  let detailRequest = 0
  let editorSession = 0
  let downloadSession = 0
  watch(
    () => [
      props.caseId,
      props.productId,
      props.traceId,
      stepKey.value,
      props.editLocked,
      props.active,
    ],
    () => {
      editorSession++
      downloadSession++
      deliveryRequest++
      detailRequest++
      mockRequest++
      deliveries.value = []
      evidence.value = null
      editorVisible.value = false
      evidenceVisible.value = false
      mockLoading.value = false
      evidenceLoading.value = false
      detailLoading.value = false
    }
  )
  const newKey = () => globalThis.crypto.randomUUID().replaceAll('-', '')

  function editRule(rule?: CallbackRuleDraft) {
    if (saving.value || props.savePending || (!rule && !canConfigure.value)) return
    if (rule && rule.trigger_step_key !== stepKey.value) return
    editorSession++
    form.value = rule
      ? JSON.parse(JSON.stringify(rule))
      : createCallbackRuleDraft(
          newKey(),
          stepKey.value,
          callbackRuleName(triggerLabel.value, scopedRules.value),
          newKey
        )
    form.value.checks.forEach((check: any) => {
      check.expected_text = JSON.stringify(check.expected ?? '')
      check.general_editor = Boolean(check.assertions?.length)
    })
    advancedKeys.value = []
    expandedCheckKeys.value = []
    editorVisible.value = true
    searchMocks('')
  }
  async function searchMocks(keyword: string) {
    const request = ++mockRequest
    mockLoading.value = true
    try {
      const response = await getMockConfigs({
        project_product: props.productId,
        name: keyword,
        page: 1,
        pageSize: 100,
      })
      if (request === mockRequest)
        mockOptions.value = (response.data || []).map((item: any) => ({
          value: item.id,
          label: item.name,
        }))
    } catch {
      if (request === mockRequest) mockOptions.value = []
    } finally {
      if (request === mockRequest) mockLoading.value = false
    }
  }
  function addCheck() {
    if (!canConfigure.value || saving.value || props.savePending || form.value.checks.length >= 30)
      return
    const key = newKey()
    form.value.checks.push({
      key,
      type: 'field',
      source: 'business_json',
      field: '',
      operator: 'equals',
      expected: '',
      expected_text: '""',
      assertions: [{ group_name: '', group_logic: 'AND', method: '', value: {} }],
      general_editor: true,
    })
    expandedCheckKeys.value = [key]
  }
  function toggleCheck(key: string) {
    expandedCheckKeys.value = expandedCheckKeys.value.includes(key) ? [] : [key]
  }
  function removeCheck(key: string) {
    if (!canConfigure.value || saving.value || props.savePending) return
    form.value.checks = form.value.checks.filter((check: any) => check.key !== key)
    expandedCheckKeys.value = expandedCheckKeys.value.filter((item) => item !== key)
  }
  function useGeneralAssertions(check: any) {
    check.general_editor = true
    check.assertions = [{ group_name: '', group_logic: 'AND', method: '', value: {} }]
  }
  function changeCheckType(check: any) {
    check.source = check.type === 'field' ? 'business_json' : 'raw_body'
    check.assertions = []
    check.general_editor = false
    if (check.type === 'field') useGeneralAssertions(check)
  }
  async function persist(rules: CallbackRuleDraft[]) {
    if (saving.value || props.savePending || props.editLocked) return false
    saving.value = true
    try {
      if (!(await props.persistRules(rules))) return false
      Message.success('回调验证已保存；发布态执行需生成新修订并发布')
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  async function saveRule() {
    if (!canConfigure.value) {
      if (configurationBlock.value) Message.warning(configurationBlock.value)
      return
    }
    const requiredError = callbackRequiredConfigError(form.value)
    if (requiredError) {
      Message.warning(requiredError)
      return
    }
    const rule = JSON.parse(JSON.stringify(form.value))
    if (
      rule.checks.some(
        (check: any) =>
          check.type === 'field' &&
          check.general_editor &&
          (!check.assertions?.length ||
            check.assertions.some(
              (item: any) =>
                !item.value?.value ||
                !item.value?.parameter?.some((parameter: any) => parameter.f === 'actual')
            ))
      )
    ) {
      Message.warning('请至少配置一条通用断言，并选择断言方法')
      return
    }
    rule.name ||= callbackRuleName(triggerLabel.value, scopedRules.value)
    rule.enabled = true
    rule.trigger_step_key = stepKey.value
    try {
      rule.checks.forEach((check: any) => {
        if (check.type === 'field' && !check.assertions?.length && check.operator !== 'exists')
          check.expected = JSON.parse(check.expected_text)
        delete check.expected_text
        delete check.general_editor
      })
    } catch {
      Message.warning('期望值需要是有效 JSON，字符串请加双引号')
      return
    }
    const session = editorSession
    const rules = props.rules.some((item) => item.key === rule.key)
      ? props.rules.map((item) => (item.key === rule.key ? rule : item))
      : [...props.rules, rule]
    if ((await persist(rules)) && session === editorSession) editorVisible.value = false
  }
  async function removeRule(key: string) {
    if (!scopedRules.value.some((rule) => rule.key === key)) return
    await persist(props.rules.filter((item) => item.key !== key))
  }
  async function openDeliveries(run: any) {
    runId.value = run.id
    evidence.value = null
    deliveries.value = []
    evidenceVisible.value = true
    await loadDeliveries()
  }
  async function loadDeliveries(current = 1) {
    const request = ++deliveryRequest
    detailRequest++
    evidence.value = null
    detailLoading.value = false
    evidenceLoading.value = true
    try {
      const response = await getCallbackDeliveries({
        case_id: props.caseId,
        run_id: runId.value,
        page: current,
        page_size: 10,
      })
      if (request !== deliveryRequest) return
      deliveries.value = response.data.items
      deliveryTotal.value = response.data.count
      deliveryPage.value = current
    } catch {
      if (request === deliveryRequest) deliveries.value = []
    } finally {
      if (request === deliveryRequest) evidenceLoading.value = false
    }
  }
  async function showEvidence(id: number) {
    const request = ++detailRequest
    detailLoading.value = true
    try {
      const response = await getCallbackDeliveries({
        case_id: props.caseId,
        run_id: runId.value,
        delivery_id: id,
      })
      if (request === detailRequest) evidence.value = response.data.items[0] || null
    } catch {
      if (request === detailRequest) evidence.value = null
    } finally {
      if (request === detailRequest) detailLoading.value = false
    }
  }
  async function downloadEvidence() {
    if (!evidence.value || downloading.value) return
    downloading.value = true
    const deliveryId = evidence.value.id,
      token = ++downloadSession
    try {
      const response = await downloadCallbackEvidence({
        case_id: props.caseId,
        run_id: runId.value,
        delivery_id: deliveryId,
      })
      if (token !== downloadSession || !evidenceVisible.value) return
      if (!(response.data instanceof Blob) || response.data.type.includes('json')) {
        Message.error('原始证据下载失败，请检查权限或保留期')
        return
      }
      const href = URL.createObjectURL(response.data)
      const anchor = document.createElement('a')
      anchor.href = href
      anchor.download = `callback-${deliveryId}.bin`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(href), 1000)
    } catch {
      Message.error('原始证据下载失败')
    } finally {
      if (token === downloadSession) downloading.value = false
    }
  }
  function closePanels() {
    editorSession++
    deliveryRequest++
    detailRequest++
    mockRequest++
    downloadSession++
    editorVisible.value = evidenceVisible.value = false
    mockLoading.value = evidenceLoading.value = detailLoading.value = downloading.value = false
  }
  watch(editorVisible, (visible) => {
    if (!visible) {
      editorSession++
      mockRequest++
      mockLoading.value = false
    }
  })
  watch(evidenceVisible, (visible) => {
    if (!visible) {
      deliveryRequest++
      detailRequest++
      downloadSession++
      evidenceLoading.value = detailLoading.value = downloading.value = false
    }
  })
  onBeforeUnmount(closePanels)
  onDeactivated(closePanels)
</script>

<style scoped>
  .mango-callback-panel {
    min-width: 0;
  }
  .mango-callback-panel__notice {
    margin-bottom: var(--m-page-gap);
  }
  .mango-callback-panel :deep(.arco-table) {
    margin-top: var(--m-page-gap);
  }
  .mango-callback-hint {
    color: var(--m-muted);
    overflow-wrap: anywhere;
    font-size: 12px;
    line-height: 1.6;
    margin-block: var(--m-page-gap);
  }
  .mango-callback-form {
    container-type: inline-size;
  }
  .mango-callback-form-section + .mango-callback-form-section {
    margin-top: var(--m-page-gap);
    padding-top: var(--m-card-padding);
    border-top: 1px solid var(--m-border);
  }
  .mango-callback-form-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
    gap: 12px 16px;
  }
  .mango-callback-form-fields :deep(.arco-form-item) {
    min-width: 0;
    margin-bottom: 0;
    flex-wrap: nowrap;
  }
  .mango-callback-form-fields :deep(.arco-form-item-label-col) {
    flex: 0 0 132px;
    width: 132px;
    max-width: 132px;
    white-space: nowrap;
  }
  .mango-callback-form-fields :deep(.arco-form-item-wrapper-col) {
    flex: 1 1 0;
    width: 0;
    max-width: none;
    min-width: 0;
  }
  .mango-callback-form-fields :deep(.arco-input-number) {
    width: 100%;
  }
  .mango-callback-form-fields :deep(.arco-form-item-extra) {
    margin-top: 4px;
    color: var(--m-muted);
  }
  .mango-callback-form-wide {
    grid-column: 1 / -1;
  }
  .mango-callback-event-count {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }
  @container (max-width: 680px) {
    .mango-callback-form-fields {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  .mango-callback-advanced {
    margin-top: var(--m-page-gap);
  }
  .mango-callback-legacy-hint {
    margin-bottom: var(--m-page-gap);
  }
  .mango-callback-check-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
  }
  .mango-callback-check-summary {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-callback-check-table {
    height: 480px;
    min-height: 0;
    overflow: hidden;
  }
  .mango-callback-check-table :deep(.arco-scrollbar-container) {
    overscroll-behavior: contain;
  }
  .mango-callback-check-editor {
    min-width: 0;
    padding: var(--m-card-padding);
  }
  .mango-callback-check-editor :deep(.mango-key-value-row) {
    display: grid;
    grid-template-columns: minmax(140px, 1fr) minmax(0, 3fr);
  }
  .mango-callback-check-editor :deep(.mango-button-container) {
    grid-column: 1 / -1;
    min-width: 0;
    width: 100%;
    margin-left: 0;
    justify-self: stretch;
  }
  .mango-callback-check-editor :deep(.mango-general-assertion-parameters) {
    min-width: 0;
  }
  .mango-callback-check-editor :deep(.mango-general-assertion-parameter) {
    min-width: 0;
  }
  .mango-callback-check-result {
    display: flex;
    align-items: center;
    gap: var(--m-page-gap);
    margin-block: var(--m-page-gap);
  }
  .mango-code-panel {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    max-height: 480px;
    overflow: auto;
  }
</style>
