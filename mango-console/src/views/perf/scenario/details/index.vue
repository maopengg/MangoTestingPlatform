<template>
  <TableBody plain class="mango-detail-workbench-page mango-perf-page">
    <template #header>
      <TableHeader :title="`性能场景 / ${id || '-'} / ${form.name || '-'}`">
        <template #header-extra>
          <a-space>
            <a-button  status="success" size="small" :loading="executing" @click="openExecuteDialog"
              >执行场景</a-button
            >
            <a-button  size="small" :loading="scriptPreviewLoading" @click="openScriptPreview">预览 k6 脚本</a-button>
            <a-button size="small" :loading="validating" @click="validateConfig">校验配置</a-button>
            <a-button  type="primary" size="small" :loading="saving" @click="save">保存</a-button>
            <a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button>
          </a-space>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <a-alert data-feedback-kind="validation" v-if="!id" type="error" class="mango-perf-read-error">场景 ID 无效，请返回列表重新进入。</a-alert>
      
      <a-alert v-if="refreshBeforeWrite" type="warning" class="mango-perf-read-error">
        保存期间离开了当前页面，请重新加载以确认保存结果。
        <template #action><a-button size="small" :loading="loading" :disabled="saving" @click="retryDetails">重新加载</a-button></template>
      </a-alert>
      <a-spin :loading="loading" class="mango-perf-detail-spin">
        <div class="mango-perf-config-workbench">
          <div class="mango-perf-editor-grid">
            <main class="mango-perf-flow-column">
              <section class="mango-section-card mango-perf-flow-section">
                <div class="mango-section-title mango-perf-section-heading">
                  <div
                    ><span>Case 编排</span
                    ><small>一次 iteration 完整执行一次已发布 Case</small></div
                  >
                  <a-button size="small" :disabled="!sourceCase?.case_id" @click="caseDetailVisible = true"
                    >查看用例详情</a-button
                  >
                </div>
                
                <a-form layout="horizontal" :model="form" auto-label-width>
                  <a-form-item label="已发布 Case" required>
                    <a-select
                      v-model="form.source_case_release_id"
                      :options="caseOptions"
                      :loading="!loading && caseLoading"
                      allow-search
                      placeholder="请选择当前产品下已发布的API自动化 Case"
                      @change="selectCase"
                    />
                  </a-form-item>
                </a-form>
                <template v-if="sourceCase">
                  <a-alert data-feedback-kind="validation" v-if="!sourceCase.compatible" type="error"
                    >当前 Case 暂不兼容性能模式：{{
                      sourceCase.incompatible_reasons?.join('；')
                    }}</a-alert
                  >
                  <div v-else class="mango-perf-case-meta">
                    <a-tag size="small" color="green">已发布 {{ sourceCase.version_label }}</a-tag>
                    <span>{{ sourceCase.module_full_path }}</span
                    ><span>修订 #{{ sourceCase.revision_no }}</span>
                  </div>
                  <div class="mango-perf-step-list">
                    <article
                      v-for="(item, index) in sourceCase.steps || []"
                      :key="item.key"
                      class="mango-soft-panel mango-perf-step-item"
                    >
                      <div class="mango-perf-step-index">{{ index + 1 }}</div>
                      <div class="mango-perf-step-content">
                        <strong>{{ item.name }}</strong>
                        <div class="mango-perf-meta-row"
                          ><span>API #{{ item.api_info_id }}</span
                          ><span>提取 {{ item.extractor_count }}</span
                          ><span>检查 {{ item.check_count }}</span></div
                        >
                      </div>
                      <a-tag size="small">只读</a-tag>
                    </article>
                  </div>
                </template>
                <div v-else class="mango-perf-empty"
                  ><strong>请选择一个已发布 Case</strong
                  ><span>请求、变量、提取和断言均复用 Case 发布快照</span></div
                >
              </section>
            </main>

            <aside class="mango-perf-settings-column">
              <section class="mango-section-card mango-perf-settings-panel">
                <div class="mango-section-title mango-perf-section-heading"
                  ><div><span>场景设置</span><small>基本信息与执行器策略</small></div></div
                >
                <a-form
                  :model="form"
                  layout="horizontal"
                  :label-col-props="{ span: 7 }"
                  :wrapper-col-props="{ span: 17 }"
                >
                  <a-form-item label="场景名称" required
                    ><a-input v-model="form.name" :max-length="128"
                  /></a-form-item>
                  <a-form-item label="执行引擎"
                    ><a-select v-model="form.engine" :options="engineOptions" disabled
                  /></a-form-item>
                  <a-form-item label="执行器数"
                    ><a-input-number v-model="form.default_executor_count" :min="1" :max="100"
                  /></a-form-item>
                  <a-form-item label="失败策略"
                    ><a-select v-model="form.node_failure_policy" :options="failurePolicyOptions"
                  /></a-form-item>
                  <a-form-item label="最小就绪节点"
                    ><a-input-number
                      v-model="form.min_ready_nodes"
                      :min="1"
                      :max="form.default_executor_count || 100"
                      :disabled="form.node_failure_policy === 'strict'"
                  /></a-form-item>
                </a-form>
              </section>

              <section class="mango-section-card mango-perf-side-section">
                <div class="mango-section-title mango-perf-section-heading">
                  <div><span>负载配置</span><small>一次运行只使用这一套负载配置</small></div>
                  <a-button  size="mini" type="text" @click="openLoadConfig">编辑</a-button>
                </div>
                <div v-if="hasLoadConfig" class="mango-soft-panel mango-perf-load-summary">
                  <div class="mango-perf-load-name">
                    <span>压测方案</span>
                    <strong>{{ loadProfileLabel(loadConfig.profile) }}</strong>
                  </div>
                  <div class="mango-perf-load-metric">
                    <span>目标负载</span>
                    <strong>{{ formatLoadTarget(loadConfig) }}</strong>
                    <small>{{ formatLoadUnit(loadConfig) }}</small>
                  </div>
                  <div class="mango-perf-load-metric">
                    <span>{{ loadConfig.profile === 'fixed_iterations' ? '截止时间' : '持续时间' }}</span>
                    <strong>{{ loadConfig.duration_seconds || 0 }}</strong>
                    <small>秒</small>
                  </div>
                  <div class="mango-perf-load-metric">
                    <span>{{ loadConfig.profile === 'fixed_iterations' ? 'Case 执行次数' : '配置名称' }}</span>
                    <strong>{{ loadConfig.profile === 'fixed_iterations' ? loadConfig.total_iterations : loadConfig.name }}</strong>
                  </div>
                </div>
                <div v-else class="mango-perf-empty"
                  ><strong>尚未配置负载</strong><span>请设置持续时间和目标负载</span></div
                >
              </section>

              <section class="mango-section-card mango-perf-side-section">
                <div class="mango-section-title mango-perf-section-heading">
                  <div><span>性能目标</span><small>三个客户端指标 AND 判定</small></div>
                  <a-select
                    v-model="performanceGoalTemplate"
                    class="mango-perf-goal-template-select"
                    size="mini"
                    :options="performanceGoalTemplateOptions"
                    @change="applyPerformanceGoalTemplate"
                  />
                </div>
                <p class="mango-perf-goal-description">{{ performanceGoalDescription }}</p>
                <div class="mango-perf-goal-form">
                  <label class="mango-perf-goal-row"
                    ><span><strong>P95 响应时间</strong><small>95% 请求耗时上限</small></span
                    ><a-input-number
                      v-model="performanceGoal.p95_ms"
                      :min="1"
                      :precision="0"
                      @change="markPerformanceGoalCustom"
                      ><template #suffix>ms</template></a-input-number
                    ></label
                  >
                  <label class="mango-perf-goal-row"
                    ><span><strong>错误率</strong><small>失败请求比例上限</small></span
                    ><a-input-number
                      v-model="performanceGoal.error_rate_percent"
                      :min="0"
                      :max="100"
                      :precision="2"
                      @change="markPerformanceGoalCustom"
                      ><template #suffix>%</template></a-input-number
                    ></label
                  >
                  <label class="mango-perf-goal-row"
                    ><span><strong>负载达成率</strong><small>实际负载最低比例</small></span
                    ><a-input-number
                      v-model="performanceGoal.load_achievement_rate_percent"
                      :min="0"
                      :max="100"
                      :precision="2"
                      @change="markPerformanceGoalCustom"
                      ><template #suffix>%</template></a-input-number
                    ></label
                  >
                </div>
              </section>
            </aside>
          </div>
        </div>
      </a-spin>
    </template>
  </TableBody>

  <LoadConfigurationDialog
    ref="loadDialogRef"
    :context-key="String(executionContextVersion)"
    :context-version="executionContextVersion"
    :is-context-current="isExecutionContextCurrent"
    :executor-count="Number(form.default_executor_count || 1)"
    @confirm="commitLoadConfig"
  />

  <ScenarioExecuteDialog
    ref="executeDialogRef"
    :scenario-id="id"
    :context-version="executionContextVersion"
    :executor-count="Number(form.default_executor_count || 1)"
    :is-context-current="isExecutionContextCurrent"
    :save-configuration="saveExecutionConfiguration"
    @busy-change="executing = $event"
    @executed="onScenarioExecuted"
  />

  <BaseSidePanel
    :visible="scriptPreviewVisible"
    :title="`k6 脚本预览 / 场景版本 ${scriptPreview?.scenario_version || '-'}`"
    width="80vw"
    :show-footer="false"
    @update:visible="onScriptPreviewVisibilityChange"
    @cancel="closeScriptPreview"
  >
    <template #header-actions>
      <a-button v-if="scriptPreview" size="mini" :loading="scriptPreviewCopying" :disabled="scriptPreviewLoading" @click="copyScriptPreview">复制当前内容</a-button>
    </template>
    <MangoPanelSpin :loading="scriptPreviewLoading" class="mango-perf-script-preview">
      
      <template v-if="scriptPreview">
        <a-alert type="info" class="mango-perf-script-preview__notice">
          预览基于已保存的场景配置。执行器运行同一份脚本模板，场景快照通过环境变量注入；测试环境、分片、运行号和密钥在执行时才填入。快照按敏感字段规则脱敏，仍请勿对外分享。
        </a-alert>
        <div class="mango-perf-script-preview__meta" :title="scriptPreview.snapshot_hash">快照 SHA-256：{{ scriptPreview.snapshot_hash }}</div>
        <a-tabs v-model:active-key="scriptPreviewTab" class="mango-perf-script-preview__tabs">
          <a-tab-pane key="script" title="k6 脚本">
            <div class="mango-perf-script-preview__code">
              <CodeEditor :model-value="scriptPreview.script" language="javascript" readonly />
            </div>
          </a-tab-pane>
          <a-tab-pane key="snapshot" title="场景快照（脱敏）">
            <div class="mango-perf-script-preview__code">
              <CodeEditor :model-value="scriptPreview.snapshot" language="json" readonly />
            </div>
          </a-tab-pane>
        </a-tabs>
      </template>
    </MangoPanelSpin>
  </BaseSidePanel>

  <BaseSidePanel
    :visible="caseDetailVisible"
    :title="`API 用例详情 / ${sourceCase?.name || ''}`"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="caseDetailVisible = $event"
    @cancel="caseDetailVisible = false"
  >
    <ApiCaseDetails
      v-if="caseDetailVisible && sourceCase?.case_id"
      :key="sourceCase.case_id"
      embedded
      :case-id="sourceCase.case_id"
      :project-product-id="form.project_product"
      @close="caseDetailVisible = false"
    />
  </BaseSidePanel>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { Message } from '@arco-design/web-vue'
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import LoadConfigurationDialog from './components/LoadConfigurationDialog.vue'
  import ScenarioExecuteDialog from './components/ScenarioExecuteDialog.vue'
  import { useScenarioScriptPreview } from './composables/useScenarioScriptPreview'
  import useUserStore from '@/store/modules/user'
  import { readScenarioConfiguration, readSourceCaseOptions, readSavedScenarioVersion, readScenarioValidation } from './records'
  import ApiCaseDetails from '@/views/apitest/case/details/index.vue'
  import {
    getPerfScenario,
    getPerfScenarioSourceCases,
    savePerfScenarioConfiguration,
    validatePerfScenario,
  } from '@/api/perf'
  import { engineOptions, loadProfileOptions } from '../config'
  import {
    createDefaultLoadConfiguration,
    createDefaultPerformanceGoal,
    createScenarioForm,
    failurePolicyOptions,
    performanceGoalTemplateOptions,
  } from './config'
  import {
    isRecommendedPerformanceGoal,
    performanceGoalToPayload,
    performanceGoalValidationMessage,
  } from './performance-goal'
  import type { LoadConfiguration, LoadConfigurationChange, PerformanceGoalDraft, PerformanceGoalTemplateKey, ScenarioConfigurationRecord, ScenarioForm, SourceCaseRelease } from './types'

  const route = useRoute()
  const router = useRouter()
  function scenarioId(value: unknown): string {
    return typeof value === 'string' && /^\d+$/.test(value) && Number.isSafeInteger(Number(value)) && Number(value) > 0
      ? String(Number(value)) : ''
  }
  const id = ref(scenarioId(route.query.id))
  watch(() => route.path === '/perf/scenario/details' ? scenarioId(route.query.id) : null, value => {
    if (value !== null) id.value = value
  }, { flush: 'sync' })
  const user = useUserStore()
  const executionContextVersion = ref(0)
  let active = true, mounted = false, disposed = false
  function isExecutionContextCurrent(version: number): boolean {
    return !disposed && active && !!id.value && version === executionContextVersion.value &&
      route.path === '/perf/scenario/details' && (typeof document === 'undefined' || document.visibilityState !== 'hidden')
  }
  function captureContext() {
    const version = executionContextVersion.value, scenarioId = id.value
    return isExecutionContextCurrent(version) ? {
      id: scenarioId, version,
      isCurrent: () => id.value === scenarioId && isExecutionContextCurrent(version),
    } : null
  }
  async function saveExecutionConfiguration(isCurrent: () => boolean): Promise<boolean> {
    if (!isCurrent()) return false
    const saved = await save()
    return saved && isCurrent()
  }
  function onScenarioExecuted(runId: number, version: number): void {
    if (isExecutionContextCurrent(version)) router.push({ path: '/perf/run/details', query: { id: runId } })
  }
  const loading = ref(false)
  const detailError = ref(false)
  const saving = ref(false)
  const validating = ref(false)
  const refreshBeforeWrite = ref(false)
  const executing = ref(false)
  const caseLoading = ref(false)
  const caseError = ref(false)
  const form: ScenarioForm = reactive(createScenarioForm())
  const scenarioRecord = ref<ScenarioConfigurationRecord | null>(null)
  const loadConfig: LoadConfiguration = reactive({ ...createDefaultLoadConfiguration(), duration_seconds: 0 })
  const sourceCase = ref<SourceCaseRelease | null>(null)
  const caseDetailVisible = ref(false)
  const {
    visible: scriptPreviewVisible, loading: scriptPreviewLoading, copying: scriptPreviewCopying,
    error: scriptPreviewError, activeTab: scriptPreviewTab, preview: scriptPreview,
    open: openScriptPreview, close: closeScriptPreview, reload: reloadScriptPreview,
    copy: copyScriptPreview, onVisibleChange: onScriptPreviewVisibilityChange,
  } = useScenarioScriptPreview({
    scenarioId: () => id.value,
    contextVersion: () => executionContextVersion.value,
    isContextCurrent: isExecutionContextCurrent,
  })
  const caseItems = ref<SourceCaseRelease[]>([])
  const performanceGoal: PerformanceGoalDraft = reactive(createDefaultPerformanceGoal())
  const performanceGoalTemplate = ref<PerformanceGoalTemplateKey>('recommended')
  const loadDialogRef = ref<InstanceType<typeof LoadConfigurationDialog> | null>(null)
  const executeDialogRef = ref<InstanceType<typeof ScenarioExecuteDialog> | null>(null)
  let detailReadVersion = 0
  let caseReadVersion = 0
  let pendingSaveVersion: number | null = null
  let needsDetailRead = true, needsCaseRead = true

  function invalidateContext(reset: boolean): void {
    const previousVersion = executionContextVersion.value
    executionContextVersion.value++
    detailReadVersion++
    caseReadVersion++
    if (loading.value) needsDetailRead = true
    if (caseLoading.value) needsCaseRead = true
    loading.value = false
    caseLoading.value = false
    caseDetailVisible.value = false
    loadDialogRef.value?.close()
    executeDialogRef.value?.close()
    if (reset) {
      Object.assign(form, createScenarioForm())
      Object.assign(loadConfig, createDefaultLoadConfiguration(), { duration_seconds: 0 })
      Object.assign(performanceGoal, createDefaultPerformanceGoal())
      performanceGoalTemplate.value = 'recommended'
      scenarioRecord.value = null
      sourceCase.value = null
      caseItems.value = []
      detailError.value = false
      caseError.value = false
      refreshBeforeWrite.value = false
      needsDetailRead = true
      needsCaseRead = true
    } else if (saving.value && pendingSaveVersion === previousVersion) refreshBeforeWrite.value = true
  }
  function resumeReads(): void {
    if (!mounted || !captureContext() || refreshBeforeWrite.value) return
    if (needsDetailRead) {
      if (!loading.value) retryDetails()
      return
    }
    if (needsCaseRead && !caseLoading.value) retryCaseOptions()
  }
  watch(() => [id.value, user.userId, user.roleId, user.token, user.selected_environment], () => {
    invalidateContext(true)
    void Promise.resolve().then(resumeReads)
  }, { flush: 'sync' })
  watch(() => route.path, () => {
    invalidateContext(false)
    void Promise.resolve().then(resumeReads)
  }, { flush: 'sync' })
  watch(() => form.source_case_release_id, () => { caseDetailVisible.value = false }, { flush: 'sync' })

  const caseOptions = computed(() =>
    caseItems.value.map((item) => ({
      label: item.title,
      value: item.release_id,
      disabled: item.disabled,
    }))
  )
  const hasLoadConfig = computed(() => Number(loadConfig.duration_seconds || 0) > 0)
  function loadProfileLabel(profile: string) {
    return loadProfileOptions.find((item) => item.value === profile)?.label.split(' · ')[0] || '固定并发'
  }
  const performanceGoalDescription = computed(() =>
    performanceGoalTemplate.value === 'recommended'
      ? '系统推荐模板：三个客户端指标必须同时达标；仅用于结果判定，不会自动中止执行。'
      : '自定义目标：三个客户端指标按 AND 关系判定；不会自动中止执行。'
  )
  async function loadCases() {
    const context = captureContext()
    if (!context) return
    const request = ++caseReadVersion
    const detail = detailReadVersion
    const isCurrent = () => context.isCurrent() && request === caseReadVersion && detail === detailReadVersion
    needsCaseRead = true
    caseLoading.value = true
    caseError.value = false
    try {
      const response = await getPerfScenarioSourceCases(context.id)
      if (!isCurrent()) return
      const items = readSourceCaseOptions(response), pinned = sourceCase.value
      if (pinned && !items.some(item => item.release_id === pinned.release_id)) items.unshift(pinned)
      caseItems.value = items
      needsCaseRead = false
    } catch (error) {
      if (!isCurrent()) return
      void (reportLoadError(error, "加载失败，请重试", false), caseError.value = true)
      throw error
    } finally {
      if (isCurrent()) caseLoading.value = false
    }
  }
  async function load() {
    const context = captureContext()
    if (!context || (refreshBeforeWrite.value && saving.value)) return
    const request = ++detailReadVersion
    const isCurrent = () => context.isCurrent() && request === detailReadVersion
    needsDetailRead = true
    ++caseReadVersion
    caseLoading.value = false
    caseError.value = false
    loading.value = true
    detailError.value = false
    try {
      const response = await getPerfScenario(context.id)
      if (!isCurrent()) return
      const record = readScenarioConfiguration(response, context.id)
      scenarioRecord.value = record
      Object.assign(form, record.form)
      Object.assign(loadConfig, record.load)
      sourceCase.value = record.source
      Object.assign(performanceGoal, record.goal)
      performanceGoalTemplate.value = record.goalTemplate
      needsDetailRead = false
      refreshBeforeWrite.value = false
    } catch (error) {
      if (!isCurrent()) return
      void (reportLoadError(error, "加载失败，请重试", false), detailError.value = true)
      throw error
    } finally {
      if (isCurrent()) loading.value = false
    }
    await loadCases()
  }
  function retryDetails(): void { void load().catch(() => {}) }
  function retryCaseOptions(): void { void loadCases().catch(() => {}) }
  function selectCase(value: unknown) {
    sourceCase.value = caseItems.value.find((item) => item.release_id === Number(value)) || null
  }
  function formatLoadTarget(item: LoadConfiguration) {
    return form.load_type === 'concurrency' ? item.target_users || 0 : item.target_rate || 0
  }
  function formatLoadUnit(item: LoadConfiguration) {
    return form.load_type === 'concurrency'
      ? '并发用户'
      : item.rate_time_unit === 'minute'
      ? 'Case 启动/分钟'
      : 'Case 启动/秒'
  }
  async function openLoadConfig() {
    if (!captureContext() || loading.value) return
    await loadDialogRef.value?.open(hasLoadConfig.value ? loadConfig : undefined, form.load_type)
  }
  function commitLoadConfig(change: LoadConfigurationChange) {
    if (!captureContext()) return
    form.load_type = change.loadType
    Object.assign(loadConfig, change.configuration)
  }
  function applyPerformanceGoalTemplate(value: unknown) {
    if (value !== 'recommended' && value !== 'custom') return
    performanceGoalTemplate.value = value
    if (value === 'recommended') Object.assign(performanceGoal, createDefaultPerformanceGoal())
  }
  function markPerformanceGoalCustom() {
    performanceGoalTemplate.value = isRecommendedPerformanceGoal(performanceGoal)
      ? 'recommended'
      : 'custom'
  }
  function validateLocal() {
    if (!form.name?.trim()) return Message.warning('请输入场景名称'), false
    if (!sourceCase.value || !form.source_case_release_id)
      return Message.warning('请选择已发布的API自动化 Case'), false
    if (!sourceCase.value.compatible)
      return Message.warning('当前 Case 不兼容性能模式，请更换 Case'), false
    if (!hasLoadConfig.value) return Message.warning('请配置负载'), false
    if (Number(loadConfig.user_wait_min_ms || 0) > Number(loadConfig.user_wait_max_ms || 0))
      return Message.warning('最大迭代等待不能小于最小值'), false
    const goalError = performanceGoalValidationMessage(performanceGoal)
    if (goalError) return Message.warning(goalError), false
    return true
  }
  async function save() {
    const context = captureContext()
    if (!context || saving.value || loading.value || refreshBeforeWrite.value || form.version === null) return false
    if (!validateLocal()) return false
    pendingSaveVersion = context.version
    saving.value = true
    try {
      const version = form.version
      const response = await savePerfScenarioConfiguration(context.id, {
        version,
        source_case_release_id: form.source_case_release_id,
        base: {
          name: form.name,
          default_executor_count: form.default_executor_count,
          node_failure_policy: form.node_failure_policy,
          min_ready_nodes: form.min_ready_nodes ?? null,
        },
        load_config: { ...loadConfig },
        performance_goal: performanceGoalToPayload(performanceGoal, performanceGoalTemplate.value),
      })
      if (!context.isCurrent()) return false
      form.version = readSavedScenarioVersion(response, context.id, version)
      Message.success('配置已保存')
      return true
    } catch (error) {
      if (!context.isCurrent()) return false
      throw error
    } finally {
      saving.value = false
      pendingSaveVersion = null
    }
  }
  async function validateConfig() {
    const context = captureContext()
    if (!context || validating.value) return
    validating.value = true
    try {
      if (!(await save())) return
      if (!context.isCurrent()) return
      const response = await validatePerfScenario(context.id)
      if (!context.isCurrent()) return
      const result = readScenarioValidation(response)
      Message.success(
        `校验通过：完整 Case 共 ${result.step_count} 个步骤，预计 ${result.duration_seconds} 秒`
      )
    } catch (error) {
      if (context.isCurrent()) throw error
    } finally {
      validating.value = false
    }
  }
  async function openExecuteDialog() {
    if (loading.value || refreshBeforeWrite.value || !isExecutionContextCurrent(executionContextVersion.value) || !validateLocal()) return
    await executeDialogRef.value?.open()
  }
  function visibilityChanged(): void {
    if (document.visibilityState === 'hidden') invalidateContext(false)
    else resumeReads()
  }
  onMounted(async () => {
    mounted = true
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', visibilityChanged)
    const context = captureContext()
    if (!context) return
    try { await load() } catch { return }
    if (context.isCurrent() && String(route.query.execute || '') === '1') await openExecuteDialog()
  })
  onDeactivated(() => { active = false; invalidateContext(false) })
  onActivated(() => { active = true; resumeReads() })
  onBeforeUnmount(() => {
    disposed = true
    invalidateContext(false)
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', visibilityChanged)
  })
