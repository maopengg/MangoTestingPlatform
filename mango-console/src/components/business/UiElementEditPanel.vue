<template>
  <BaseSidePanel
    :visible="visible"
    :title="title"
    width="min(760px, 92vw)"
    @update:visible="(val) => { visible = val }"
    @cancel="visible = false"
  >
    <a-spin :loading="loading" class="mango-ui-element-edit-spin">
      
      <MangoRequestFeedback v-if="saveError" :message="(saveError)" />
      <a-form
        :model="form"
        layout="horizontal"
        label-align="right"
        class="mango-ui-element-edit-form"
      >
        <section class="mango-ui-element-edit-section">
          <div class="mango-ui-element-edit-section-head">
            <h3>元素基本信息</h3>
            <span>用于识别和分类页面元素</span>
          </div>
          <div class="mango-ui-element-edit-grid">
            <a-form-item required>
              <template #label>
                <span class="mango-ui-element-field-label">
                  元素名称
                  <a-tooltip content="会参与描述定位和 AI 自愈。建议写清控件用途，如“订单类型名称输入框”，避免只写“输入框”。">
                    <span class="mango-ui-element-field-help" aria-label="元素名称填写说明">
                      <icon-question-circle />
                    </span>
                  </a-tooltip>
                </span>
              </template>
              <a-input v-model="form.name" placeholder="请输入元素名称" data-testid="qa-components-business-uielementeditpanel-input-请输入元素名称" />
            </a-form-item>
            <a-form-item required>
              <template #label>
                <span class="mango-ui-element-field-label">
                  元素分类
                  <a-tooltip content="用于页面内分组，也会作为描述定位的上下文。建议填写稳定业务区域，如“搜索区域”“表格”“创建弹窗”。">
                    <span class="mango-ui-element-field-help" aria-label="元素分类填写说明">
                      <icon-question-circle />
                    </span>
                  </a-tooltip>
                </span>
              </template>
              <a-input v-model="form.category" placeholder="如：搜索区域、表格、弹窗、半屏窗口" data-testid="qa-components-business-uielementeditpanel-input-如-搜索区域-表格-弹窗-半屏窗口" />
            </a-form-item>
          </div>
          <div class="mango-ui-element-identity-status">
            <a-spin v-if="identityCheck.loading" :size="scaleDensityPixels(16)" />
            <template v-if="mode === 'edit'">
              <a-tag color="blue" size="small">编辑</a-tag>
              <span>
                当前为编辑模式，将更新元素 #{{ form.id }}；修改名称或分类不会创建新元素
              </span>
              <span
                v-if="identityCheck.record?.id != null && String(identityCheck.record.id) !== String(form.id)"
                class="mango-ui-element-identity-warning"
              >
                当前页面存在同名同分类元素 #{{ identityCheck.record.id }}，保存后可能形成重复数据
              </span>
            </template>
            <template v-else-if="identityCheck.status === 'existing'">
              <a-tag color="orange" size="small">更新</a-tag>
              <span>
                当前页面已存在相同名称和分类的元素，将更新元素 #{{ identityCheck.record.id }}
              </span>
              <span v-if="identityCheck.matchCount > 1" class="mango-ui-element-identity-warning">
                共发现 {{ identityCheck.matchCount }} 条历史重复数据，优先更新当前或最新记录
              </span>
            </template>
            <template v-else-if="identityCheck.status === 'new'">
              <a-tag color="green" size="small">创建</a-tag>
              <span>当前页面不存在相同名称和分类的元素，将创建新元素</span>
            </template>
            <template v-else-if="identityCheck.status === 'error'">
              <a-tag color="red" size="small">校验失败</a-tag>
              <span data-feedback-kind="validation">{{ identityCheck.error }}</span>
            </template>
            <span v-else-if="identityCheck.status === 'checking'">正在校验页面元素…</span>
            <span v-else-if="identityCheck.status === 'pending'">等待校验名称和分类…</span>
            <span v-else>填写元素名称和元素分类后自动校验</span>
          </div>
        </section>

        <section class="mango-ui-element-edit-section">
          <div class="mango-ui-element-edit-section-head">
            <div class="mango-ui-element-edit-section-head__main">
              <h3>元素描述</h3>
              <span>两个字段均可选；没有定位表达式时，将组合基本信息和下方描述直接识别元素</span>
            </div>
            <a-button
              v-if="checkable && mode === 'edit' && form.id != null"
              size="small"
              :loading="checking"
              :disabled="checking"
              @click="emit('check', { ...form }, 'deep')" data-testid="qa-components-business-uielementeditpanel-button-深度检测"
            >
              在当前浏览器中识别
            </a-button>
          </div>
          <div class="mango-ui-element-description-fields">
            <a-form-item label="元素位置与周边文字">
              <a-textarea
                v-model="form.location_description"
                placeholder="例如：左侧字段选择菜单中，“默认字段”分组下的“收支类型”"
                :auto-size="{ minRows: 2, maxRows: 4 }"
                data-testid="qa-components-business-uielementeditpanel-textarea-元素位置"
              />
            </a-form-item>
            <a-form-item label="排除项">
              <a-textarea
                v-model="form.surrounding_text"
                placeholder="例如：排除右侧模板字段列表中的同名“收支类型”"
                :auto-size="{ minRows: 2, maxRows: 4 }"
                data-testid="qa-components-business-uielementeditpanel-textarea-排除项"
              />
            </a-form-item>
          </div>
          <div class="mango-ui-element-description-note">
            前者填写目标所在位置和周边可见文字，后者只填写不能选择的同名或相似元素；元素描述与定位表达式至少填写一种。
          </div>
          <div v-if="form.latest_runtime_time" class="mango-ui-element-recognition-summary">
            <a-tag color="arcoblue" size="small">最近识别</a-tag>
            <span>匹配 {{ form.latest_match_count ?? '-' }}</span>
            <span v-if="form.latest_element_text">文本：{{ form.latest_element_text }}</span>
            <span>{{ form.latest_runtime_time }}</span>
          </div>
        </section>

        <section class="mango-ui-element-edit-section mango-ui-element-locator-section">
          <div class="mango-ui-element-edit-section-head">
            <div class="mango-ui-element-edit-section-head__main">
              <h3>定位表达式</h3>
              <span>已有/本次生成 {{ configuredLocatorCount }}/3 组；第一组为主定位</span>
            </div>
          </div>
          <div class="mango-ui-element-locator-card">
            <div class="mango-ui-element-locator-card-title">第一组元素</div>
            <div class="mango-ui-element-locator-row">
              <a-form-item label="定位类型">
                <a-select
                  v-model="form.exp"
                  :options="enumStore.element_exp"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </a-form-item>
              <a-form-item label="定位表达式">
                <a-input v-model="form.loc" placeholder="请输入定位表达式" data-testid="qa-components-business-uielementeditpanel-input-请输入定位表达式" />
              </a-form-item>
              <a-form-item label="下标">
                <a-input v-model="form.sub" placeholder="从1开始" data-testid="qa-components-business-uielementeditpanel-input-从1开始" />
              </a-form-item>
            </div>
            <UiLocatorRuntimeMeta
              :data="locatorRuntimeGroup(1)"
              :fallback-match-count="form.latest_match_count"
              :fallback-text="form.latest_element_text"
              :runtime-time="form.latest_runtime_time"
            />
          </div>
          <div class="mango-ui-element-locator-card">
            <div class="mango-ui-element-locator-card-title">第二组元素</div>
            <div class="mango-ui-element-locator-row">
              <a-form-item label="定位类型">
                <a-select
                  v-model="form.exp2"
                  :options="enumStore.element_exp"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </a-form-item>
              <a-form-item label="定位表达式">
                <a-input v-model="form.loc2" placeholder="请输入第二组定位表达式" data-testid="qa-components-business-uielementeditpanel-input-请输入第二组定位表达式" />
              </a-form-item>
              <a-form-item label="下标">
                <a-input v-model="form.sub2" placeholder="从1开始" data-testid="qa-components-business-uielementeditpanel-input-从1开始-2" />
              </a-form-item>
            </div>
            <UiLocatorRuntimeMeta
              :data="locatorRuntimeGroup(2)"
              :runtime-time="form.latest_runtime_time"
            />
          </div>
          <div class="mango-ui-element-locator-card">
            <div class="mango-ui-element-locator-card-title">第三组元素</div>
            <div class="mango-ui-element-locator-row">
              <a-form-item label="定位类型">
                <a-select
                  v-model="form.exp3"
                  :options="enumStore.element_exp"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </a-form-item>
              <a-form-item label="定位表达式">
                <a-input v-model="form.loc3" placeholder="请输入第三组定位表达式" data-testid="qa-components-business-uielementeditpanel-input-请输入第三组定位表达式" />
              </a-form-item>
              <a-form-item label="下标">
                <a-input v-model="form.sub3" placeholder="从1开始" data-testid="qa-components-business-uielementeditpanel-input-从1开始-3" />
              </a-form-item>
            </div>
            <UiLocatorRuntimeMeta
              :data="locatorRuntimeGroup(3)"
              :runtime-time="form.latest_runtime_time"
            />
          </div>
        </section>

        <section class="mango-ui-element-edit-section">
          <div class="mango-ui-element-edit-section-head">
            <h3>预期事件与输入</h3>
            <span>选择该元素作为步骤对象时，自动带入推荐操作和默认入参</span>
          </div>
          <div class="mango-ui-element-edit-grid mango-ui-element-edit-grid-single">
            <a-form-item label="元素操作">
              <a-cascader
                v-model="form.expected_event.ope_key"
                :options="props.operationOptions"
                placeholder="请选择预期元素操作，非必填"
                allow-clear
                allow-search
                expand-trigger="hover"
                value-key="key"
                @change="onExpectedEventChange" data-testid="qa-components-business-uielementeditpanel-cascader-请选择预期元素操作-非必填"
              />
            </a-form-item>
          </div>
          <div
            v-if="expectedEventParams.length"
            class="mango-ui-element-expected-event-params"
          >
            <div class="mango-ui-element-expected-event-title">预期输入</div>
            <a-form-item
              v-for="item in expectedEventParams"
              :key="item.f"
              :label="item.n || item.f"
            >
              <a-textarea
                v-model="item.v"
                :placeholder="item.p"
                :auto-size="{ minRows: 2, maxRows: 4 }"
                allow-clear
              />
            </a-form-item>
          </div>
        </section>

        <section class="mango-ui-element-edit-section">
          <div class="mango-ui-element-edit-section-head">
            <h3>辅助配置</h3>
            <span>执行等待信息</span>
          </div>
          <div class="mango-ui-element-edit-grid mango-ui-element-edit-grid-single mango-ui-element-assist-row">
            <a-form-item label="等待时间">
              <a-input v-model="form.sleep" placeholder="秒" data-testid="qa-components-business-uielementeditpanel-input-秒" />
            </a-form-item>
          </div>
        </section>
      </a-form>
    </a-spin>
    <template #footer-buttons>
      <a-space class="mango-ui-element-edit-actions">
        <a-button @click="visible = false" data-testid="qa-components-business-uielementeditpanel-button-取消">取消</a-button>
        <a-button
          v-if="mode === 'create'"
          :loading="continuousSaving"
          @click="save(true)" data-testid="qa-components-business-uielementeditpanel-button-保存并继续"
        >
          保存并继续
        </a-button>
        <a-button type="primary" :loading="saving" @click="save(false)" data-testid="qa-components-business-uielementeditpanel-button-保存">
          保存
        </a-button>
      </a-space>
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import { readElementEditor, readElementEvent } from './ui-element-editor'
  import type { ElementEditorDraft, ElementEventParameter, ElementOperation } from './ui-element-editor'
  import { liveId, liveError, liveObject, readLiveResult } from './ui-live-workbench'
  import { Message } from '@arco-design/web-vue'
  import { IconQuestionCircle } from '@arco-design/web-vue/es/icon'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import UiLocatorRuntimeMeta from '@/components/business/UiLocatorRuntimeMeta.vue'
  import {
    getUiElement,
    getUiElementIdentity,
    postUiElement,
    putUiElement,
  } from '@/api/uitest/element'

  const props = withDefaults(defineProps<{
    operationOptions?: unknown[]
    checkable?: boolean
    checkLoadingKey?: string
    checkLoading?: boolean
    contextKey?: string | number
  }>(), {
    operationOptions: () => [],
    checkable: false,
    checkLoadingKey: '',
    checkLoading: false,
  })

  const emit = defineEmits<{
    (event: 'saved', record: unknown): void
    (event: 'check', record: ElementEditorDraft, checkMode: 'normal' | 'deep'): void
  }>()

  const enumStore = useEnum()
  const visible = ref(false)
  let disposed = false, windowVersion = 0, readSequence = 0
  watch(visible, value => { if (!value) { windowVersion++; clearIdentityCheckTimer(); resetIdentityCheck() } }, { flush: 'sync' })
  const scope = useLiveWorkbenchScope(() => props.contextKey, {
    invalidate() { visible.value = false; clearIdentityCheckTimer(); resetIdentityCheck() },
    resume() {},
  })
  const captureWindow = () => { const version = windowVersion, current = scope.capture(); return () => current() && !disposed && visible.value && version === windowVersion }
  const loading = ref(false)
  const readError = ref('')
  let readTargetId: string | number | null = null
  const saving = ref(false)
  const saveError = ref('')
  const continuousSaving = ref(false)
  const mode = ref<'create' | 'edit'>('create')
  const form: ElementEditorDraft = reactive(readElementEditor())
  const expectedEventParams = ref<ElementEventParameter[]>([])
  const identityCheck = reactive({
    status: 'idle' as 'idle' | 'pending' | 'checking' | 'existing' | 'new' | 'error',
    loading: false,
    key: '',
    record: null as ElementEditorDraft | null,
    matchCount: 0,
    error: '',
  })
  let identityCheckTimer: ReturnType<typeof setTimeout> | null = null
  let identityCheckVersion = 0
  let identityCheckTask: Promise<boolean> | null = null
  const title = computed(() => (mode.value === 'create' ? '新增元素' : '编辑元素'))
  const locatorGroups = () => [
    { label: '第一组', exp: form.exp, loc: form.loc },
    { label: '第二组', exp: form.exp2, loc: form.loc2 },
    { label: '第三组', exp: form.exp3, loc: form.loc3 },
  ]
  const hasLocatorType = (value: unknown) => value !== null && value !== undefined && value !== ''
  const hasLocatorExpression = (value: unknown) => Boolean(String(value || '').trim())
  const configuredLocatorCount = computed(() =>
    locatorGroups().filter((item) => hasLocatorType(item.exp) && hasLocatorExpression(item.loc)).length
  )
  const checking = computed(
    () => props.checkLoading || String(props.checkLoadingKey || '') === String(form.id ?? '')
  )

  function normalizeDescriptionFields(record: ElementEditorDraft) {
    let positive = String(record.location_description || '').trim()
    let exclusion = String(record.surrounding_text || '').trim()
    const marker = exclusion.match(/[，；。\n](?:排除|不是)/)
    if (marker?.index !== undefined) {
      const legacyPositive = exclusion.slice(0, marker.index).replace(/[，；。\s]+$/g, '')
      exclusion = exclusion.slice(marker.index + marker[0].length).replace(/^[，；。\s]+/g, '')
      if (legacyPositive && !positive.includes(legacyPositive)) {
        positive = [positive, legacyPositive].filter(Boolean).join('；')
      }
    }
    return { positive, exclusion }
  }

  function resetForm(input: unknown = {}) {
    const record = readElementEditor(input)
    windowVersion++
    readSequence++
    saveError.value = ''
    readError.value = ''
    loading.value = false
    const descriptions = normalizeDescriptionFields(record)
    const hasStructuredDescription = Boolean(
      descriptions.positive || descriptions.exclusion
    )
    Object.assign(form, {
      id: record.id,
      page: record.page,
      name: record.name ?? '',
      category: record.category ?? '未分类',
      exp: record.exp ?? null,
      loc: record.loc ?? '',
      sub: record.sub ?? '',
      exp2: record.exp2 ?? null,
      loc2: record.loc2 ?? '',
      sub2: record.sub2 ?? '',
      exp3: record.exp3 ?? null,
      loc3: record.loc3 ?? '',
      sub3: record.sub3 ?? '',
      sleep: record.sleep ?? '',
      is_iframe: record.is_iframe ?? 0,
      location_description: descriptions.positive || (
        hasStructuredDescription ? '' : record.prompt ?? ''
      ),
      surrounding_text: descriptions.exclusion,
      // 旧 prompt 仅作兼容；没有结构化描述时会迁移到正向识别线索。
      prompt: hasStructuredDescription ? record.prompt ?? '' : '',
      expected_event: readElementEvent(record.expected_event),
      latest_match_count: record.latest_match_count ?? null,
      latest_element_text: record.latest_element_text ?? '',
      latest_runtime_time: record.latest_runtime_time ?? '',
      latest_runtime_snapshot: record.latest_runtime_snapshot || {},
    })
    buildExpectedEventParams(form.expected_event.ope_key, form.expected_event.ope_value)
  }

  function normalizeNumber(value: unknown) {
    if (value === '' || value === undefined || value === null) return null
    return Number(value)
  }

  function identityKey() {
    const page = String(form.page ?? '').trim()
    const name = String(form.name || '').trim()
    const category = String(form.category || '').trim()
    return page && name && category ? `${page}\u0000${name}\u0000${category}` : ''
  }

  function clearIdentityCheckTimer() {
    if (!identityCheckTimer) return
    clearTimeout(identityCheckTimer)
    identityCheckTimer = null
  }

  function resetIdentityCheck(status: 'idle' | 'pending' = 'idle', key = '') {
    identityCheckVersion += 1
    identityCheck.status = status
    identityCheck.loading = false
    identityCheck.key = key
    identityCheck.record = null
    identityCheck.matchCount = 0
    identityCheck.error = ''
  }

  async function runIdentityCheck(force = false): Promise<boolean> {
    const key = identityKey()
    if (!visible.value || disposed || !key) {
      resetIdentityCheck()
      return false
    }
    if (!force && identityCheck.key === key && ['existing', 'new'].includes(identityCheck.status)) {
      return true
    }
    if (identityCheck.loading && identityCheck.key === key && identityCheckTask) {
      return identityCheckTask
    }
    const current = captureWindow()
    const pageId = liveId(form.page)
    if (pageId === null) return false
    const version = ++identityCheckVersion
    identityCheck.status = 'checking'
    identityCheck.loading = true
    identityCheck.key = key
    identityCheck.record = null
    identityCheck.matchCount = 0
    identityCheck.error = ''
    const task = (async () => {
      try {
        const res = await getUiElementIdentity({
          page_id: pageId,
          name: String(form.name || '').trim(),
          category: String(form.category || '').trim(),
          ...(form.id != null ? { current_id: form.id } : {}),
        })
        if (!current() || version !== identityCheckVersion || key !== identityKey()) return false
        identityCheck.record = res.data?.element ? readElementEditor(res.data.element) : null
        identityCheck.matchCount = Number(res.data?.match_count || 0)
        identityCheck.status = res.data?.exists ? 'existing' : 'new'
        return true
      } catch (error) {
        if (!current() || version !== identityCheckVersion) return false
        identityCheck.status = 'error'
        identityCheck.error = liveError(error, '元素名称和分类校验失败，请稍后重试')
        return false
      } finally {
        if (version === identityCheckVersion) identityCheck.loading = false
      }
    })()
    identityCheckTask = task
    return task
  }

  function scheduleIdentityCheck() {
    clearIdentityCheckTimer()
    if (!visible.value) {
      resetIdentityCheck()
      return
    }
    const key = identityKey()
    if (!key) {
      resetIdentityCheck()
      return
    }
    if (key === identityCheck.key && ['checking', 'existing', 'new'].includes(identityCheck.status)) {
      return
    }
    resetIdentityCheck('pending', key)
    identityCheckTimer = setTimeout(() => {
      identityCheckTimer = null
      void runIdentityCheck()
    }, 400)
  }

  watch(
    () => [visible.value, form.page, form.name, form.category],
    scheduleIdentityCheck,
    { flush: 'post' }
  )

  onBeforeUnmount(() => {
    disposed = true
    windowVersion++
    clearIdentityCheckTimer()
    identityCheckVersion += 1
  })

  function validate() {
    if (!form.name) {
      Message.error('请输入元素名称')
      return false
    }
    if (!String(form.category || '').trim()) {
      Message.error('请输入元素分类')
      return false
    }
    for (const locator of locatorGroups()) {
      if (hasLocatorType(locator.exp) !== hasLocatorExpression(locator.loc)) {
        Message.error(`请同时填写${locator.label}的定位类型和定位表达式`)
        return false
      }
    }
    const hasDescription = [
      form.location_description,
      form.surrounding_text,
      form.prompt,
    ].some((value) => String(value || '').trim())
    if (!configuredLocatorCount.value && !hasDescription) {
      Message.error('元素描述和定位表达式至少填写一项')
      return false
    }
    return true
  }

  function findOperationByValue(options: unknown[], value: string): ElementOperation | null {
    for (const valueItem of options || []) {
      const item = liveObject(valueItem)
      if (item.value === value) return item as unknown as ElementOperation
      const child = findOperationByValue(Array.isArray(item.children) ? item.children : [], value)
      if (child) return child
    }
    return null
  }

  function buildExpectedEventParams(opeKey: string, presetValues: ElementEventParameter[] = []) {
    const operation = findOperationByValue(props.operationOptions, opeKey)
    const presetMap = new Map((presetValues || []).map((item) => [item.f, item]))
    expectedEventParams.value = (operation?.parameter || [])
      .filter((item) => item?.d === true)
      .map((item) => {
        const preset = presetMap.get(item.f)
        return {
          ...item,
          v: preset && Object.prototype.hasOwnProperty.call(preset, 'v') ? preset.v : item.v,
        }
      })
  }

  function onExpectedEventChange(value: string) {
    if (!value) {
      form.expected_event = { ope_key: '', ope_value: [] }
      expectedEventParams.value = []
      return
    }
    form.expected_event = { ope_key: value, ope_value: [] }
    buildExpectedEventParams(value)
  }

  function buildPayload() {
    const {
      latest_match_count,
      latest_element_text,
      latest_runtime_time,
      latest_runtime_snapshot,
      ...editableForm
    } = form
    return {
      ...editableForm,
      name: String(form.name || '').trim(),
      sub: normalizeNumber(form.sub),
      sub2: normalizeNumber(form.sub2),
      sub3: normalizeNumber(form.sub3),
      sleep: normalizeNumber(form.sleep),
      category: String(form.category || '').trim(),
      prompt: String(form.prompt || '').trim() || null,
      location_description: String(form.location_description || '').trim() || null,
      surrounding_text: String(form.surrounding_text || '').trim() || null,
      exp: form.loc ? normalizeNumber(form.exp) : null,
      loc: String(form.loc || '').trim() || null,
      exp2: normalizeNumber(form.exp2),
      loc2: String(form.loc2 || '').trim() || null,
      exp3: normalizeNumber(form.exp3),
      loc3: String(form.loc3 || '').trim() || null,
      is_iframe: form.is_iframe ?? 0,
      expected_event: form.expected_event?.ope_key
        ? {
            ope_key: form.expected_event.ope_key,
            ope_value: expectedEventParams.value.map((item) => ({
              f: item.f,
              n: item.n,
              p: item.p,
              d: item.d,
              v: item.v,
            })),
          }
        : {},
    }
  }

  function locatorRuntimeGroup(group: number) {
    const groups = form.latest_runtime_snapshot?.locator_groups
    if (!Array.isArray(groups)) return null
    return groups.find((item, index) => Number(item?.group || index + 1) === group) || null
  }

  function applyRuntimeResult(input: unknown) {
    const result = readLiveResult(input)
    if (!visible.value || disposed || liveId(form.id) === null || String(result.element_id ?? '') !== String(form.id ?? '')) return
    const groups = Array.isArray(result.locator_groups) ? result.locator_groups : []
    const selectedElement = result.selected_result?.elements?.[0] || result.elements?.[0] || {}
    form.latest_match_count = selectedElement.ele_quantity ?? groups[0]?.count ?? null
    form.latest_element_text = selectedElement.element_text || groups[0]?.element_text || ''
    form.latest_runtime_time = result.checked_time || new Date().toLocaleString()
    form.latest_runtime_snapshot = {
      ...(form.latest_runtime_snapshot || {}),
      ...result,
      locator_groups: groups,
    }
  }

  function openCreate(pageId: string | number, category = '未分类', defaults: unknown = {}) {
    mode.value = 'create'
    resetForm({ page: pageId, is_iframe: 0, category, ...cloneLosslessJson(liveObject(defaults)) })
    visible.value = true
  }

  async function openEdit(record: unknown) {
    mode.value = 'edit'
    resetForm(record)
    visible.value = true
  }

  async function openEditById(id: string | number) {
    mode.value = 'edit'
    resetForm({ id })
    readTargetId = id
    visible.value = true
    const current = captureWindow()
    const sequence = ++readSequence
    loading.value = true
    try {
      const res = await getUiElement({ id, page: 1, pageSize: 1 })
      if (!current() || sequence !== readSequence) return
      const record = (res.data || [])[0]
      if (!record || liveId(record.id) === null || String(record.id) !== String(id)) throw Error('未找到对应元素数据')
      resetForm(record)
    } catch (error) {
      if (current() && sequence === readSequence) (reportLoadError(error, "元素数据获取失败，请重试", false), readError.value = liveError(error, '元素数据获取失败，请重试'))
    } finally {
      if (sequence === readSequence) loading.value = false
    }
  }
  function retryRead() { if (readTargetId !== null && !loading.value) void openEditById(readTargetId) }

  async function save(continuous: boolean) {
    if (saving.value || continuousSaving.value || loading.value || readError.value || disposed || !visible.value) return
    if (!validate()) return
    const loadingRef = continuous ? continuousSaving : saving
    if (loadingRef.value) return
    loadingRef.value = true
    const current = captureWindow()
    saveError.value = ''
    try {
      clearIdentityCheckTimer()
      if (mode.value === 'create' && !(await runIdentityCheck(true))) {
        if (!current()) return
        Message.error('请等待元素名称和分类校验成功后再保存')
        return
      }
      if (!current()) return
      const payload = cloneLosslessJson(buildPayload())
      const targetId = mode.value === 'edit' ? form.id : identityCheck.record?.id
      if (mode.value === 'edit' && (targetId == null || targetId === '')) {
        Message.error('当前编辑元素缺少ID，请关闭后重新打开')
        return
      }
      const updating = targetId != null && targetId !== ''
      const submitted = updating ? { ...payload, id: targetId } : payload
      const res = updating ? await putUiElement(submitted) : await postUiElement(submitted)
      if (!current()) return
      Message.success(res.msg)
      emit('saved', res.data || submitted)
      if (mode.value === 'create' && continuous) {
        resetForm({ page: form.page, is_iframe: 0 })
      } else {
        visible.value = false
      }
    } catch (error) {
      if (current()) saveError.value = requestFailureMessage(error, liveError(error, '元素保存失败，请重试'))
    } finally {
      loadingRef.value = false
    }
  }

  defineExpose({
    openCreate,
    openEdit,
    openEditById,
    applyRuntimeResult,
  })
