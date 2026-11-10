<template>
  <BaseSidePanel
    :visible="visible"
    title="流程自愈"
    page-description="定义步骤目标和可验证状态；安全且高置信的 AI 修复会自动同步，并标记为待检查"
    :width="960"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="mango-step-healing-panel">
      <a-alert v-if="error" type="error">{{ error }}</a-alert>
      <template v-for="kind in (['records', 'versions', 'cases', 'nodes'] as const)" :key="kind"></template>
      <a-tabs v-model:active-key="activeTab">
        <a-tab-pane key="config" title="自愈配置">
          <a-form :model="draft" :disabled="saving || resourceLoading.nodes" layout="horizontal">
            <section class="mango-step-healing-section mango-step-healing-section--switch">
              <div class="mango-step-healing-section__head">
                <div>
                  <h3>启用流程自愈</h3>
                  <p>执行偏离目标时，允许 AI 分析页面状态并修复低风险流程。</p>
                </div>
                <a-switch v-model="draft.healing_enabled" aria-label="启用流程自愈" />
              </div>
            </section>

            <template v-if="draft.healing_enabled">
              <section class="mango-step-healing-section">
                <div class="mango-step-healing-section__head">
                  <div>
                    <h3>目标与判定</h3>
                    <p>告诉 AI 要完成什么，并提供可验证的开始与完成状态。</p>
                  </div>
                </div>
                <a-form-item
                  label="步骤目标"
                  required
                  :validate-status="validation.goal ? 'error' : undefined"
                  :help="validation.goal"
                >
                  <a-textarea
                    v-model="draft.goal"
                    :max-length="1000"
                    show-word-limit
                    placeholder="例如：创建订单模板并进入可编辑状态"
                    @input="validation.goal = ''"
                  />
                </a-form-item>
                <ConditionGroupEditor
                  v-model="draft.entry_criteria"
                  title="进入条件（可选）"
                  :element-options="elementOptions"
                  :disabled="saving"
                  :error-message="validation.entryCriteria"
                  @update:model-value="validation.entryCriteria = ''"
                />
                <ConditionGroupEditor
                  v-model="draft.success_criteria"
                  title="成功条件"
                  required
                  :element-options="elementOptions"
                  :disabled="saving"
                  :error-message="validation.successCriteria"
                  @update:model-value="validation.successCriteria = ''"
                />
              </section>

              <section class="mango-step-healing-section">
                <div class="mango-step-healing-section__head">
                  <div>
                    <h3>节点检查点</h3>
                    <p>按节点配置执行前和执行后的页面状态；未添加条件的检查点不会参与执行判断。</p>
                  </div>
                  <a-tag>{{ nodeCheckpoints.length }} 个节点</a-tag>
                </div>
  <div v-if="!nodeCheckpoints.length" class="mango-empty-state">{{ resourceLoading.nodes ? '节点加载中…' : '当前流程暂无已保存节点' }}</div>
                <a-collapse
                  v-else
                  v-model:active-key="expandedCheckpointKeys"
                  class="mango-step-healing-checkpoints"
                >
                  <a-collapse-item
                    v-for="(node, index) in nodeCheckpoints"
                    :key="String(node.id)"
                  >
                    <template #header>
                      <div class="mango-step-healing-checkpoint__header">
                        <strong>{{ index + 1 }}. {{ node.title }}</strong>
                        <span>
                          前置 {{ conditionCount(node.precondition) }} · 后置
                          {{ conditionCount(node.postcondition) }}
                        </span>
                      </div>
                    </template>
                    <div class="mango-step-healing-checkpoint__body">
                      <ConditionGroupEditor
                        v-model="node.precondition"
                        title="执行前状态（可选）"
                        :element-options="elementOptions"
                        :disabled="saving"
                        :error-message="nodeValidation[`${node.id}:pre`]"
                        @update:model-value="clearNodeValidation(node.id, 'pre')"
                      />
                      <ConditionGroupEditor
                        v-model="node.postcondition"
                        title="执行后状态（可选）"
                        :element-options="elementOptions"
                        :disabled="saving"
                        :error-message="nodeValidation[`${node.id}:post`]"
                        @update:model-value="clearNodeValidation(node.id, 'post')"
                      />
                    </div>
                  </a-collapse-item>
                </a-collapse>
              </section>

              <section class="mango-step-healing-section">
                <div class="mango-step-healing-section__head">
                  <div>
                    <h3>执行策略</h3>
                    <p>控制 AI 可以采取的修复范围和本次修复的最长等待时间。</p>
                  </div>
                </div>
                <div class="mango-step-healing-grid">
                  <a-form-item
                    label="运行模式"
                    required
                    :validate-status="validation.mode ? 'error' : undefined"
                    :help="validation.mode"
                  >
                    <a-select v-model="draft.healing_policy.mode" @change="validation.mode = ''">
                      <a-option value="suggest_only">只给建议</a-option>
                      <a-option value="execute_low_risk">自动执行低风险修复</a-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item
                    label="智能修复总超时（秒）"
                    required
                    :validate-status="validation.timeout ? 'error' : undefined"
                    :help="validation.timeout"
                  >
                    <a-input-number
                      v-model="draft.healing_policy.total_timeout_seconds"
                      :min="5"
                      :max="120"
                      @change="validation.timeout = ''"
                    />
                  </a-form-item>
                </div>
              </section>

              <section class="mango-step-healing-section">
                <div class="mango-step-healing-section__head">
                  <div>
                    <h3>正式流程同步</h3>
                    <p>修复通过安全校验后，自动保存为下次执行可复用的正式节点。</p>
                  </div>
                  <a-switch
                    v-model="draft.healing_policy.auto_writeback"
                    aria-label="成功后自动同步到正式流程"
                  />
                </div>
                <a-form-item
                  v-if="draft.healing_policy.auto_writeback"
                  label="自动同步最低置信度"
                  required
                  :validate-status="validation.confidence ? 'error' : undefined"
                  :help="validation.confidence"
                >
                  <div class="mango-step-healing-confidence-control">
                    <div class="mango-step-healing-confidence">
                      <a-slider
                        v-model="draft.healing_policy.auto_writeback_min_confidence"
                        :min="0.7"
                        :max="1"
                        :step="0.01"
                        :format-tooltip="formatConfidence"
                        aria-label="自动同步最低置信度"
                        @change="validation.confidence = ''"
                      />
                      <strong>{{ formatConfidence(draft.healing_policy.auto_writeback_min_confidence) }}</strong>
                    </div>
                    <div class="mango-step-healing-confidence__range">
                      <span>70%</span>
                      <span>100%</span>
                    </div>
                  </div>
                </a-form-item>
                <a-alert v-if="draft.healing_policy.auto_writeback" type="info" class="mango-step-healing-impact">
                  仅同步已验证成功、低风险且具有稳定定位器的新增动作；节点会标记“AI修复·待检查”，并保留回滚版本。
                </a-alert>
              </section>
            </template>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="records" title="修复记录">
          <a-alert v-if="referencedCases.length" type="warning" class="mango-step-healing-impact">
            应用修复会影响引用该页面步骤的 {{ referencedCases.length }} 个 Case，请确认后再应用。
          </a-alert>
          <a-table
            class="mango-step-healing-table mango-native-scroll-table"
            :data="records"
            :loading="resourceLoading.records"
            :pagination="false"
            :bordered="false"
            size="small"
            row-key="id"
            :scroll="{ x: 890, y: 420 }"
          >
            <template #columns>
              <a-table-column title="时间" data-index="create_time" :width="170" :ellipsis="true" :tooltip="true" />
              <a-table-column title="结果" :width="90">
                <template #cell="{ record }"><a-tag size="small" :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag></template>
              </a-table-column>
              <a-table-column title="说明" data-index="user_message" :width="280" :ellipsis="true" :tooltip="true" />
              <a-table-column title="同步状态" :width="160">
                <template #cell="{ record }">
                  <a-tag size="small" :color="writebackColor(record.writeback_status)">
                    {{ writebackText(record.writeback_status) }}
                  </a-tag>
                </template>
              </a-table-column>
              <a-table-column title="操作" :width="160" fixed="right" align="center">
                <template #cell="{ record }">
                  <MangoTableActions :actions="repairRecordActions(record)" />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="versions" title="版本回滚">
          <a-table
            class="mango-step-healing-table mango-native-scroll-table"
            :data="versions"
            :loading="resourceLoading.versions"
            :pagination="false"
            :bordered="false"
            size="small"
            row-key="id"
            :scroll="{ x: 670, y: 420 }"
          >
            <template #columns>
              <a-table-column title="版本" data-index="version" :width="100" />
              <a-table-column title="来源" data-index="source" :width="240" :ellipsis="true" :tooltip="true" />
              <a-table-column title="创建时间" data-index="create_time" :width="170" :ellipsis="true" :tooltip="true" />
              <a-table-column title="操作" :width="160" align="center">
                <template #cell="{ record }">
                  <MangoTableActions :actions="[{ label: '回滚', danger: true, loading: saving, disabled: saving, onClick: () => rollback(record.version) }]" />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </div>
    <a-modal v-model:visible="detailVisible" title="流程自愈详情" :footer="false" :width="720" @cancel="detailSequence++; detailLoading = false; selectedDetail = null">
      
      <a-spin :loading="detailLoading">
        <a-descriptions v-if="selectedDetail" :column="2" bordered size="small">
          <a-descriptions-item label="触发原因">{{ triggerText(selectedDetail.trigger) }}</a-descriptions-item>
          <a-descriptions-item label="结果">{{ statusText(selectedDetail.status) }}</a-descriptions-item>
          <a-descriptions-item label="可信度">{{ Math.round((selectedDetail.confidence || 0) * 100) }}%</a-descriptions-item>
          <a-descriptions-item label="配置版本">{{ selectedDetail.source_version }}</a-descriptions-item>
          <a-descriptions-item label="用户说明" :span="2">{{ selectedDetail.user_message || '-' }}</a-descriptions-item>
          <a-descriptions-item v-if="selectedDetail.error_message" label="失败原因" :span="2">{{ selectedDetail.error_message }}</a-descriptions-item>
          <a-descriptions-item label="修复前检查点" :span="2">{{ checkpointText(selectedDetail.before_state) }}</a-descriptions-item>
          <a-descriptions-item label="修复后检查点" :span="2">{{ checkpointText(selectedDetail.after_state) }}</a-descriptions-item>
        </a-descriptions>
        <div v-if="selectedDetail" class="mango-step-healing-plan">
          <strong>建议动作</strong>
          <div v-if="!planActions(selectedDetail).length" class="mango-empty-state">没有可执行建议</div>
          <a-timeline v-else>
            <a-timeline-item v-for="(action, index) in planActions(selectedDetail)" :key="index">
              {{ actionText(action) }}：{{ action.reason }}
            </a-timeline-item>
          </a-timeline>
          <a-alert v-if="selectedDetail.writeback_status === 'pending_review' && !canDirectApply(selectedDetail)" type="info">
            该建议只能临时执行。请按建议编辑并保存正式画布后，再拒绝或关闭本条待审核记录。
          </a-alert>
        </div>
      </a-spin>
    </a-modal>
    <template #footer-buttons>
      <a-button @click="emit('update:visible', false)">取消</a-button>
      <a-button type="primary" :loading="saving" @click="save">保存配置</a-button>
    </template>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import type { UiStepConditionGroup, UiStepHealingPolicy } from '@/types/ui-test/case'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import {
    getUiPageStepHealRecords,
    getUiPageStepHealRecord,
    getUiPageStepReferencedCases,
    getUiPageStepVersions,
    postUiPageStepHealApply,
    postUiPageStepHealReject,
    postUiPageStepRollback,
    putUiSteps,
  } from '@/api/uitest/page-steps'
  import {
    getUiPageStepsDetailed,
    postUiPageStepsDetailed,
  } from '@/api/uitest/page-steps-detailed'
  import { useStepHealingWrite } from '@/hooks/use-ui-step-healing-write'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import { liveObject, liveId } from './ui-live-workbench'
  import { readStepGroup, readStepDetail, stepArray, stepResponse, requiredStepId, type StepRecord, type StepElement, type StepDetail } from './ui-page-step'
  import { readHealingRecord, type HealingDraft, type HealingCheckpoint, type HealingRecord, type HealingVersion, type HealingAction } from './ui-step-healing'
  import ConditionGroupEditor from './UiStepConditionEditor.vue'

  const props = withDefaults(defineProps<{
    visible: boolean
    pageStepId: number | string
    record: StepRecord | null
    elementOptions?: StepElement[]
  }>(), {
    elementOptions: () => [],
  })
  const emit = defineEmits<{ (event: 'update:visible', value: boolean): void; (event: 'changed'): void }>()
  const activeTab = ref('config')
  const { saving, executeLocked } = useStepHealingWrite(() => props.pageStepId)
  const records = ref<HealingRecord[]>([])
  const versions = ref<HealingVersion[]>([])
  const referencedCases = ref<Array<{ id: string | number; name: string }>>([])
  const detailVisible = ref(false)
  const detailLoading = ref(false)
  const selectedDetail = ref<HealingRecord | null>(null)
  const expandedCheckpointKeys = ref<string[]>([])
  const nodeCheckpoints = ref<HealingCheckpoint[]>([])
  const nodeValidation = reactive<Record<string, string>>({})
  const defaultPolicy = (): UiStepHealingPolicy => ({
    mode: 'execute_low_risk', total_timeout_seconds: 60, max_model_calls: 2,
    max_patch_actions: 3, max_recovery_rounds: 1,
    allowed_actions: ['retry_node', 'replace_target', 'insert_action', 'skip_node', 'jump_to_node'],
    auto_writeback: true, auto_writeback_min_confidence: 0.9,
  })
  const emptyGroup = (): UiStepConditionGroup => ({ operator: 'all', conditions: [] })
  const supportedConditionTypes = new Set([
    'visible_text', 'url_path', 'page_title', 'element_state',
  ])
  const draft = reactive<HealingDraft>({
    goal: '', healing_enabled: false, healing_policy: defaultPolicy(),
    entry_criteria: emptyGroup(), success_criteria: emptyGroup(),
  })
  const validation = reactive({
    goal: '',
    mode: '',
    timeout: '',
    entryCriteria: '',
    successCriteria: '',
    confidence: '',
  })

  function clearValidation() {
    Object.assign(validation, {
      goal: '', mode: '', timeout: '', entryCriteria: '', successCriteria: '', confidence: '',
    })
    Object.keys(nodeValidation).forEach((key) => delete nodeValidation[key])
  }

  function formatConfidence(value: number | undefined) {
    const confidence = Number(value)
    return Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : '-'
  }

  function isConditionComplete(condition: UiStepConditionGroup['conditions'][number]) {
    if (!condition?.type || !condition?.matcher) return false
    if (condition.type === 'element_state') return liveId(condition.element_id) !== null
    if (condition.matcher === 'count_gte') {
      return String(condition.expected ?? '').trim() !== ''
        && condition.count !== null
        && condition.count !== undefined
        && Number.isFinite(Number(condition.count))
        && Number(condition.count) >= 0
    }
    return String(condition.expected ?? '').trim() !== ''
  }

  function conditionCount(group: UiStepConditionGroup | null | undefined) {
    return group?.conditions?.length ?? 0
  }

  function clearNodeValidation(id: number | string, phase: 'pre' | 'post') {
    delete nodeValidation[`${id}:${phase}`]
  }

  function normalizeOptionalGroup(group: UiStepConditionGroup) {
    const normalized = normalizeConditionGroup(group)
    return conditionCount(normalized) ? normalized : {}
  }

  function normalizeConditionGroup(value: unknown): UiStepConditionGroup {
    const group = readStepGroup(value)
    return { ...group, conditions: group.conditions.filter(condition => supportedConditionTypes.has(condition.type)) }
  }

  function checkpointSignature(node: Pick<HealingCheckpoint, 'precondition' | 'postcondition'>) {
    return JSON.stringify({
      precondition: normalizeOptionalGroup(node.precondition),
      postcondition: normalizeOptionalGroup(node.postcondition),
    })
  }

  function nodeTitle(item: StepDetail) {
    const flowNode = (props.record?.flow_data?.nodes || []).find(
      (node) => String(node?.config?.id) === String(item?.id)
    )
    return flowNode?.label || item?.ele_name?.name || item?.name || item?.ope_key || `节点 #${item?.id}`
  }

  function syncNodeCheckpoints(items: StepDetail[]) {
    const flowOrder = new Map<string, number>(
      (props.record?.flow_data?.nodes || []).map((node, index) => [
        String(node?.config?.id),
        index,
      ] as [string, number])
    )
    const orderedItems = [...(Array.isArray(items) ? items : [])].sort(
      (left, right) =>
        (flowOrder.get(String(left?.id)) ?? Number.MAX_SAFE_INTEGER) -
        (flowOrder.get(String(right?.id)) ?? Number.MAX_SAFE_INTEGER)
    )
    nodeCheckpoints.value = orderedItems.map((item) => {
      const node = {
        id: requiredStepId(item.id),
        title: nodeTitle(item),
        precondition: normalizeConditionGroup(item.precondition),
        postcondition: normalizeConditionGroup(item.postcondition),
        originalSignature: '',
      }
      node.originalSignature = checkpointSignature(node)
      return node
    })
    expandedCheckpointKeys.value = nodeCheckpoints.value
      .filter((node) => conditionCount(node.precondition) || conditionCount(node.postcondition))
      .map((node) => String(node.id))
  }

  function validateNodeCheckpoints() {
    let valid = true
    nodeCheckpoints.value.forEach((node) => {
      const phases = ['pre', 'post'] as const
      phases.forEach((phase) => {
        const field = phase === 'pre' ? 'precondition' : 'postcondition'
        const conditions = Array.isArray(node[field]?.conditions) ? node[field].conditions : []
        if (conditions.some((condition) => !isConditionComplete(condition))) {
          nodeValidation[`${node.id}:${phase}`] = '请补全已添加的条件'
          if (!expandedCheckpointKeys.value.includes(String(node.id))) {
            expandedCheckpointKeys.value.push(String(node.id))
          }
          valid = false
        }
      })
    })
    return valid
  }

  function validateDraft() {
    clearValidation()
    if (!draft.healing_enabled) return true
    if (!String(draft.goal || '').trim()) validation.goal = '请填写步骤目标'
    if (!['suggest_only', 'execute_low_risk'].includes(draft.healing_policy?.mode)) {
      validation.mode = '请选择自愈运行模式'
    }
    const timeout = Number(draft.healing_policy?.total_timeout_seconds)
    if (!Number.isFinite(timeout) || timeout < 5 || timeout > 120) {
      validation.timeout = '请填写 5–120 秒的智能修复超时时间'
    }
    const entryConditions = Array.isArray(draft.entry_criteria?.conditions)
      ? draft.entry_criteria.conditions
      : []
    if (entryConditions.some((condition) => !isConditionComplete(condition))) {
      validation.entryCriteria = '请补全已添加的进入条件'
    }
    const successConditions = Array.isArray(draft.success_criteria?.conditions)
      ? draft.success_criteria.conditions
      : []
    if (!successConditions.length) {
      validation.successCriteria = '请至少添加一条成功条件'
    } else if (successConditions.some((condition) => !isConditionComplete(condition))) {
      validation.successCriteria = '请补全已添加的成功条件'
    }
    if (draft.healing_policy?.auto_writeback) {
      const confidence = Number(draft.healing_policy?.auto_writeback_min_confidence)
      if (!Number.isFinite(confidence) || confidence < 0.7 || confidence > 1) {
        validation.confidence = '请填写 0.7–1 之间的最低置信度'
      }
    }
    return !Object.values(validation).some(Boolean) && validateNodeCheckpoints()
  }

  function syncDraft() {
    clearValidation()
    Object.assign(draft, {
      goal: props.record?.goal || '', healing_enabled: Boolean(props.record?.healing_enabled),
      healing_policy: cloneLosslessJson({ ...defaultPolicy(), ...(props.record?.healing_policy || {}) }),
      entry_criteria: normalizeConditionGroup(props.record?.entry_criteria),
      success_criteria: normalizeConditionGroup(props.record?.success_criteria),
    })
  }
  const resourceLoading = reactive({ records: false, versions: false, cases: false, nodes: false })
  const resourceErrors = reactive({ records: '', versions: '', cases: '', nodes: '' })
  const error = ref(''), detailError = ref(''), detailTarget = ref<string | number | null>(null)
  const acceptedActions = reactive(new Set<string>())
  let session = 0, detailSequence = 0
  const requests = { records: 0, versions: 0, cases: 0, nodes: 0 }
  let confirmation: ReturnType<typeof Modal.warning> | null = null
  function close() {
    session++; detailSequence++; detailVisible.value = false; selectedDetail.value = null; detailTarget.value = null; detailLoading.value = false
    error.value = detailError.value = ''
    for (const kind of ['records', 'versions', 'cases', 'nodes'] as const) { resourceLoading[kind] = false; resourceErrors[kind] = '' }
    confirmation?.close(); confirmation = null; emit('update:visible', false)
  }
  const scope = useLiveWorkbenchScope(() => [props.pageStepId, props.visible], { invalidate: close, resume: () => { if (props.visible) void load() } })
  async function loadResource(kind: keyof typeof resourceLoading) {
    const current = scope.capture(), id = props.pageStepId, version = session, sequence = ++requests[kind]
    const valid = () => current() && props.visible && version === session && sequence === requests[kind]
    if (!valid() || liveId(id) === null) return
    resourceLoading[kind] = true; resourceErrors[kind] = ''
    try {
      if (kind === 'records') { const data = liveObject(stepResponse(await getUiPageStepHealRecords(id))); const values = stepArray(data.items ?? []).map(readHealingRecord); if (valid()) records.value = values }
      if (kind === 'versions') { const values = stepArray(stepResponse(await getUiPageStepVersions(id))).map(value => { const row = liveObject(value); if (!Number.isSafeInteger(row.version)) throw Error('版本格式不正确'); return { version: Number(row.version), source: String(row.source ?? ''), create_time: String(row.create_time ?? '') } }); if (valid()) versions.value = values }
      if (kind === 'cases') { const values = stepArray(stepResponse(await getUiPageStepReferencedCases(id))).map(value => { const row = liveObject(value); return { id: requiredStepId(row.id), name: String(row.name ?? '') } }); if (valid()) referencedCases.value = values }
      if (kind === 'nodes') { const values = stepArray(stepResponse(await getUiPageStepsDetailed(id))).map(readStepDetail); if (valid()) syncNodeCheckpoints(values) }
    } catch (failure) { if (valid()) { resourceErrors[kind] = '加载失败，请重试'; reportLoadError(failure) } }
    finally { if (valid()) resourceLoading[kind] = false }
  }
  function load() { return Promise.allSettled((['records', 'versions', 'cases', 'nodes'] as const).map(loadResource)) }
  async function write(action: () => Promise<void>): Promise<boolean> {
    const current = scope.capture(), version = session
    if (!current() || !props.visible || saving.value) return false
    error.value = ''
    return executeLocked(async () => {
      try { await action(); return current() && version === session }
      catch { if (current() && version === session) error.value = '操作失败，已接受的步骤会保留，请重试剩余操作'; return false }
    })
  }
  async function save() {
    if (!validateDraft()) { Message.warning('请先完成流程自愈的必填配置'); return false }
    if (resourceLoading.nodes || resourceErrors.nodes) { error.value = '请先成功加载节点检查点'; return false }
    const current = scope.capture(), version = session, id = props.pageStepId, snapshot = cloneLosslessJson(draft)
    const checkpoints = cloneLosslessJson(nodeCheckpoints.value)
    return write(async () => {
      if (snapshot.healing_enabled) for (const node of checkpoints) {
        if (!current() || version !== session) return
        const signature = checkpointSignature(node)
        if (signature === node.originalSignature) continue
        stepResponse(await postUiPageStepsDetailed({ id: node.id, page_step: id, precondition: normalizeOptionalGroup(node.precondition), postcondition: normalizeOptionalGroup(node.postcondition) }, id))
        if (!current() || version !== session) return
        const accepted = nodeCheckpoints.value.find(item => String(item.id) === String(node.id)); if (accepted) accepted.originalSignature = signature
      }
      if (!current() || version !== session) return
      stepResponse(await putUiSteps({ id, ...snapshot }))
      if (!current() || version !== session) return
      Message.success('流程自愈配置已保存'); emit('changed'); close()
    })
  }
  async function mutateRecord(record: HealingRecord, reject = false) {
    const snapshot = cloneLosslessJson(record), key = `${reject ? 'reject' : 'apply'}:${record.id}`, current = scope.capture(), version = session
    if (acceptedActions.has(key)) return false
    return write(async () => {
      stepResponse(await (reject ? postUiPageStepHealReject(snapshot.id) : postUiPageStepHealApply(snapshot.id)))
      if (!current() || version !== session) return
      acceptedActions.add(key); emit('changed'); Message.success(reject ? '修复建议已拒绝' : '流程修复已确认')
      await Promise.allSettled([loadResource('records'), loadResource('versions')])
    })
  }
  const applyRecord = (record: HealingRecord) => mutateRecord(record)
  const rejectRecord = (record: HealingRecord) => mutateRecord(record, true)
  function rollback(version: number) {
    if (saving.value || !scope.available() || !Number.isSafeInteger(version)) return
    const id = props.pageStepId, current = scope.capture(), window = session
    confirmation?.close()
    confirmation = Modal.warning({ title: '回滚页面步骤', content: `确认回滚到版本 ${version}？`, hideCancel: false,
      onBeforeOk: () => !current() || window !== session ? Promise.resolve(false) : write(async () => {
        stepResponse(await postUiPageStepRollback(id, version)); if (!current() || window !== session) return
        Message.success('回滚成功'); emit('changed'); close()
      }),
    })
  }
  function statusText(status: string) { return ({ recovered: '已恢复', suggested: '待审核', failed: '未恢复', rejected: '已拒绝' } as Record<string, string>)[status] || status }
  function statusColor(status: string) { return status === 'recovered' ? 'green' : status === 'failed' ? 'red' : 'orange' }
  function writebackText(status: string) {
    return ({
      none: '未同步', pending_review: '待人工应用',
      auto_applied_review: '已自动同步·待检查',
      auto_applied_pending_review: '已自动同步·待检查', applied: '已确认', rolled_back: '已回滚',
    } as Record<string, string>)[status] || status
  }
  function writebackColor(status: string) {
    return status === 'applied' ? 'green' : status === 'rolled_back' ? 'gray'
      : isAutoAppliedReview(status) ? 'orange' : 'blue'
  }
  function canDirectApply(record: HealingRecord) {
    if (isAutoAppliedReview(record.writeback_status)) return true
    return record.writeback_status === 'pending_review'
      && Array.isArray(record.action_types)
      && record.action_types.length > 0
      && record.action_types.every((action: string) => ['skip_node', 'insert_action', 'retry_node'].includes(action))
  }
  function isAutoAppliedReview(status?: string) {
    return ['auto_applied_review', 'auto_applied_pending_review'].includes(status || '')
  }
  function repairRecordActions(record: HealingRecord) {
    return [
      { label: '详情', onClick: () => showDetail(record) },
      {
        label: isAutoAppliedReview(record.writeback_status) ? '确认' : '应用',
        loading: saving.value, disabled: saving.value || acceptedActions.has(`apply:${record.id}`),
        hidden: !canDirectApply(record),
        onClick: () => applyRecord(record),
      },
      {
        label: '拒绝', disabled: saving.value || acceptedActions.has(`reject:${record.id}`),
        danger: true,
        hidden: record.writeback_status !== 'pending_review',
        onClick: () => rejectRecord(record),
      },
    ]
  }
  async function showDetail(record: HealingRecord) { detailTarget.value = record.id; detailVisible.value = true; return loadDetail() }
  async function loadDetail() {
    const current = scope.capture(), version = session, sequence = ++detailSequence, id = detailTarget.value
    const valid = () => current() && version === session && sequence === detailSequence && detailVisible.value
    if (!valid() || id === null) return
    detailLoading.value = true; selectedDetail.value = null; detailError.value = ''
    try { const value = readHealingRecord(stepResponse(await getUiPageStepHealRecord(id))); if (String(value.id) !== String(id) || (value.page_step != null && String(value.page_step) !== String(props.pageStepId))) throw Error('修复记录不匹配'); if (valid()) selectedDetail.value = value }
    catch (loadFailure0) { if (valid()) (reportLoadError(loadFailure0, "详情加载失败，请重试", false), detailError.value = '详情加载失败，请重试') }
    finally { if (valid()) detailLoading.value = false }
  }
  function planActions(record: HealingRecord) { return (record.executed_plan || record.proposed_plan)?.actions || [] }
  function checkpointText(state: HealingRecord['before_state']) { return state?.matched_checkpoints?.join('、') || '未命中' }
  function triggerText(trigger: string) {
    return ({ entry_criteria_mismatch: '进入条件不满足', precondition_mismatch: '节点执行前状态不满足', node_failed: '节点执行失败', postcondition_mismatch: '节点执行后状态不满足', success_criteria_mismatch: '步骤成功条件不满足' } as Record<string, string>)[trigger] || trigger
  }
  function actionText(action: HealingAction) {
    return ({ retry_node: '重试节点', replace_target: '临时替换目标', insert_action: '临时补充动作', skip_node: '移除失效节点', jump_to_node: '临时跳转节点', abort: '停止执行' } as Record<string, string>)[action.action] || action.action
  }
  watch(
    () => props.visible,
    (value) => {
      if (value) {
        syncDraft()
        void load()
      } else {
        session++; detailSequence++; detailVisible.value = false; selectedDetail.value = null; confirmation?.close(); confirmation = null
      }
    },
    { immediate: true }
  )
  watch(
    () => draft.healing_enabled,
    (enabled) => { if (!enabled) clearValidation() }
  )
  watch(
    () => draft.healing_policy.auto_writeback,
    (enabled) => { if (!enabled) validation.confidence = '' }
  )