</script>

<style scoped lang="less">
  .mango-perf-read-error {
    margin-bottom: var(--m-page-gap);
  }
  .mango-perf-script-preview {
    display: block;
    min-height: 220px;
    padding: 0;
  }
  .mango-perf-script-preview__notice {
    margin-bottom: 12px;
  }
  .mango-perf-script-preview__meta {
    overflow: hidden;
    color: var(--m-muted);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-perf-script-preview__code {
    height: calc(100vh - 260px);
    min-height: 240px;
    overflow: hidden;
  }
  .mango-perf-script-preview__code :deep(.cm-editor) {
    height: 100%;
  }
  .mango-perf-detail-spin {
    display: block;
  }
  .mango-perf-config-workbench,
  .mango-perf-flow-column,
  .mango-perf-settings-column {
    display: grid;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-perf-config-workbench {
    width: 100%;
    padding-bottom: var(--m-page-gap);
  }
  .mango-perf-editor-grid {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(460px, 1fr);
    align-items: start;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-perf-flow-column > .mango-section-card,
  .mango-perf-settings-column > .mango-section-card {
    margin-top: 0;
    padding: var(--m-card-padding);
  }
  .mango-perf-section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .mango-perf-section-heading > div {
    display: flex;
    align-items: baseline;
    gap: 8px;
    min-width: 0;
  }
  .mango-perf-section-heading > div > span {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
  }
  .mango-perf-section-heading small,
  .mango-perf-goal-description {
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 400;
  }
  .mango-perf-case-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    align-items: center;
    margin: 10px 0;
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-step-list {
    display: grid;
    gap: 6px;
    margin-top: 10px;
  }
  .mango-perf-step-item {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr) auto;
    align-items: center;
    gap: 10px;
    padding: 11px 12px;
    border-color: transparent;
  }
  .mango-perf-step-index {
    display: flex;
    width: 28px;
    height: 28px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: var(--m-primary-soft);
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 700;
  }
  .mango-perf-step-content {
    min-width: 0;
  }
  .mango-perf-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-empty {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-empty {
    display: grid;
    min-height: 76px;
    place-content: center;
    gap: 5px;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-lg);
    text-align: center;
  }
  .mango-perf-empty strong {
    color: var(--m-text-2);
  }
  .mango-perf-load-summary {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 0;
    overflow: hidden;
  }
  .mango-perf-load-name,
  .mango-perf-load-metric {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    align-content: center;
    gap: 4px 6px;
    min-width: 0;
    min-height: 68px;
    padding: 10px 12px;
  }
  .mango-perf-load-metric {
    border-left: 1px solid var(--m-border);
  }
  .mango-perf-load-name {
    align-items: flex-start;
  }
  .mango-perf-load-name span,
  .mango-perf-load-metric span {
    flex-basis: 100%;
  }
  .mango-perf-load-metric:nth-child(3) {
    border-top: 1px solid var(--m-border);
    border-left: 0;
  }
  .mango-perf-load-metric:nth-child(4) {
    border-top: 1px solid var(--m-border);
  }
  .mango-perf-load-name span,
  .mango-perf-load-metric span,
  .mango-perf-load-metric small {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-load-name strong,
  .mango-perf-load-metric strong {
    overflow: hidden;
    max-width: 100%;
    color: var(--m-text);
    font-size: 15px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-perf-load-metric strong {
    color: var(--m-primary);
    font-size: 18px;
  }
  .mango-perf-settings-panel :deep(.arco-form-item) {
    margin-bottom: 10px;
  }
  .mango-perf-settings-panel :deep(.arco-input-number),
  .mango-perf-settings-panel :deep(.arco-select) {
    width: 100%;
  }
  .mango-perf-goal-template-select {
    width: 144px;
  }
  .mango-perf-goal-description {
    margin: 0 0 10px;
    line-height: 18px;
  }
  .mango-perf-goal-form {
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
  }
  .mango-perf-goal-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 128px;
    align-items: center;
    gap: 10px;
    padding: 11px 12px;
    background: var(--m-surface);
  }
  .mango-perf-goal-row + .mango-perf-goal-row {
    border-top: 1px solid var(--m-border);
  }
  .mango-perf-goal-row > span {
    display: grid;
    gap: 2px;
  }
  .mango-perf-goal-row small {
    color: var(--m-muted);
    font-size: 11px;
  }
  .mango-perf-goal-row :deep(.arco-input-number) {
    width: 100%;
  }
  @container (max-width: 1199px) {
    .mango-perf-editor-grid {
      grid-template-columns: minmax(0, 1fr);
    }
    .mango-perf-section-heading small {
      display: none;
    }
  }
</style>