</script>

<style scoped>
  .mango-ui-element-edit-spin {
    display: block;
  }

  .mango-ui-element-edit-form {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    padding: 0;
  }

  .mango-ui-element-edit-form :deep(.arco-form-item) {
    margin-bottom: 0;
  }

  .mango-ui-element-edit-form :deep(.arco-form-item-label-col) {
    flex: 0 0 86px;
    max-width: 86px;
    min-width: 86px;
  }

  .mango-ui-element-edit-form :deep(.arco-form-item-label) {
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 32px;
    white-space: nowrap;
  }

  .mango-ui-element-edit-form :deep(.arco-form-item-wrapper-col) {
    min-width: 0;
    flex: 1;
  }

  .mango-ui-element-edit-section {
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
    padding: var(--m-card-padding);
  }

  .mango-ui-element-edit-section-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .mango-ui-element-edit-section-head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
  }

  .mango-ui-element-edit-section-head__main {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 3px;
  }

  .mango-ui-element-edit-section-head span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ui-element-edit-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 12px;
  }

  .mango-ui-element-edit-grid-single {
    grid-template-columns: minmax(0, 1fr);
  }

  .mango-ui-element-field-label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .mango-ui-element-field-help {
    display: inline-flex;
    align-items: center;
    color: var(--m-muted);
    cursor: help;
    line-height: 1;
  }

  .mango-ui-element-description-fields {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }

  .mango-ui-element-description-fields :deep(.arco-form-item-label-col) {
    flex-basis: 126px;
    max-width: 126px;
    min-width: 126px;
  }

  .mango-ui-element-description-note {
    margin-top: 8px;
    padding-left: 126px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-ui-element-identity-status {
    display: flex;
    min-height: 24px;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-ui-element-identity-warning {
    color: var(--m-warning);
  }

  .mango-ui-element-assist-row {
    margin-bottom: 12px;
  }

  .mango-ui-element-expected-event-params {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
    margin-top: 10px;
  }

  .mango-ui-element-expected-event-title {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .mango-ui-element-locator-card {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface-soft);
    padding: 12px;
  }

  .mango-ui-element-recognition-summary {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ui-element-recognition-summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
  }

  .mango-ui-element-locator-card + .mango-ui-element-locator-card {
    margin-top: 10px;
  }

  .mango-ui-element-locator-card-title {
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--m-border);
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .mango-ui-element-locator-row {
    display: grid;
    grid-template-columns: 210px minmax(0, 1fr) 170px;
    gap: 10px 12px;
  }

  .mango-ui-element-edit-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    width: 100%;
  }

  @media (max-width: 720px) {
    .mango-ui-element-edit-grid,
    .mango-ui-element-locator-row {
      grid-template-columns: 1fr;
      gap: 10px;
    }

    .mango-ui-element-edit-form :deep(.arco-form-item-label-col) {
      flex-basis: 78px;
      max-width: 78px;
      min-width: 78px;
    }

    .mango-ui-element-description-note {
      padding-left: 116px;
    }

    .mango-ui-element-description-fields :deep(.arco-form-item-label-col) {
      flex-basis: 116px;
      max-width: 116px;
      min-width: 116px;
    }
  }
</style>