</script>

<style scoped>
  .mango-step-healing-panel { display: block; min-height: 520px; padding: 0; }
  .mango-step-healing-section {
    margin-bottom: var(--m-page-gap);
    padding: var(--m-card-padding);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }
  .mango-step-healing-section--switch { background: var(--m-surface); }
  .mango-step-healing-section__head {
    display: flex;
    margin-bottom: 16px;
    align-items: flex-start;
    justify-content: space-between;
    gap: 20px;
  }
  .mango-step-healing-section__head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }
  .mango-step-healing-section__head p {
    margin: 4px 0 0;
    color: var(--m-muted);
    font-size: 13px;
    line-height: 20px;
  }
  .mango-step-healing-section--switch .mango-step-healing-section__head { margin-bottom: 0; align-items: center; }
  .mango-step-healing-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .mango-step-healing-impact { margin-top: 4px; }
  .mango-step-healing-checkpoints {
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }
  .mango-step-healing-checkpoint__header {
    display: flex;
    min-width: 0;
    width: 100%;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .mango-step-healing-checkpoint__header strong {
    overflow: hidden;
    color: var(--m-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-step-healing-checkpoint__header span {
    flex: none;
    color: var(--m-muted);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
  .mango-step-healing-checkpoint__body {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    padding-top: 4px;
  }
  .mango-step-healing-checkpoint__body :deep(.mango-step-condition) { margin-bottom: 0; }
  .mango-step-healing-plan { margin-top: 16px; }
  .mango-step-healing-confidence-control { width: 100%; }
  .mango-step-healing-confidence {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 52px;
    align-items: center;
    gap: 16px;
    width: 100%;
  }
  .mango-step-healing-confidence strong {
    color: var(--m-primary);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .mango-step-healing-confidence__range {
    display: flex;
    margin-top: -2px;
    padding-right: 68px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    justify-content: space-between;
  }
  @media (max-width: 720px) {
    .mango-step-healing-grid { grid-template-columns: 1fr; }
    .mango-step-healing-section__head { gap: 12px; }
  }
</style>
