<template>
  <div class="mango-ui-live-workbench-panel">
    <section class="mango-ui-live-workbench-panel__stage">
      <div class="mango-ui-live-workbench-panel__viewer-card">
        <div class="mango-section-title mango-ui-live-workbench-panel__viewer-head">
          <div class="mango-section-title__main">
            <h2>
              实时浏览器
              <span
                v-if="workspace.workspaceId"
                class="mango-ui-live-workbench-panel__execution-id"
              >
                （执行id：{{ workspace.workspaceId }}）
              </span>
            </h2>
            <p v-if="!workspace.workspaceId">等待执行器浏览器启动</p>
          </div>
          <div
            :id="liveActionsTargetId"
            class="mango-section-actions mango-ui-live-workbench-panel__viewer-actions"
          ></div>
        </div>
        <div class="mango-ui-live-workbench-panel__viewer">
          <UiLiveStreamPanel
            ref="livePanelRef"
            :key="workspace.workspaceId || 'pending-workspace'"
            v-model:visible="liveVisible"
            :execution-type="workspace.executionType"
            :execution-id="workspace.workspaceId"
            :resource-id="workspace.resourceId"
            :actions-target="liveActionsTarget"
            :allow-operate="supportsElementTools"
            :allow-record="supportsElementTools"
            embedded
            @command-result="handleLiveCommandResult"
            @reconnect-workspace="reopenWorkspace"
            @stream-ready="handleStreamReady"
            @stream-connection="handleStreamConnection"
            @workspace-expired="recoverExpiredWorkspace"
            @interaction-mode="handleInteractionMode"
          />
        </div>
      </div>
      <section
        v-if="supportsElementTools && interactionMode !== 'record'"
        class="mango-ui-live-workbench-panel__scan-panel"
      >
        <div class="mango-section-title mango-ui-live-workbench-panel__scan-head">
          <div class="mango-section-title__main">
            <h2>页面元素扫描</h2>
            <p v-if="scanStats">
              {{ scanModeText(scanStats.scan_mode) }} · 返回 {{ scanStats.returned_count || 0 }} 个
              · {{ scanStats.duration_ms || 0 }} ms
              <template v-if="scanStats.frame_count > 1">
                · {{ scanStats.frame_count }} 个页面框架</template
              >
              <template v-if="scanStats.shadow_roots">
                · {{ scanStats.shadow_roots }} 个 Shadow Root</template
              >
            </p>
          </div>
          <div class="mango-section-actions">
            <a-select
              v-model="scanMode"
              size="small"
              class="mango-ui-live-workbench-panel__scan-mode"
              :disabled="scanLoading"
            >
              <a-option value="quick" data-testid="qa-components-business-uiliveworkbenchpanel-option-快速扫描">快速扫描</a-option>
              <a-option value="deep" data-testid="qa-components-business-uiliveworkbenchpanel-option-深度扫描">深度扫描</a-option>
              <a-option value="region" data-testid="qa-components-business-uiliveworkbenchpanel-option-区域扫描">区域扫描</a-option>
            </a-select>
            <a-button
              type="primary"
              size="small"
              :loading="scanLoading"
              :disabled="!workspace.workspaceId"
              @click="scanPageElements"
            >
              {{ scanMode === 'region' ? '扫描区域元素' : '一键扫描页面元素' }}
            </a-button>
          </div>
        </div>
        <div v-if="scannedElements.length" class="mango-ui-live-workbench-panel__scan-table">
          <a-table
            :data="scannedElements"
            :pagination="false"
            :bordered="false"
            :scroll="{ x: 1660 }"
            size="small"
            row-key="_rowKey"
          >
            <template #columns>
              <a-table-column title="元素名称" :width="180" fixed="left">
                <template #cell="{ record }">
                  <span class="mango-ui-live-workbench-panel__scan-text">
                    {{ record._name || getElementDisplayName(record) }}
                  </span>
                </template>
              </a-table-column>
              <a-table-column title="第一组元素" :width="330">
                <template #cell="{ record }">
                  <UiLocatorGroupCell
                    :locator="getScannedLocatorGroup(record, 1)"
                    :type-label="locatorExpName(getScannedLocatorGroup(record, 1)?.exp)"
                    :type-color="enumStore.colors[getScannedLocatorGroup(record, 1)?.exp]"
                    :match-count="getScannedLocatorGroup(record, 1)?.match_count"
                    match-label="元素"
                    :text-summary="getScannedElementText(record)"
                    :source-label="locatorSourceName(getScannedLocatorGroup(record, 1)?.source)"
                    :score="getScannedLocatorGroup(record, 1)?.score"
                  />
                </template>
              </a-table-column>
              <a-table-column title="第二组元素" :width="330">
                <template #cell="{ record }">
                  <UiLocatorGroupCell
                    :locator="getScannedLocatorGroup(record, 2)"
                    :type-label="locatorExpName(getScannedLocatorGroup(record, 2)?.exp)"
                    :type-color="enumStore.colors[getScannedLocatorGroup(record, 2)?.exp]"
                    :match-count="getScannedLocatorGroup(record, 2)?.match_count"
                    match-label="元素"
                    :text-summary="getScannedElementText(record)"
                    :source-label="locatorSourceName(getScannedLocatorGroup(record, 2)?.source)"
                    :score="getScannedLocatorGroup(record, 2)?.score"
                  />
                </template>
              </a-table-column>
              <a-table-column title="第三组元素" :width="330">
                <template #cell="{ record }">
                  <UiLocatorGroupCell
                    :locator="getScannedLocatorGroup(record, 3)"
                    :type-label="locatorExpName(getScannedLocatorGroup(record, 3)?.exp)"
                    :type-color="enumStore.colors[getScannedLocatorGroup(record, 3)?.exp]"
                    :match-count="getScannedLocatorGroup(record, 3)?.match_count"
                    match-label="元素"
                    :text-summary="getScannedElementText(record)"
                    :source-label="locatorSourceName(getScannedLocatorGroup(record, 3)?.source)"
                    :score="getScannedLocatorGroup(record, 3)?.score"
                  />
                </template>
              </a-table-column>
              <a-table-column title="识别信息" :width="220">
                <template #cell="{ record }">
                  <div class="mango-ui-live-workbench-panel__scan-meta">
                    <div class="mango-ui-live-workbench-panel__scan-tags">
                      <a-tag size="small">{{ record.role || record.tag || '-' }}</a-tag>
                      <a-tag size="small" :color="record.in_viewport ? 'green' : 'orange'">
                        {{ record.in_viewport ? '视口内' : '需滚动' }}
                      </a-tag>
                      <a-tag v-if="record.frame_depth" size="small" color="blue">
                        iframe {{ record.frame_depth }} 层
                      </a-tag>
                      <a-tag v-if="record.shadow_depth" size="small" color="purple">
                        Shadow DOM
                      </a-tag>
                    </div>
                    <strong>{{ record.text || record.label || record.placeholder || '-' }}</strong>
                    <span v-if="record.risks?.length">{{ record.risks.join('；') }}</span>
                  </div>
                </template>
              </a-table-column>
              <a-table-column title="检测状态" :width="120" align="center">
                <template #cell="{ record }">
                  <a-tag
                    v-if="record._checkStatus"
                    size="small"
                    :color="record._checkStatus === 'passed' ? 'green' : 'red'"
                  >
                    {{ record._checkStatus === 'passed' ? '通过' : '失败' }}
                    <template v-if="record._checkDuration != null">
                      · {{ record._checkDuration }} ms
                    </template>
                  </a-tag>
                  <span v-else>-</span>
                </template>
              </a-table-column>
              <a-table-column title="操作" :width="140" fixed="right" align="center">
                <template #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      {
                        label: '检测',
                        loading: elementCheckLoading,
                        disabled: !workspace.workspaceId || elementCheckLoading,
                        onClick: () => checkScannedElement(record),
                      },
                      {
                        label: 'AI 推荐',
                        loading: record._aiLoading,
                        disabled: !workspace.workspaceId,
                        onClick: () => openAiLocatorRecommendation(record, 'scan'),
                      },
                      {
                        label: record._saved ? '已保存' : '保存',
                        loading: record._saving,
                        disabled: record._saved,
                        onClick: () => saveScannedElement(record),
                      },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
        <a-empty
          v-else
          class="mango-ui-live-workbench-panel__scan-empty"
          description="暂无扫描结果"
        />
      </section>
    </section>
    <aside class="mango-ui-live-workbench-panel__tools">
      <UiStepRecorderPanel
        v-if="supportsElementTools && interactionMode === 'record'"
        :actions="recordedActions"
        :page-id="pageId || ''"
        :paused="recordingPaused"
        :element-options="elementOptions"
        :page-type="pageType"
        :project-product-id="projectProductId"
        :test-env="testEnv"
        :check-loading="elementCheckLoading"
        @reorder="reorderRecordedAction"
        @remove="removeRecordedAction"
        @clear="clearRecordedActions"
        @update-action="updateRecordedAction"
        @edit-element="editRecordedElement"
        @check-element="checkRecordedElement"
        @toggle-pause="recordingPaused = !recordingPaused"
        @saved="handleRecordingSaved"
        @settings-change="handleRecorderSettingsChange"
      />
      <template v-else>
        <section class="mango-soft-panel mango-ui-live-workbench-panel__summary-card">
          <div class="mango-section-title mango-ui-live-workbench-panel__tools-head">
            <div class="mango-section-title__main">
              <h2>{{ titleText }}</h2>
              <p>{{ workspaceStatusText }}</p>
            </div>
            <div class="mango-section-actions">
              <a-tag
                :color="workspace.ready ? 'green' : workspace.workspaceId ? 'orange' : 'blue'"
                size="small"
              >
                {{ workspace.ready ? '已就绪' : workspace.workspaceId ? '连接中' : '等待中' }}
              </a-tag>
              <a-tag v-if="workspace.maxUserCount" size="small">
                {{ workspace.activeUserCount }}/{{ workspace.maxUserCount }} 人
              </a-tag>
              <a-tag
                v-if="workspace.workspaceId"
                size="small"
                :color="liveConnected ? 'green' : 'orange'"
              >
                {{ liveConnected ? '直播保护中' : `空闲回收 ${idleRemainingText}` }}
              </a-tag>
            </div>
          </div>
          <div class="mango-ui-live-workbench-panel__runtime-grid">
            <div class="mango-ui-live-workbench-panel__runtime-group">
              <div class="mango-ui-live-workbench-panel__runtime-group-head">
                <strong>等待执行器推流</strong>
                <span>{{ actuatorHintText }}</span>
              </div>
              <a-select
                v-model="selectedActuatorUsername"
                allow-clear
                placeholder="选择执行器"
                :loading="workspaceOpening"
                @change="handleActuatorChange" data-testid="qa-components-business-uiliveworkbenchpanel-select-选择执行器"
              >
                <a-option
                  v-for="item in actuatorOptions"
                  :key="item.username"
                  :value="item.username"
                  :label="actuatorLabel(item)"
                  :disabled="actuatorFullForCurrentUser(item)"
                />
              </a-select>
            </div>
            <div class="mango-ui-live-workbench-panel__runtime-group">
              <div class="mango-ui-live-workbench-panel__runtime-group-head">
                <strong>浏览器页签</strong>
                <span>固定可选可切换</span>
              </div>
              <a-select
                :model-value="livePanelRef?.activePageIdValue || ''"
                allow-clear
                placeholder="浏览器页签"
                :disabled="!workspace.workspaceId"
                @change="switchLivePage" data-testid="qa-components-business-uiliveworkbenchpanel-select-浏览器页签"
              >
                <a-option
                  v-for="page in livePanelRef?.browserPagesValue || []"
                  :key="page.page_id"
                  :value="page.page_id"
                  :label="livePanelRef?.pageTitle?.(page) || page.title || page.url || page.page_id"
                />
              </a-select>
              <div class="mango-ui-live-workbench-panel__page-actions">
                <a-button
                  size="mini"
                  :loading="livePanelRef?.pageLoadingValue || false"
                  :disabled="!workspace.workspaceId"
                  @click="refreshLivePages" data-testid="qa-components-business-uiliveworkbenchpanel-button-刷新页签"
                >
                  刷新页签
                </a-button>
                <a-button
                  size="mini"
                  status="danger"
                  :disabled="
                    !workspace.workspaceId || (livePanelRef?.browserPagesValue || []).length <= 1
                  "
                  @click="closeLivePage" data-testid="qa-components-business-uiliveworkbenchpanel-button-关闭页签"
                >
                  关闭页签
                </a-button>
              </div>
            </div>
          </div>
        </section>

        <section v-if="supportsElementTools && pickedElement" class="mango-soft-panel">
          <div class="mango-ui-live-workbench-panel__section-head">
            <strong>采集元素</strong>
            <span>顶部开关关闭时点击画面采集元素，确认后保存到页面元素表</span>
          </div>
          <div v-if="pickedElement" class="mango-ui-live-workbench-panel__picked">
            <div
              v-for="(locator, index) in pickedElement.locators"
              :key="index"
              class="mango-ui-live-workbench-panel__picked-locator"
            >
              <div class="mango-ui-live-workbench-panel__picked-locator-title">
                <strong>第{{ ['一', '二', '三'][index] }}组</strong>
                <span>{{ index === 0 ? '主定位' : '备用定位' }}</span>
              </div>
              <div class="mango-ui-live-workbench-panel__picked-locator-fields">
                <label>
                  <span>定位类型</span>
                  <a-select
                    v-model="locator.exp"
                    :options="enumStore.element_exp"
                    :field-names="fieldNames"
                    value-key="key"
                    allow-clear
                    allow-search
                    placeholder="选择类型" data-testid="qa-components-business-uiliveworkbenchpanel-select-选择类型"
                  />
                </label>
                <label>
                  <span>定位表达式</span>
                  <a-input v-model="locator.loc" allow-clear placeholder="请输入定位表达式" data-testid="qa-components-business-uiliveworkbenchpanel-input-请输入定位表达式" />
                </label>
                <label>
                  <span>下标</span>
                  <a-input v-model="locator.sub" allow-clear placeholder="从1开始" data-testid="qa-components-business-uiliveworkbenchpanel-input-从1开始" />
                </label>
              </div>
            </div>
            <div class="mango-ui-live-workbench-panel__picked-actions">
              <a-button
                size="small"
                :loading="aiLocator.loading && aiLocator.targetType === 'picked'"
                :disabled="!workspace.workspaceId"
                @click="openAiLocatorRecommendation(pickedElement, 'picked')" data-testid="qa-components-business-uiliveworkbenchpanel-button-ai-推荐"
              >
                AI 推荐
              </a-button>
              <a-button
                type="primary"
                size="small"
                :loading="savingPicked"
                @click="savePickedElement" data-testid="qa-components-business-uiliveworkbenchpanel-button-保存为页面元素"
              >
                保存为页面元素
              </a-button>
            </div>
          </div>
        </section>

        <section v-if="inlineElementResult" class="mango-soft-panel">
          <div class="mango-ui-live-workbench-panel__section-head">
            <strong>元素结果</strong>
            <span>{{ mode === 'step' ? '调试回传后自动更新' : '检测回传后自动更新' }}</span>
          </div>
          <UiStepRuntimeResult
            :result="latestElementResult"
            title="元素结果"
            empty-text="暂无元素结果"
            frameless
          />
        </section>
      </template>
    </aside>
    <UiElementEditPanel
      ref="elementEditPanelRef"
      :operation-options="operationOptions"
      :checkable="supportsElementTools"
      :check-loading-key="elementChecking ? String(getSelectedElementId()) : ''"
      :check-loading="elementCheckLoading"
      @saved="handleElementSaved"
      @check="checkEditedElement"
    />
    <UiElementDeepCheckVariablesDialog ref="deepCheckVariablesDialogRef" />
    <UiAiLocatorRecommendationPanel
      v-model:visible="aiLocator.visible"
      :loading="aiLocator.loading"
      :validating="aiLocator.validating"
      :candidates="aiLocator.candidates"
      :batch="aiLocator.batch"
      :target-name="aiLocator.targetName"
      :empty-reason="aiLocator.emptyReason"
      @refresh="handleAiLocatorRefresh"
      @use-many="useAiLocatorCandidates"
    />
    <UiElementCheckResultPanel
      v-if="mode !== 'step'"
      v-model:visible="elementCheckDetail.visible"
      :title="elementCheckDetail.title"
      :data="elementCheckDetail.data"
      :apply-loading="deepCheckApplyLoading"
      :applied="deepCheckApplied"
      @apply="applyDeepCheckUpdates"
    />
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import UiLiveStreamPanel from '@/components/business/UiLiveStreamPanel.vue'
  import UiElementEditPanel from '@/components/business/UiElementEditPanel.vue'
  import UiAiLocatorRecommendationPanel from '@/components/business/UiAiLocatorRecommendationPanel.vue'
  import UiElementCheckResultPanel from '@/components/business/UiElementCheckResultPanel.vue'
  import UiElementDeepCheckVariablesDialog from '@/components/business/UiElementDeepCheckVariablesDialog.vue'
  import UiLocatorGroupCell from '@/components/business/UiLocatorGroupCell.vue'
  import UiStepRuntimeResult from '@/components/reports/UiStepRuntimeResult.vue'
  import UiStepRecorderPanel from '@/components/business/UiStepRecorderPanel.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { createUiElementCheckSession } from '@/utils/ui-element-check-session.mjs'
  import {
    closeUiLiveWorkspace,
    createUiLiveWorkspace,
    getUiLiveWorkspaceStatus,
  } from '@/api/uitest/live-stream'
  import {
    getUiUiElementName,
    postUiElementAiLocatorRecommend,
    postUiElementAiSnapshot,
    postUiElementCheck,
    postUiElementScan,
    putUiElementDeepCheckApply,
  } from '@/api/uitest/element'
  import { getUiStepsTest } from '@/api/uitest/page-steps'
  import { getExecutorTask } from '@/api/system/executor-task'
  import {
    clearExecutorTaskObservation,
    loadExecutorTaskObservation,
    saveExecutorTaskObservation,
  } from '@/utils/executor-task-observer.mjs'
  import type { UiStepControl } from '@/types/components'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'

  const props = defineProps<{
    mode: 'element' | 'step'
    pageId?: string | number
    pageUrl?: string
    pageStepId?: string | number
    testEnv?: string | number
    category?: string
    operationOptions?: any[]
    inlineElementResult?: boolean
    stepControl?: UiStepControl
    pageType?: string | number
    projectProductId?: string | number
    checkLoading?: boolean
  }>()
  const emit = defineEmits<{
    (event: 'stream-ready'): void
    (event: 'element-check-started', value: any): void
    (event: 'element-check-result', value: any): void
    (event: 'element-check-finished'): void
    (event: 'element-saved', value: any): void
    (event: 'page-step-saved', value: any): void
  }>()

  const userStore = useUserStore()
  const enumStore = useEnum()
  const livePanelRef = ref<InstanceType<typeof UiLiveStreamPanel> | null>(null)
  const elementEditPanelRef = ref<InstanceType<typeof UiElementEditPanel> | null>(null)
  const deepCheckVariablesDialogRef = ref<InstanceType<
    typeof UiElementDeepCheckVariablesDialog
  > | null>(null)
  const liveVisible = ref(false)
  const elementOptions = ref<any[]>([])
  const selectedElementId = ref<number | string | Array<number | string>>('')
  const liveActionsTargetId = `mango-live-actions-${Math.random().toString(36).slice(2)}`
  const liveActionsTarget = `#${liveActionsTargetId}`
  const elementChecking = ref(false)
  const elementCheckLoading = computed(
    () =>
      Boolean(props.checkLoading) ||
      elementChecking.value ||
      scannedElements.value.some((item: any) => item._checking) ||
      recordedActions.value.some((item: any) => item._checking)
  )
  const stepDebugging = ref(false)
  const recordingTrialRunning = ref(false)
  const scanLoading = ref(false)
  const scanTaskId = ref('')
  const scanMode = ref<'quick' | 'deep' | 'region'>('quick')
  const scanStats = ref<any>(null)
  const savingPicked = ref(false)
  const workspaceOpening = ref(false)
  const actuatorOptions = ref<any[]>([])
  const selectedActuatorUsername = ref('')
  const liveConnected = ref(false)
  const idleNow = ref(Date.now())
  const pickedElement = ref<any>(null)
  const scannedElements = ref<any[]>([])
  const latestElementResult = ref<any>(null)
  const deepCheckApplyLoading = ref(false)
  const deepCheckApplied = ref(false)
  const elementCheckDetail = reactive({
    visible: false,
    title: '元素检测结果',
    data: null as any,
  })
  const pendingBaselineSnapshot = ref<any>(null)
  const pendingSavedScannedRecord = ref<any>(null)
  const pendingCapturedElementSave = ref(false)
  const interactionMode = ref<'select' | 'operate' | 'record'>('select')
  const recordingPaused = ref(false)
  let recordingPausedByDisconnect = false
  const recordedActions = ref<any[]>([])
  const recorderSettings = reactive({
    mergeInput: true,
    recordScroll: false,
    recordNavigation: true,
  })
  const pendingRecordedElementAction = ref<any>(null)
  const pickedForm = reactive({
    name: '',
    category: '',
  })
  const aiLocator = reactive({
    visible: false,
    loading: false,
    validating: false,
    snapshotId: '',
    batch: 0,
    candidates: [] as any[],
    target: null as any,
    targetType: '' as 'picked' | 'scan' | '',
    targetName: '',
    emptyReason: '',
    requestKey: '',
    locationDescription: '',
    surroundingText: '',
  })
  const workspace = reactive({
    workspaceId: '',
    executionType: 'element_workspace' as 'element_workspace' | 'page_step_workspace',
    resourceId: '',
    ready: false,
    error: '',
    activeUserCount: 0,
    maxUserCount: 5,
    idleDeadline: 0,
  })
  let workspaceRetryTimer: number | null = null
  let workspaceMounted = true
  let workspaceAutoRetryBlocked = false
  let idleClockTimer: number | null = null
  let workspaceReadyPromise: Promise<boolean> | null = null
  let workspaceReadyResolver: ((ready: boolean) => void) | null = null
  let workspaceReadyTimer: number | null = null
  let workspaceStatusPollTimer: number | null = null
  const readyWorkspaceIds = new Set<string>()
  const failedWorkspaceMessages = new Map<string, string>()
  let elementCheckTimer: number | null = null
  let elementCheckTaskPollTimer: number | null = null
  let scanTimer: number | null = null
  let aiLocatorValidationTimer: number | null = null
  let recordingPollTimer: number | null = null
  let elementCheckRequestId = ''
  let elementCheckTaskId = ''
  const elementCheckSession = createUiElementCheckSession()
  let workspaceRequestSeq = 0
  let streamReadyEmitted = false
  const testEnvValue = computed(() => props.testEnv ?? userStore.selected_environment)
  const supportsElementTools = computed(() => Boolean(props.pageId))
  const inlineElementResult = computed(() => props.inlineElementResult !== false)
  const recordingStorageKey = computed(() => `mango-ui-recorder:${props.pageId || 'unknown'}`)
  const titleText = computed(() =>
    props.mode === 'step' ? '页面步骤实时工作台' : '页面元素实时工作台'
  )
  const workspaceStatusText = computed(() => {
    if (workspace.ready) return '工作区已连接'
    if (workspace.workspaceId) return workspace.error || '执行器正在初始化浏览器'
    return '等待执行器推流'
  })
  const actuatorHintText = computed(() => {
    if (workspace.ready) return '直播连接期间持续保留，断开且无任务后空闲 5 分钟自动回收'
    if (workspace.workspaceId) return '执行器正在初始化'
    if (actuatorOptions.value.length) return '请选择可用执行器'
    if (workspaceOpening.value) return '正在检查在线执行器'
    return '自己的执行器上线后会自动连接'
  })
  const idleRemainingText = computed(() => {
    const remaining = Math.max(0, Math.ceil((workspace.idleDeadline - idleNow.value) / 1000))
    const minutes = Math.floor(remaining / 60)
    const seconds = String(remaining % 60).padStart(2, '0')
    return `${minutes}:${seconds}`
  })
  async function openWorkspace(actuatorUsername = '', silent = false) {
    if (!workspaceMounted || workspace.workspaceId || workspaceOpening.value) return
    const requestSeq = ++workspaceRequestSeq
    const resourceId = String(props.mode === 'step' ? props.pageStepId || '' : props.pageId || '')
    if (!resourceId || testEnvValue.value == null) {
      if (!silent) Message.error('缺少页面/步骤ID或测试环境')
      return
    }
    workspace.executionType = props.mode === 'step' ? 'page_step_workspace' : 'element_workspace'
    workspace.resourceId = resourceId
    workspaceOpening.value = true
    try {
      const res = await createUiLiveWorkspace({
        workspace_type: workspace.executionType,
        resource_id: resourceId,
        test_env: testEnvValue.value as any,
        actuator_username: actuatorUsername || undefined,
      })
      if (!workspaceMounted || requestSeq !== workspaceRequestSeq) return
      if (res.data?.status === 'select_actuator') {
        actuatorOptions.value = res.data?.actuators || []
        if (
          selectedActuatorUsername.value &&
          !actuatorOptions.value.some((item) => item.username === selectedActuatorUsername.value)
        ) {
          selectedActuatorUsername.value = ''
        }
        return
      }
      actuatorOptions.value = res.data?.actuators || actuatorOptions.value
      selectedActuatorUsername.value = res.data?.executor_username || actuatorUsername || ''
      workspace.workspaceId = res.data?.workspace_id || ''
      workspace.executionType = res.data?.execution_type || workspace.executionType
      workspace.resourceId = String(res.data?.resource_id || resourceId)
      workspace.ready = readyWorkspaceIds.delete(workspace.workspaceId)
      workspace.error = failedWorkspaceMessages.get(workspace.workspaceId) || ''
      workspace.activeUserCount = Number(res.data?.active_user_count || 0)
      workspace.maxUserCount = Number(res.data?.max_user_count || 5)
      workspace.idleDeadline = Number(res.data?.idle_deadline || Date.now() / 1000 + 300) * 1000
      failedWorkspaceMessages.delete(workspace.workspaceId)
      if (workspace.ready) finishWorkspaceReadyWait(true)
      else if (workspace.error) finishWorkspaceReadyWait(false)
      liveVisible.value = false
      streamReadyEmitted = false
      const ready = workspace.ready || (await waitForWorkspaceReady())
      if (!workspaceMounted || requestSeq !== workspaceRequestSeq) return
      if (!ready) {
        if (!silent) Message.error(workspace.error || '执行器初始化实时工作区失败，请重新连接')
        return
      }
      await nextTick()
      liveVisible.value = true
      if (res.data?.reused) Message.success('已复用当前执行器实时工作区')
      if (supportsElementTools.value) await loadElements()
    } catch (error: any) {
      if (!workspaceMounted || requestSeq !== workspaceRequestSeq) return
      const errorMessage = error?.message || error?.msg || '打开实时工作台失败'
      if (/UI授权.*缓存已过期|缓存已过期或为空/.test(errorMessage)) {
        workspaceAutoRetryBlocked = true
      }
      if (!silent) Message.error(errorMessage)
    } finally {
      if (workspaceMounted && requestSeq === workspaceRequestSeq) workspaceOpening.value = false
    }
  }

  function clearWorkspaceRetryTimer() {
    if (!workspaceRetryTimer) return
    window.clearTimeout(workspaceRetryTimer)
    workspaceRetryTimer = null
  }

  function finishWorkspaceReadyWait(ready: boolean) {
    if (workspaceReadyTimer) window.clearTimeout(workspaceReadyTimer)
    if (workspaceStatusPollTimer) window.clearTimeout(workspaceStatusPollTimer)
    workspaceReadyTimer = null
    workspaceStatusPollTimer = null
    const resolve = workspaceReadyResolver
    workspaceReadyResolver = null
    workspaceReadyPromise = null
    resolve?.(ready)
  }

  function waitForWorkspaceReady(timeout = 120000) {
    if (workspace.ready) return Promise.resolve(true)
    if (workspace.error) return Promise.resolve(false)
    if (workspaceReadyPromise) return workspaceReadyPromise
    workspaceReadyPromise = new Promise<boolean>((resolve) => {
      workspaceReadyResolver = resolve
      const workspaceId = workspace.workspaceId
      const pollStatus = async () => {
        if (!workspaceMounted || workspaceId !== workspace.workspaceId || workspace.ready) return
        try {
          const response = await getUiLiveWorkspaceStatus(workspaceId)
          const status = response.data?.status
          if (status === 'ready') {
            workspace.ready = true
            workspace.error = ''
            finishWorkspaceReadyWait(true)
            return
          }
          if (status === 'failed' || status === 'closed') {
            workspace.ready = false
            workspace.error =
              response.data?.message ||
              (status === 'closed'
                ? '实时工作区不存在或已过期'
                : '执行器初始化实时工作区失败')
            finishWorkspaceReadyWait(false)
            return
          }
        } catch (error) {
          // WebSocket 仍可能先返回；短暂查询失败不应提前终止初始化。
        }
        workspaceStatusPollTimer = window.setTimeout(pollStatus, 1000)
      }
      workspaceStatusPollTimer = window.setTimeout(pollStatus, 500)
      workspaceReadyTimer = window.setTimeout(() => {
        workspace.error = '执行器初始化实时工作区超时，请重新连接'
        finishWorkspaceReadyWait(false)
      }, timeout)
    })
    return workspaceReadyPromise
  }

  async function ensureWorkspaceReady() {
    if (!workspace.workspaceId && !workspaceOpening.value) {
      clearWorkspaceRetryTimer()
      await openWorkspace(selectedActuatorUsername.value || '')
    }
    if (!workspace.workspaceId && workspaceOpening.value) {
      const startedAt = Date.now()
      while (workspaceOpening.value && !workspace.workspaceId && Date.now() - startedAt < 15000) {
        await new Promise((resolve) => window.setTimeout(resolve, 100))
      }
    }
    if (!workspace.workspaceId) {
      if (actuatorOptions.value.length && !selectedActuatorUsername.value) {
        Message.warning('请先选择执行器并等待工作区连接完成')
      } else {
        Message.warning('实时工作区创建失败，请确认执行器在线后重试')
      }
      return false
    }
    if (workspace.ready) return true
    const ready = await waitForWorkspaceReady()
    if (!ready) {
      Message.error(workspace.error || '实时工作区初始化失败，请重新连接')
    }
    return ready
  }

  function scheduleWorkspaceRetry(delay = 3000) {
    if (
      !workspaceMounted ||
      workspaceAutoRetryBlocked ||
      workspace.workspaceId ||
      workspaceRetryTimer
    )
      return
    workspaceRetryTimer = window.setTimeout(() => {
      workspaceRetryTimer = null
      if (workspaceMounted && !workspace.workspaceId) {
        openWorkspace(selectedActuatorUsername.value || '', true)
      }
    }, delay)
  }

  async function resetWorkspace(closeRemote = true, force = false) {
    workspaceRequestSeq += 1
    const workspaceId = workspace.workspaceId
    readyWorkspaceIds.delete(workspaceId)
    failedWorkspaceMessages.delete(workspaceId)
    workspace.workspaceId = ''
    workspace.ready = false
    workspace.error = ''
    finishWorkspaceReadyWait(false)
    liveVisible.value = false
    if (closeRemote && workspaceId) {
      await closeUiLiveWorkspace(workspaceId, force).catch(() => {})
    }
  }

  async function reopenWorkspace() {
    if (workspaceOpening.value) return
    workspaceAutoRetryBlocked = false
    clearWorkspaceRetryTimer()
    await resetWorkspace(true, true)
    await openWorkspace(selectedActuatorUsername.value || '')
  }

  async function recoverExpiredWorkspace(expiredWorkspaceId?: string | number): Promise<boolean> {
    const expiredId = String(expiredWorkspaceId || workspace.workspaceId || '')
    if (expiredId && workspace.workspaceId && expiredId !== workspace.workspaceId) {
      return true
    }
    workspace.ready = false
    workspace.error = '实时工作区已断开，请点击“重新连接”'
    return false
  }

  function handlePlatformWebsocketOpen() {
    // 平台连接恢复不代表执行器工作区已丢失，禁止在这里创建新的浏览器上下文。
  }

  function actuatorLabel(item: any) {
    const name = item?.name || item?.username || '未知执行器'
    const tag = item?.is_owner ? '我的执行器' : 'OPEN'
    const count = `${Number(item?.active_user_count || 0)}/${Number(item?.max_user_count || 5)} 人`
    return `${name}（${item?.username || '-'} · ${tag} · ${count}）`
  }

  function actuatorFullForCurrentUser(item: any) {
    if (!item?.is_full) return false
    return !(item?.users || []).some((user: any) => user?.username === userStore.userName)
  }

  async function handleActuatorChange(value: any) {
    selectedActuatorUsername.value = String(value || '')
    if (!selectedActuatorUsername.value || workspaceOpening.value) return
    workspaceAutoRetryBlocked = false
    clearWorkspaceRetryTimer()
    await resetWorkspace(true, true)
    await openWorkspace(selectedActuatorUsername.value)
  }

  function switchLivePage(value: any) {
    if (!value) return
    livePanelRef.value?.switchPage?.(value)
    if (interactionMode.value === 'record' && !recordingPaused.value) {
      const page = (livePanelRef.value?.browserPagesValue || []).find(
        (item: any) => String(item.page_id) === String(value)
      )
      appendRecordedAction({
        action: 'navigation',
        name: '切换浏览器页签',
        url: page?.url,
        page,
        passive: true,
      })
    }
  }

  function refreshLivePages() {
    livePanelRef.value?.refreshPages?.()
  }

  function closeLivePage() {
    livePanelRef.value?.closeActivePage?.()
  }

  async function loadElements() {
    if (!props.pageId) return
    const res = await getUiUiElementName(props.pageId)
    elementOptions.value = res.data || []
  }

  function handleInteractionMode(value: 'select' | 'operate' | 'record') {
    interactionMode.value = value
    if (value === 'record') restoreRecordedActions()
  }

  function persistRecordedActions() {
    try {
      const draft = recordedActions.value.map(
        ({ _checking, _checkStatus, _checkDuration, ...action }: any) => action
      )
      sessionStorage.setItem(recordingStorageKey.value, JSON.stringify(draft))
    } catch (_) {
      // 浏览器禁用会话存储时仍允许继续在内存中录制。
    }
  }

  function restoreRecordedActions() {
    if (recordedActions.value.length) return
    try {
      const data = JSON.parse(sessionStorage.getItem(recordingStorageKey.value) || '[]')
      if (Array.isArray(data)) recordedActions.value = data
    } catch (_) {
      recordedActions.value = []
    }
  }

  function normalizeRecordedAction(data: any) {
    const element = data?.element || null
    const normalized: any = {
      ...data,
      client_id: data?.client_id || `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: data?.name || (element ? getElementDisplayName(element) : ''),
      category: data?.category || '未分类',
      status:
        data?.status ||
        (data?.sensitive && !String(data?.input_value || '').startsWith('${{')
          ? 'review'
          : 'ready'),
    }
    normalized.detail = buildRecordedNodeDetail(normalized)
    return normalized
  }

  function buildRecordedNodeDetail(action: any) {
    if (action?.detail) return action.detail
    const value = (f: string, v: any) => ({ f, v })
    const operationMap: Record<string, { ope_key: string; ope_value?: any[] }> = {
      click: { ope_key: 'w_click' },
      double_click: { ope_key: 'w_dblclick' },
      right_click: { ope_key: 'w_right_click' },
      input: { ope_key: 'w_input', ope_value: [value('input_value', action.input_value || '')] },
      key_press: { ope_key: 'w_press', ope_value: [value('key', action.key || 'Enter')] },
      scroll: {
        ope_key: 'w_mouse_wheel_xy',
        ope_value: [value('x', action.delta_x || 0), value('y', action.delta_y || 0)],
      },
      navigation: {
        ope_key: 'w_goto',
        ope_value: [value('url', action.url || action.page?.url || '')],
      },
      select: {
        ope_key: 'w_select_option',
        ope_value: [value('values', action.input_value || action.value || '')],
      },
      check: { ope_key: 'w_check' },
      uncheck: { ope_key: 'w_uncheck' },
    }
    if (action.action === 'drag') {
      const deltaX = Number(action.drag_delta_x || 0)
      const deltaY = Number(action.drag_delta_y || 0)
      const horizontal = Math.abs(deltaX) >= Math.abs(deltaY)
      return {
        type: 0,
        ope_key: horizontal
          ? deltaX >= 0
            ? 'w_drag_right_pixel'
            : 'w_drag_left_pixel'
          : deltaY >= 0
          ? 'w_drag_down_pixel'
          : 'w_drag_up_pixel',
        ope_value: [value('n', Math.max(1, Math.round(Math.abs(horizontal ? deltaX : deltaY))))],
        ele_name: action.element_id || null,
      }
    }
    if (action.action === 'wait')
      return {
        type: 0,
        ope_key: 'w_wait_for_timeout',
        ope_value: [value('_time', action.seconds || 1)],
        ele_name: null,
      }
    if (action.action === 'assert_page_text')
      return {
        type: 1,
        ope_key: 'w_page_to_contain_text',
        ope_value: [value('expect', action.expect || '')],
        ele_name: null,
      }
    if (action.action === 'custom_variable')
      return { type: 3, custom: [{ key: action.key || '', value: action.value || '' }] }
    const operation = operationMap[action.action]
    if (!operation) return action.detail || null
    return {
      type: 0,
      ope_key: operation.ope_key,
      ope_value: operation.ope_value || [],
      ele_name: action.element_id || null,
    }
  }

  function appendRecordedAction(data: any) {
    if (recordingPaused.value) return
    const action = normalizeRecordedAction(data)
    if (action.action === 'scroll' && !recorderSettings.recordScroll) return
    if (action.action === 'navigation' && !recorderSettings.recordNavigation) return
    const previous = recordedActions.value[recordedActions.value.length - 1]
    const sameElement =
      (previous?.element?.locators?.[0]?.loc || '') === (action.element?.locators?.[0]?.loc || '')
    if (
      recorderSettings.mergeInput &&
      action.action === 'input' &&
      previous?.action === 'input' &&
      sameElement &&
      previous.page?.page_id === action.page?.page_id &&
      !action.sensitive
    ) {
      previous.input_value = `${previous.input_value || ''}${action.input_value || ''}`
      previous.duration_ms = Number(previous.duration_ms || 0) + Number(action.duration_ms || 0)
      previous.detail = buildRecordedNodeDetail({ ...previous, detail: null })
    } else {
      recordedActions.value.push(action)
    }
    persistRecordedActions()
  }

  function handleRecorderSettingsChange(value: Record<string, any>) {
    Object.assign(recorderSettings, value)
  }

  function reorderRecordedAction(from: number, to: number) {
    const [item] = recordedActions.value.splice(from, 1)
    if (item) recordedActions.value.splice(to, 0, item)
    persistRecordedActions()
  }

  function removeRecordedAction(index: number) {
    recordedActions.value.splice(index, 1)
    persistRecordedActions()
  }

  function clearRecordedActions() {
    recordedActions.value = []
    try {
      sessionStorage.removeItem(recordingStorageKey.value)
    } catch (_) {
      // 浏览器禁用会话存储时，清理内存草稿即可。
    }
  }

  function updateRecordedAction(value: any) {
    const index = recordedActions.value.findIndex((item) => item.client_id === value.client_id)
    if (index >= 0) {
      const current = recordedActions.value[index]
      Object.assign(current, normalizeRecordedAction({ ...current, ...value }))
    } else recordedActions.value.push(normalizeRecordedAction(value))
    persistRecordedActions()
  }

  function editRecordedElement(action: any) {
    pendingRecordedElementAction.value = action
    if (action.element_id) {
      pendingCapturedElementSave.value = false
      elementEditPanelRef.value?.openEditById(action.element_id)
      return
    }
    const element = action.element || {}
    const locators = (element.locators || []).slice(0, 3)
    if (!locators[0]?.loc) {
      Message.warning('当前录制步骤没有可编辑的元素定位器')
      return
    }
    pendingCapturedElementSave.value = true
    elementEditPanelRef.value?.openCreate(
      props.pageId || '',
      action.category || props.category || '录制元素',
      {
        name: action.name || getElementDisplayName(element),
        exp: locators[0].exp,
        loc: locators[0].loc,
        sub: locators[0].sub ?? '',
        exp2: locators[1]?.exp ?? null,
        loc2: locators[1]?.loc || '',
        sub2: locators[1]?.sub ?? '',
        exp3: locators[2]?.exp ?? null,
        loc3: locators[2]?.loc || '',
        sub3: locators[2]?.sub ?? '',
        prompt: action.name || getElementDisplayName(element),
      }
    )
  }

  function handleRecordingSaved(result: any) {
    clearRecordedActions()
    interactionMode.value = 'operate'
    livePanelRef.value?.setInteractionMode?.('operate')
    void loadElements()
    emit('page-step-saved', result)
  }

  async function checkSelectedElement(
    checkMode: 'normal' | 'deep' = 'normal',
    runtimeVariables: Record<string, string> = {}
  ) {
    if (elementCheckLoading.value) return false
    const elementId = getSelectedElementId()
    if (!elementId || !workspace.workspaceId) return false
    if (String(elementId).startsWith('category:')) {
      Message.warning('请选择具体元素')
      return false
    }
    elementChecking.value = true
    const requestToken = elementCheckSession.start(elementId, workspace.workspaceId)
    elementCheckRequestId = ''
    elementCheckTaskId = ''
    clearElementCheckTimer()
    latestElementResult.value = {
      ...buildElementCheckPendingResult(elementId),
      check_mode: checkMode,
      ope_key: checkMode === 'deep' ? '元素深度检测' : '元素检测',
    }
    emit('element-check-started', {
      element_id: elementId,
      workspace_id: workspace.workspaceId,
      check_mode: checkMode,
      result: latestElementResult.value,
    })
    elementCheckTimer = window.setTimeout(
      () => {
        elementCheckTimer = null
        if (!elementCheckSession.isActive(requestToken)) return
        if (!elementChecking.value) return
        elementCheckSession.cancel(requestToken)
        elementChecking.value = false
        elementCheckRequestId = ''
        clearElementCheckTaskPoll()
        latestElementResult.value = {
          ...latestElementResult.value,
          status: 0,
          error_message: '元素检测等待回传超时，请确认执行器连接正常或查看执行器日志',
        }
        // 超时是本地状态，不是执行器回传结果。不得伪装成检测结果让父页面打开结果窗口。
        emit('element-check-finished')
      },
      checkMode === 'deep' ? 180000 : 60000
    )
    try {
      const res = await postUiElementCheck({
        element_id: elementId,
        test_env: testEnvValue.value,
        workspace_id: workspace.workspaceId,
        check_mode: checkMode,
        runtime_variables: runtimeVariables,
      })
      if (elementCheckSession.bindCheckId(requestToken, res.data?.check_id || '')) {
        elementCheckRequestId = String(res.data?.check_id || '')
      }
      elementCheckTaskId = String(res.data?.task_id || '')
      if (elementCheckTaskId) {
        saveExecutorTaskObservation('element-check', elementId, {
          taskId: elementCheckTaskId,
          businessType: 'u_element_check',
          meta: {
            checkId: elementCheckRequestId,
            checkMode,
            workspaceId: workspace.workspaceId,
          },
        })
        scheduleElementCheckTaskPoll(0)
      }
      Message.success(res.msg)
      return elementCheckRequestId || true
    } catch (error) {
      elementCheckSession.cancel(requestToken)
      elementChecking.value = false
      elementCheckRequestId = ''
      elementCheckTaskId = ''
      clearElementCheckTaskPoll()
      clearElementCheckTimer()
      latestElementResult.value = {
        ...latestElementResult.value,
        status: 0,
        error_message: (error as any)?.msg || '元素检测触发失败',
      }
      emit('element-check-finished')
      return false
    }
  }

  async function checkElementInWorkspace(
    record: any,
    checkMode: 'normal' | 'deep' = 'deep',
    runtimeVariables?: Record<string, string>
  ) {
    if (!record?.id) return false
    const variables =
      checkMode === 'deep' && runtimeVariables === undefined
        ? await deepCheckVariablesDialogRef.value?.open({ ...record, page_url: props.pageUrl })
        : runtimeVariables || {}
    if (variables === null) return false
    if (!(await ensureWorkspaceReady())) return false
    selectedElementId.value = record.id
    return checkSelectedElement(checkMode, variables)
  }

  async function checkEditedElement(record: any, checkMode: 'normal' | 'deep' = 'deep') {
    if (!record?.id) return
    selectedElementId.value = record.id
    const variables =
      checkMode === 'deep'
        ? await deepCheckVariablesDialogRef.value?.open({ ...record, page_url: props.pageUrl })
        : {}
    if (variables === null) return
    void checkSelectedElement(checkMode, variables)
  }

  function getSelectedElementId() {
    const value = selectedElementId.value
    if (Array.isArray(value)) return value[value.length - 1]
    return value
  }

  function clearElementCheckTimer() {
    if (!elementCheckTimer) return
    window.clearTimeout(elementCheckTimer)
    elementCheckTimer = null
  }

  function clearElementCheckTaskPoll() {
    if (!elementCheckTaskPollTimer) return
    window.clearTimeout(elementCheckTaskPollTimer)
    elementCheckTaskPollTimer = null
  }

  function scheduleElementCheckTaskPoll(delay = 1000) {
    clearElementCheckTaskPoll()
    if (!elementChecking.value || !elementCheckTaskId) return
    elementCheckTaskPollTimer = window.setTimeout(() => void pollElementCheckTask(), delay)
  }

  async function pollElementCheckTask() {
    if (!elementChecking.value || !elementCheckTaskId) return
    try {
      const res = await getExecutorTask(elementCheckTaskId)
      const task = res.data || {}
      if (!task.terminal) {
        scheduleElementCheckTaskPoll()
        return
      }
      clearElementCheckTaskPoll()
      const result =
        task.result?.check_id || task.result?.element_id
          ? task.result
          : {
              check_id: elementCheckRequestId,
              element_id: getSelectedElementId(),
              element_name: selectedElementRecord(getSelectedElementId())?.name,
              check_mode:
                task.task_type === 'element_deep_check' ? 'deep' : 'normal',
              status: 0,
              check_status: 'invalid',
              error_message: task.error_message || '执行器任务未返回检测结果',
            }
      const taskResult = { ...result, executor_task_id: elementCheckTaskId }
      if (!acceptElementCheckResult(taskResult)) return
      if (props.inlineElementResult !== false) showElementCheckDetail(taskResult)
      elementEditPanelRef.value?.applyRuntimeResult?.(taskResult)
      emit('element-check-result', taskResult)
      emit('element-check-finished')
    } catch (error) {
      console.log(error)
      scheduleElementCheckTaskPoll(1500)
    }
  }

  function acceptElementCheckResult(result: any) {
    if (!elementCheckSession.accept(result)) return false
    const completedTaskId = elementCheckTaskId
    const completedElementId = getSelectedElementId()
    elementChecking.value = false
    elementCheckRequestId = ''
    elementCheckTaskId = ''
    clearElementCheckTimer()
    clearElementCheckTaskPoll()
    latestElementResult.value = resolveRuntimeResult(result)
    if (completedTaskId && completedElementId) {
      clearExecutorTaskObservation('element-check', completedElementId, completedTaskId)
    }
    return true
  }

  function selectedElementRecord(elementId: any) {
    return elementOptions.value.find((item) => String(item?.id) === String(elementId))
  }

  function buildElementCheckPendingResult(elementId: any) {
    const element = selectedElementRecord(elementId)
    return {
      id: elementId,
      name: element?.name || `元素 ${elementId}`,
      type: 0,
      ope_key: '元素检测',
      status: 3,
      sleep: null,
      duration_ms: null,
      page_url: '',
      page_title: '',
      locator_engine: {
        used_source: 'waiting',
        candidate_count: 0,
        temporary_heal_used: false,
      },
      elements: [
        {
          name: element?.name || `元素 ${elementId}`,
          exp: element?.exp,
          loc: element?.loc,
          sub: element?.sub,
          ele_quantity: '-',
          element_text: '等待执行器检测回传',
        },
      ],
      error_message: '',
    }
  }

  async function scanPageElements() {
    if (scanMode.value === 'region' && !pickedElement.value) {
      interactionMode.value = 'select'
      livePanelRef.value?.setInteractionMode?.('select')
      Message.warning('请先通过实时浏览器的“选择元素”选中一个扫描区域，再开始区域扫描')
      return
    }
    scanLoading.value = true
    scannedElements.value = []
    scanStats.value = null
    clearScanTimer()
    try {
      const res = await postUiElementScan({
        page_id: props.pageId || '',
        workspace_id: workspace.workspaceId,
        mode: scanMode.value,
      })
      scanTaskId.value = String(res.data?.task_id || '')
      if (!scanTaskId.value) throw new Error('页面元素扫描任务未返回任务ID')
      saveExecutorTaskObservation('page-scan', props.pageId || '', {
        taskId: scanTaskId.value,
        businessType: 'u_page_scan',
        meta: { workspaceId: workspace.workspaceId, scanMode: scanMode.value },
      })
      scheduleScanTaskPoll(0)
    } catch (error: any) {
      scanLoading.value = false
      scanTaskId.value = ''
      Message.error(error?.msg || error?.message || '页面元素扫描任务创建失败')
    }
  }

  function restorePageScanTask() {
    const observation = loadExecutorTaskObservation('page-scan', props.pageId || '')
    if (!observation?.taskId) return
    scanTaskId.value = String(observation.taskId)
    scanMode.value = ['quick', 'deep', 'region'].includes(observation.meta?.scanMode)
      ? observation.meta.scanMode
      : 'quick'
    scanLoading.value = true
    scheduleScanTaskPoll(0)
  }

  function clearScanTimer() {
    if (scanTimer) window.clearTimeout(scanTimer)
    scanTimer = null
  }

  function scheduleScanTaskPoll(delay = 1000) {
    clearScanTimer()
    if (!scanLoading.value || !scanTaskId.value) return
    scanTimer = window.setTimeout(() => void pollScanTask(), delay)
  }

  async function pollScanTask() {
    if (!scanLoading.value || !scanTaskId.value) return
    try {
      const res = await getExecutorTask(scanTaskId.value)
      const task = res.data || {}
      if (!task.terminal) {
        scheduleScanTaskPoll()
        return
      }
      const completedTaskId = scanTaskId.value
      scanTaskId.value = ''
      clearScanTimer()
      if (task.status !== 'success') {
        scanLoading.value = false
        Message.error(task.error_message || '页面元素扫描执行失败')
        clearExecutorTaskObservation('page-scan', props.pageId || '', completedTaskId)
        return
      }
      applyPageScanResult(task.result || {})
      clearExecutorTaskObservation('page-scan', props.pageId || '', completedTaskId)
    } catch (error) {
      console.log(error)
      scheduleScanTaskPoll(1500)
    }
  }

  function applyPageScanResult(data: any) {
    scannedElements.value = (data.elements || []).map((item: any, index: number) =>
      normalizeScannedElement(item, index)
    )
    scanStats.value = { ...(data.scan_stats || {}), scan_mode: data.scan_mode || scanMode.value }
    scanLoading.value = false
  }

  function scanModeText(value: string) {
    if (value === 'deep') return '深度扫描'
    if (value === 'region') return '区域扫描'
    return '快速扫描'
  }

  function getElementDisplayName(item: any) {
    const text =
      item?.accessible_name ||
      item?.text ||
      item?.label ||
      item?.placeholder ||
      item?.name ||
      item?.tag
    const name = String(text || '新采集元素')
      .replace(/\s+/g, ' ')
      .trim()
    return name.slice(0, 60) || '新采集元素'
  }

  function normalizeScannedElement(item: any, index: number) {
    const locators = Array.isArray(item?.locators)
      ? item.locators.filter((locator: any) => locator?.loc).slice(0, 3)
      : []
    return {
      ...item,
      locators,
      _rowKey: `${Date.now()}-${index}-${locators[0]?.loc || item?.text || ''}`,
      _name: getElementDisplayName(item),
      _category: String(props.category || '未分类'),
      _checking: false,
      _aiLoading: false,
      _saving: false,
      _saved: false,
    }
  }

  async function openAiLocatorRecommendation(record: any, targetType: 'picked' | 'scan') {
    if (!record || !workspace.workspaceId) return
    clearAiLocatorValidationTimer()
    aiLocator.visible = true
    aiLocator.snapshotId = ''
    aiLocator.batch = 0
    aiLocator.candidates = []
    aiLocator.emptyReason = ''
    aiLocator.locationDescription = ''
    aiLocator.surroundingText = ''
    aiLocator.target = record
    aiLocator.targetType = targetType
    aiLocator.targetName = record._name || getElementDisplayName(record)
    await loadAiLocatorBatch(false)
  }

  async function loadAiLocatorBatch(refresh = false) {
    if (!aiLocator.target || aiLocator.loading) return
    aiLocator.loading = true
    aiLocator.validating = false
    aiLocator.target._aiLoading = true
    clearAiLocatorValidationTimer()
    try {
      const locators = (aiLocator.target.locators || []).filter((item: any) => item?.loc)
      const response = await postUiElementAiLocatorRecommend(
        refresh && aiLocator.snapshotId
          ? {
              snapshot_id: aiLocator.snapshotId,
              location_description: aiLocator.locationDescription,
              surrounding_text: aiLocator.surroundingText,
            }
          : {
              page_id: props.pageId,
              workspace_id: workspace.workspaceId,
              context: aiLocatorContext(aiLocator.target),
              existing_locators: locators,
              location_description: aiLocator.locationDescription,
              surrounding_text: aiLocator.surroundingText,
            }
      )
      const data = response.data || {}
      aiLocator.snapshotId = String(data.snapshot_id || aiLocator.snapshotId)
      aiLocator.batch = Number(data.batch || 0)
      aiLocator.candidates = (data.candidates || []).map((item: any) => ({
        ...item,
        validation_done: false,
      }))
      aiLocator.emptyReason = String(data.diagnostics?.message || '')
      if (!aiLocator.candidates.length) {
        Message.warning(aiLocator.emptyReason || '当前批次没有可用的定位器候选')
        return
      }
      await validateAiLocatorCandidates()
    } catch (error) {
      aiLocator.candidates = []
      aiLocator.emptyReason =
        (error as any)?.msg || (error as any)?.message || 'AI 定位器候选请求失败，请稍后重试'
    } finally {
      aiLocator.loading = false
      if (aiLocator.target) aiLocator.target._aiLoading = false
    }
  }

  function handleAiLocatorRefresh(guidance: {
    location_description?: string
    surrounding_text?: string
  }) {
    aiLocator.locationDescription = String(guidance?.location_description || '').trim()
    aiLocator.surroundingText = String(guidance?.surrounding_text || '').trim()
    void loadAiLocatorBatch(true)
  }

  function aiLocatorContext(record: any) {
    return {
      tag: record.tag,
      role: record.role,
      text: record.text,
      label: record.label,
      accessible_name: record.accessible_name,
      placeholder: record.placeholder,
      attributes: record.attributes || {},
      frame_depth: record.frame_depth || 0,
      shadow_depth: record.shadow_depth || 0,
      baseline_snapshot: record.baseline_snapshot || {},
    }
  }

  async function validateAiLocatorCandidates() {
    const locators = aiLocator.candidates.slice(0, 5)
    if (!locators.length) return
    aiLocator.validating = true
    aiLocator.requestKey = `ai-recommend:${Date.now()}`
    const sent = await livePanelRef.value?.sendWorkspaceCommand('check_locator', {
      row_key: aiLocator.requestKey,
      name: aiLocator.targetName,
      locators,
    })
    if (!sent) {
      aiLocator.validating = false
      return
    }
    aiLocatorValidationTimer = window.setTimeout(() => {
      aiLocatorValidationTimer = null
      if (!aiLocator.validating) return
      aiLocator.validating = false
      aiLocator.candidates = aiLocator.candidates.map((item: any) => ({
        ...item,
        validation_done: true,
        verified: false,
        error_message: '浏览器验证等待回传超时',
      }))
    }, 30000)
  }

  function applyAiLocatorValidation(data: any) {
    if (data.row_key !== aiLocator.requestKey) return false
    clearAiLocatorValidationTimer()
    aiLocator.validating = false
    const groups = data.scan_check_result?.locator_groups || []
    aiLocator.candidates = aiLocator.candidates.map((item: any, index: number) => {
      const group = groups[index] || {}
      const count = Number(group.count || 0)
      return {
        ...item,
        validation_done: true,
        verified: group.status === 'valid' && count === 1 && Boolean(group.visible),
        count,
        visible: Boolean(group.visible),
        duration_ms: Number(group.duration_ms || 0),
        element_text: group.element_text || '',
        error_message: group.error_message || '',
      }
    })
    const passedCount = aiLocator.candidates.filter((item: any) => item.verified).length
    aiLocator.emptyReason = passedCount
      ? ''
      : `AI 已生成 ${aiLocator.candidates.length} 个候选，但浏览器校验全部失败`
    return true
  }

  function useAiLocatorCandidates(candidates: any[]) {
    if (!aiLocator.target) return
    const selected = candidates.filter((candidate) => candidate?.verified).slice(0, 3)
    if (!selected.length) return
    const locators = normalizePickedLocators(aiLocator.target.locators)
    selected.forEach((candidate, index) => {
      locators[index] = {
        exp: candidate.exp,
        loc: candidate.loc,
        sub: candidate.sub ?? '',
      }
    })
    aiLocator.target.locators = locators
    if (aiLocator.targetType === 'picked') {
      pickedElement.value = aiLocator.target
    }
    aiLocator.visible = false
    Message.success(`已替换前 ${selected.length} 组定位器，请确认后保存元素`)
  }

  function normalizePickedLocators(value: any) {
    const locators = Array.isArray(value)
      ? value.slice(0, 3).map((item: any) => ({
          exp: item?.exp ?? null,
          loc: item?.loc || '',
          sub: item?.sub ?? '',
        }))
      : []
    while (locators.length < 3) locators.push({ exp: null, loc: '', sub: '' })
    return locators
  }

  function clearAiLocatorValidationTimer() {
    if (aiLocatorValidationTimer) window.clearTimeout(aiLocatorValidationTimer)
    aiLocatorValidationTimer = null
  }

  function getScannedLocatorGroup(record: any, group: number) {
    return record?.locators?.[group - 1]
  }

  function getScannedElementText(record: any) {
    return String(
      record?.text || record?.accessible_name || record?.label || record?.placeholder || ''
    )
      .replace(/\s+/g, ' ')
      .trim()
  }

  function locatorExpName(value: any) {
    const map: Record<number, string> = {
      0: 'XPATH',
      1: 'ID',
      2: '通用定位器',
      3: '文本',
      4: '占位符',
      5: '标签',
      6: '角色',
      7: '标题',
      8: '链接文本',
      9: 'CSS',
    }
    const key = Number(value)
    return map[key] || `类型 ${value ?? '-'}`
  }

  function locatorSourceName(value: any) {
    const source = String(value || '').replace(/_frame$/, '')
    const map: Record<string, string> = {
      testid: '测试属性',
      'data-test': '测试属性',
      'data-qa': '测试属性',
      id_xpath: '唯一 ID',
      role: '语义角色',
      label: '标签',
      placeholder: '占位符',
      text: '文本',
      css_path: 'CSS 路径',
      xpath: 'XPath',
    }
    return `${map[source] || source || '候选'}${
      String(value || '').endsWith('_frame') ? ' · iframe' : ''
    }`
  }

  function saveScannedElement(record: any) {
    const locator = getScannedLocatorGroup(record, 1)
    if (!locator?.loc) {
      Message.error('没有可保存的定位器')
      return
    }
    const elementName = String(record._name || getElementDisplayName(record)).trim()
    const locator2 = getScannedLocatorGroup(record, 2)
    const locator3 = getScannedLocatorGroup(record, 3)
    pendingBaselineSnapshot.value = record.baseline_snapshot
    pendingSavedScannedRecord.value = record
    pendingCapturedElementSave.value = true
    elementEditPanelRef.value?.openCreate(
      props.pageId || '',
      String(record._category || props.category || '未分类').trim(),
      {
        name: elementName,
        exp: locator.exp,
        loc: locator.loc,
        sub: locator.sub ?? '',
        exp2: locator2?.exp ?? null,
        loc2: locator2?.loc || '',
        sub2: locator2?.sub ?? '',
        exp3: locator3?.exp ?? null,
        loc3: locator3?.loc || '',
        sub3: locator3?.sub ?? '',
        prompt: elementName,
      }
    )
  }

  async function checkScannedElement(record: any) {
    if (elementCheckLoading.value) return
    const locators = (record?.locators || []).filter((item: any) => item?.loc).slice(0, 3)
    if (!locators.length) {
      Message.error('没有可检测的定位器')
      return
    }
    record._checking = true
    latestElementResult.value = {
      id: 0,
      name: record._name || getElementDisplayName(record),
      type: 0,
      ope_key: '扫描元素检测',
      status: 3,
      sleep: null,
      duration_ms: null,
      page_url: '',
      page_title: '',
      locator_engine: {
        used_source: 'waiting',
        candidate_count: locators.length,
        temporary_heal_used: false,
      },
      elements: [
        {
          name: record._name || getElementDisplayName(record),
          exp: locators[0]?.exp,
          loc: locators[0]?.loc,
          sub: locators[0]?.sub,
          ele_quantity: '-',
          element_text: '等待执行器检测回传',
        },
      ],
      error_message: '',
    }
    emit('element-check-started', {
      element_id: 0,
      scan_row_key: record._rowKey,
      element_name: record._name || getElementDisplayName(record),
      result: latestElementResult.value,
    })
    const sent = await livePanelRef.value?.sendWorkspaceCommand('check_locator', {
      row_key: record._rowKey,
      name: record._name || getElementDisplayName(record),
      locators,
    })
    if (!sent) {
      record._checking = false
      emit('element-check-finished')
      return
    }
    window.setTimeout(() => {
      if (!record._checking) return
      record._checking = false
      latestElementResult.value = {
        ...latestElementResult.value,
        status: 0,
        error_message: '扫描元素检测等待回传超时，请确认执行器连接正常或查看执行器日志',
      }
      emit('element-check-result', buildScannedCheckDetail(record, latestElementResult.value))
    }, 30000)
  }

  function recordedElementLocators(action: any) {
    const element = action?.element || selectedElementRecord(action?.element_id) || {}
    if (Array.isArray(element.locators))
      return element.locators.filter((item: any) => item?.loc).slice(0, 3)
    return [
      { exp: element.exp, loc: element.loc, sub: element.sub },
      { exp: element.exp2, loc: element.loc2, sub: element.sub2 },
      { exp: element.exp3, loc: element.loc3, sub: element.sub3 },
    ].filter((item) => item.loc && item.exp !== undefined && item.exp !== null)
  }

  async function checkRecordedElement(action: any) {
    if (elementCheckLoading.value) return
    const locators = recordedElementLocators(action)
    if (!locators.length) {
      Message.error('当前录制节点没有可检测的定位器')
      return
    }
    const rowKey = `recording:${action.client_id}`
    action._checking = true
    action._checkStatus = ''
    emit('element-check-started', {
      element_id: 0,
      scan_row_key: rowKey,
      element_name: action.name || getElementDisplayName(action.element || {}),
      check_mode: 'normal',
    })
    const sent = await livePanelRef.value?.sendWorkspaceCommand('check_locator', {
      row_key: rowKey,
      name: action.name || getElementDisplayName(action.element || {}),
      locators,
    })
    if (!sent) {
      action._checking = false
      emit('element-check-finished')
      return
    }
    window.setTimeout(() => {
      if (!action._checking) return
      action._checking = false
      action._checkStatus = 'failed'
      emit('element-check-finished')
      Message.error('录制元素检测等待回传超时，请确认执行器连接正常')
    }, 30000)
  }

  function buildScannedCheckDetail(record: any, result: any, baselineSnapshot?: any) {
    const status = Number(result?.status) === 1 ? 'valid' : 'invalid'
    return {
      check_id: `scan:${record?._rowKey || Date.now()}`,
      scan_row_key: record?._rowKey,
      element_id: 0,
      element_name: record?._name || getElementDisplayName(record),
      check_status: status,
      checked_time: new Date().toISOString(),
      duration_ms: result?.duration_ms,
      page_url: result?.page_url,
      page_title: result?.page_title,
      error_message: result?.error_message,
      locator_groups: result?.locator_groups || [],
      expected_event_result: {
        configured: false,
        executed: false,
      },
      baseline:
        baselineSnapshot && Object.keys(baselineSnapshot).length ? { after: 'created' } : {},
      selected_result: result,
    }
  }

  function resolveRuntimeResult(result: any) {
    if (!result) return null
    const directList = Array.isArray(result.element_result_list) ? result.element_result_list : []
    if (directList.length) return directList[directList.length - 1]
    const resultDataList = Array.isArray(result.result_data?.element_result_list)
      ? result.result_data.element_result_list
      : []
    if (resultDataList.length) return resultDataList[resultDataList.length - 1]
    const elementResult = Array.isArray(result.element_result) ? result.element_result : []
    if (elementResult.length) return elementResult[elementResult.length - 1]
    return result.selected_result || result.element_result || result
  }

  function savePickedElement() {
    const [locator, locator2, locator3] = normalizePickedLocators(pickedElement.value?.locators)
    if (locator.exp === null || !String(locator.loc || '').trim()) {
      Message.error('请完善第一组主定位的定位类型和定位表达式')
      return
    }
    const incompleteBackup = [locator2, locator3].find(
      (item) => (item.exp !== null || item.loc) && (item.exp === null || !String(item.loc).trim())
    )
    if (incompleteBackup) {
      Message.error('备用定位器需要同时填写定位类型和定位表达式')
      return
    }
    const elementName =
      pickedForm.name || pickedElement.value.text || pickedElement.value.label || '新采集元素'
    pendingBaselineSnapshot.value = pickedElement.value?.baseline_snapshot
    pendingSavedScannedRecord.value = null
    pendingCapturedElementSave.value = true
    elementEditPanelRef.value?.openCreate(props.pageId || '', pickedForm.category || '未分类', {
      name: elementName,
      exp: locator.exp,
      loc: locator.loc,
      sub: locator.sub ?? '',
      exp2: locator2?.exp ?? null,
      loc2: locator2?.loc || '',
      sub2: locator2?.sub ?? '',
      exp3: locator3?.exp ?? null,
      loc3: locator3?.loc || '',
      sub3: locator3?.sub ?? '',
      prompt: elementName,
    })
  }

  async function handleElementSaved(record: any) {
    const snapshot = pendingBaselineSnapshot.value
    const scannedRecord = pendingSavedScannedRecord.value
    const capturedElementSave = pendingCapturedElementSave.value
    pendingBaselineSnapshot.value = null
    pendingSavedScannedRecord.value = null
    pendingCapturedElementSave.value = false
    if (scannedRecord) scannedRecord._saved = true
    if (pendingRecordedElementAction.value) {
      const detail = {
        ...(pendingRecordedElementAction.value.detail || {}),
        ele_name: record?.id,
      }
      updateRecordedAction({
        ...pendingRecordedElementAction.value,
        element_id: record?.id,
        detail,
        status: 'ready',
      })
      pendingRecordedElementAction.value = null
    }
    await saveElementBaselineSnapshot(record?.id, snapshot)
    const hasCapturedBaseline = Boolean(snapshot && Object.keys(snapshot).length)
    const lacksStoredBaseline = Number(record?.ai_heal_status || 0) === 0
    if (capturedElementSave && !hasCapturedBaseline && lacksStoredBaseline) {
      void triggerElementBaselineCheck(record?.id)
    }
    await loadElements()
    emit('element-saved', record)
  }

  function showElementCheckDetail(result: any) {
    if (!result) return
    elementCheckDetail.data = result
    elementCheckDetail.title = `${
      result.check_mode === 'deep' ? '元素深度检测结果' : '元素检测结果'
    } / ${result.element_name || '页面元素'}`
    deepCheckApplied.value = false
    elementCheckDetail.visible = true
  }

  async function applyDeepCheckUpdates() {
    if (deepCheckApplyLoading.value || deepCheckApplied.value) return
    const elementId = elementCheckDetail.data?.element_id
    const checkId = String(elementCheckDetail.data?.check_id || '')
    if (!elementId || !checkId) return
    deepCheckApplyLoading.value = true
    try {
      const res = await putUiElementDeepCheckApply({ element_id: elementId, check_id: checkId })
      deepCheckApplied.value = true
      const slots = res.data?.applied_slots || []
      Message.success(slots.length ? `已写入第 ${slots.join('、')} 组定位` : res.msg)
      await loadElements()
    } finally {
      deepCheckApplyLoading.value = false
    }
  }

  async function saveElementBaselineSnapshot(elementId: any, snapshot: any) {
    if (!elementId || !snapshot || !Object.keys(snapshot).length) return
    try {
      await postUiElementAiSnapshot({
        ...snapshot,
        element: elementId,
        test_env: testEnvValue.value,
      })
    } catch (_) {
      Message.warning('元素已保存，基线采集写入失败')
    }
  }

  async function triggerElementBaselineCheck(elementId: any) {
    if (!elementId || !workspace.workspaceId) return
    try {
      await postUiElementCheck({
        element_id: elementId,
        test_env: testEnvValue.value,
        workspace_id: workspace.workspaceId,
      })
    } catch (_) {
      // 元素已经保存成功，检测/基线补采失败不阻断主流程。
    }
  }

  async function debugStep(
    pageStepDetailId?: number | string,
    overridePageStepId?: number | string
  ) {
    const targetPageStepId = overridePageStepId || props.pageStepId
    if (!targetPageStepId) {
      Message.error('缺少页面步骤ID')
      return false
    }
    if (stepDebugging.value) return false
    stepDebugging.value = true
    recordingTrialRunning.value = Boolean(overridePageStepId)
    let dispatched = false
    try {
      if (!(await ensureWorkspaceReady())) return false
      const executeStep = () =>
        getUiStepsTest(
          targetPageStepId,
          testEnvValue.value as any,
          workspace.workspaceId,
          props.stepControl,
          pageStepDetailId,
          true
        )
      const controlReleased = await livePanelRef.value?.suspendControlForAutomation()
      if (!controlReleased) {
        throw new Error('直播控制权释放超时，请稍后重试')
      }
      let res
      const requestWorkspaceId = workspace.workspaceId
      try {
        res = await executeStep()
      } catch (error: any) {
        if (!isWorkspaceExpiredError(error)) throw error
        const recovered = await recoverExpiredWorkspace(requestWorkspaceId)
        if (!recovered || !workspace.workspaceId) {
          throw new Error('实时工作区恢复失败，请重新打开')
        }
        res = await executeStep()
      }
      Message.success(res.msg)
      dispatched = true
      return true
    } catch (error: any) {
      Message.error(error?.message || error?.msg || '页面步骤调试失败')
      return false
    } finally {
      if (!dispatched) {
        stepDebugging.value = false
        recordingTrialRunning.value = false
        livePanelRef.value?.resumeControlAfterAutomation()
      }
    }
  }

  function isWorkspaceExpiredError(error: any) {
    const message = String(error?.message || error?.msg || '')
    return /实时工作区不存在|实时工作区.*过期|实时工作区与当前页面步骤不匹配/.test(message)
  }

  defineExpose({
    startStepDebug: debugStep,
    refreshElements: loadElements,
    checkElementInWorkspace,
    acceptElementCheckResult,
  })

  function handleStreamReady() {
    if (streamReadyEmitted) return
    streamReadyEmitted = true
    emit('stream-ready')
  }

  function handleStreamConnection(connected: boolean) {
    liveConnected.value = connected
    if (!connected) {
      workspace.idleDeadline = Date.now() + 5 * 60 * 1000
      if (interactionMode.value === 'record' && !recordingPaused.value) {
        recordingPaused.value = true
        recordingPausedByDisconnect = true
      }
      return
    }
    if (recordingPausedByDisconnect && interactionMode.value === 'record') {
      recordingPaused.value = false
    }
    recordingPausedByDisconnect = false
  }

  function handleLiveCommandResult(message: any) {
    const data = message?.data || {}
    if (message?.success === false) {
      if (aiLocator.validating) {
        clearAiLocatorValidationTimer()
        aiLocator.validating = false
        aiLocator.candidates = aiLocator.candidates.map((item: any) => ({
          ...item,
          validation_done: true,
          verified: false,
          error_message: message?.message || '浏览器验证失败',
        }))
      }
      clearScanTimer()
      scanLoading.value = false
      scannedElements.value.forEach((item: any) => {
        item._checking = false
      })
      return
    }
    if (data.element) {
      data.element.locators = normalizePickedLocators(data.element.locators)
      pickedElement.value = data.element
      pickedForm.name = data.element.text || data.element.label || data.element.placeholder || ''
      pickedForm.category = String(props.category || '未分类')
    }
    if (data.recorded_action) appendRecordedAction(data.recorded_action)
    if (Array.isArray(data.passive_actions)) {
      data.passive_actions.forEach((item: any) => {
        const previous = recordedActions.value[recordedActions.value.length - 1]
        const passiveLoc = item?.element?.locators?.[0]?.loc || ''
        const previousLoc = previous?.element?.locators?.[0]?.loc || ''
        if (
          ['select', 'check', 'uncheck'].includes(item.action) &&
          previous?.action === 'click' &&
          passiveLoc &&
          passiveLoc === previousLoc
        ) {
          Object.assign(previous, normalizeRecordedAction({ ...previous, ...item }))
          persistRecordedActions()
          return
        }
        if (
          item.action === 'navigation' &&
          previous?.action === 'navigation' &&
          previous?.url === item.url
        )
          return
        appendRecordedAction(item)
      })
    }
    if (data.element_result) {
      latestElementResult.value = data.element_result
    }
    if (data.scan_check_result) {
      if (applyAiLocatorValidation(data)) return
      latestElementResult.value = data.scan_check_result
      const recordedAction = recordedActions.value.find(
        (item: any) => `recording:${item.client_id}` === data.row_key
      )
      if (recordedAction) {
        recordedAction._checking = false
        recordedAction._checkStatus =
          Number(data.scan_check_result?.status) === 1 ? 'passed' : 'failed'
        recordedAction._checkDuration = data.scan_check_result?.duration_ms
        if (recordedAction._checkStatus === 'passed') Message.success('录制元素检测通过')
        else Message.error(data.scan_check_result?.error_message || '录制元素检测失败')
        emit('element-check-finished')
      }
      const row = scannedElements.value.find((item: any) => item._rowKey === data.row_key)
      if (row) {
        row._checking = false
        row._checkStatus = Number(data.scan_check_result?.status) === 1 ? 'passed' : 'failed'
        row._checkDuration = data.scan_check_result?.duration_ms
        if (data.baseline_snapshot) row.baseline_snapshot = data.baseline_snapshot
        const checkDetail = buildScannedCheckDetail(
          row,
          data.scan_check_result,
          data.baseline_snapshot
        )
        emit('element-check-result', checkDetail)
        showElementCheckDetail(checkDetail)
      }
    }
  }

  function handleWebsocketMessage(event: Event) {
    const message = (event as CustomEvent).detail
    const funcName = message?.data?.func_name
    const result = message?.data?.func_args
    const msg = String(message?.msg || '')
    if (
      !workspace.workspaceId &&
      !workspaceOpening.value &&
      /执行器.*连接|连接.*执行器|执行器.*上线|已连接上测试平台服务器/.test(msg)
    ) {
      scheduleWorkspaceRetry(0)
    }
    if (funcName === 'u_live_workspace_status') {
      const statusWorkspaceId = String(result?.workspace_id || '')
      if (!statusWorkspaceId) return
      if (statusWorkspaceId !== workspace.workspaceId) {
        if (result?.status === 'ready') readyWorkspaceIds.add(statusWorkspaceId)
        else if (result?.status === 'failed') {
          failedWorkspaceMessages.set(
            statusWorkspaceId,
            result?.message || '执行器初始化实时工作区失败'
          )
        }
        return
      }
      if (result?.status === 'ready') {
        workspace.ready = true
        workspace.error = ''
        finishWorkspaceReadyWait(true)
      } else if (result?.status === 'failed') {
        workspace.ready = false
        workspace.error = result?.message || '执行器初始化实时工作区失败'
        finishWorkspaceReadyWait(false)
      } else if (result?.status === 'closed') {
        clearWorkspaceRetryTimer()
        workspaceRequestSeq += 1
        workspace.ready = false
        workspace.workspaceId = ''
        workspace.error = result?.message || '实时工作区已关闭'
        liveVisible.value = false
        Message.info(workspace.error)
      }
      return
    }
    if (funcName === 'u_page_steps') {
      if (!stepDebugging.value) return
      if (props.mode !== 'step' && !recordingTrialRunning.value) return
      if (!result?.workspace_id || String(result.workspace_id) !== workspace.workspaceId) return
      latestElementResult.value = resolveRuntimeResult(result)
      if (result?.is_final) {
        stepDebugging.value = false
        recordingTrialRunning.value = false
        livePanelRef.value?.resumeControlAfterAutomation()
      }
    }
  }

  onMounted(() => {
    workspaceMounted = true
    window.addEventListener('mango:websocket-message', handleWebsocketMessage)
    window.addEventListener('mango:websocket-open', handlePlatformWebsocketOpen)
    openWorkspace()
    restoreRecordedActions()
    restorePageScanTask()
    idleClockTimer = window.setInterval(() => {
      idleNow.value = Date.now()
    }, 1000)
    recordingPollTimer = window.setInterval(() => {
      if (
        interactionMode.value === 'record' &&
        !recordingPaused.value &&
        workspace.ready &&
        livePanelRef.value?.controllingValue
      ) {
        void livePanelRef.value.sendWorkspaceCommand?.('record_poll')
      }
    }, 1500)
  })

  onBeforeUnmount(() => {
    workspaceMounted = false
    workspaceRequestSeq += 1
    window.removeEventListener('mango:websocket-message', handleWebsocketMessage)
    window.removeEventListener('mango:websocket-open', handlePlatformWebsocketOpen)
    clearWorkspaceRetryTimer()
    clearElementCheckTimer()
    clearElementCheckTaskPoll()
    elementCheckSession.cancel()
    clearScanTimer()
    clearAiLocatorValidationTimer()
    finishWorkspaceReadyWait(false)
    if (idleClockTimer) window.clearInterval(idleClockTimer)
    if (recordingPollTimer) window.clearInterval(recordingPollTimer)
    if (workspace.workspaceId) closeUiLiveWorkspace(workspace.workspaceId, true).catch(() => {})
  })
</script>

<style scoped>
  .mango-ui-live-workbench-panel__scan-mode {
    width: 112px;
  }

  .mango-ui-live-workbench-panel {
    display: grid;
    height: 100%;
    min-height: min(760px, calc(100vh - 112px));
    grid-template-columns: minmax(720px, 1fr) clamp(380px, 24vw, 440px);
    column-gap: 0;
    overflow: hidden;
    background: var(--m-bg-soft);
  }
  .mango-ui-live-workbench-panel__stage {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    gap: 8px;
    overflow: hidden;
    padding: 0 4px 0 0;
  }
  .mango-ui-live-workbench-panel__viewer-card {
    display: flex;
    min-width: 0;
    min-height: 400px;
    flex: 1 1 auto;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }
  .mango-ui-live-workbench-panel__viewer-head,
  .mango-ui-live-workbench-panel__scan-head,
  .mango-ui-live-workbench-panel__tools-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex: 0 0 auto;
    min-height: 42px;
    margin-bottom: 0;
    padding: 7px 10px;
    background: var(--m-surface);
  }
  .mango-ui-live-workbench-panel__viewer-head,
  .mango-ui-live-workbench-panel__scan-head {
    border-bottom: 1px solid var(--m-border);
  }
  .mango-ui-live-workbench-panel__tools-head {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
    min-height: auto;
    padding: 0;
    border: 0;
    background: transparent;
  }
  .mango-ui-live-workbench-panel__tools-head .mango-section-actions {
    display: flex;
    width: 100%;
    flex: none;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
  .mango-ui-live-workbench-panel__tools-head h2,
  .mango-ui-live-workbench-panel__tools-head p {
    white-space: nowrap;
  }
  .mango-ui-live-workbench-panel__viewer-head .mango-section-title__main,
  .mango-ui-live-workbench-panel__scan-head .mango-section-title__main,
  .mango-ui-live-workbench-panel__tools-head .mango-section-title__main {
    min-width: 0;
    flex: 1;
  }
  .mango-ui-live-workbench-panel__viewer-head h2,
  .mango-ui-live-workbench-panel__scan-head h2 {
    font-size: 14px;
    line-height: 20px;
  }
  .mango-ui-live-workbench-panel__execution-id {
    color: var(--m-text-3);
    font-size: 12px;
    font-weight: 400;
  }
  .mango-ui-live-workbench-panel__viewer-head p,
  .mango-ui-live-workbench-panel__scan-head p {
    line-height: 16px;
  }
  .mango-ui-live-workbench-panel__viewer-actions {
    display: flex;
    min-width: 0;
    flex: 1;
    justify-content: flex-end;
  }
  .mango-ui-live-workbench-panel__viewer {
    min-width: 0;
    min-height: 0;
    flex: 1;
    overflow: hidden;
  }
  .mango-ui-live-workbench-panel__scan-panel {
    display: flex;
    min-height: 0;
    flex: 0 0 clamp(460px, 46vh, 560px);
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }
  .mango-ui-live-workbench-panel__tools {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 8px;
    overflow: auto;
    padding: 0 0 0 4px;
  }
  .mango-ui-live-workbench-panel__section-head {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 10px;
  }
  .mango-ui-live-workbench-panel__section-head span,
  .mango-section-title p {
    color: var(--m-text-3);
    font-size: 12px;
  }
  .mango-soft-panel {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-bg);
  }
  .mango-ui-live-workbench-panel__summary-card {
    gap: 12px;
  }
  .mango-ui-live-workbench-panel__runtime-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .mango-ui-live-workbench-panel__runtime-group {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-bg-soft);
  }
  .mango-ui-live-workbench-panel__runtime-group-head {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }
  .mango-ui-live-workbench-panel__runtime-group-head strong {
    color: var(--m-text-1);
    font-size: 13px;
    white-space: nowrap;
  }
  .mango-ui-live-workbench-panel__runtime-group-head span {
    max-width: 100%;
    overflow: hidden;
    color: var(--m-text-3);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-ui-live-workbench-panel__page-actions {
    display: flex;
    gap: 8px;
  }
  .mango-ui-live-workbench-panel__picked {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .mango-ui-live-workbench-panel__picked-locator {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }
  .mango-ui-live-workbench-panel__picked-locator-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .mango-ui-live-workbench-panel__picked-locator-title strong {
    color: var(--m-text-1);
    font-size: 13px;
  }
  .mango-ui-live-workbench-panel__picked-locator-title span,
  .mango-ui-live-workbench-panel__picked-locator-fields label > span {
    color: var(--m-text-3);
    font-size: 12px;
  }
  .mango-ui-live-workbench-panel__picked-locator-fields {
    display: grid;
    min-width: 0;
    grid-template-columns: minmax(106px, 0.8fr) minmax(0, 2fr) minmax(72px, 0.65fr);
    gap: 8px;
  }
  .mango-ui-live-workbench-panel__picked-locator-fields label {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }
  .mango-ui-live-workbench-panel__picked-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  .mango-ui-live-workbench-panel__scan-table {
    min-height: 0;
    flex: 1;
    margin: 0;
    overflow-x: hidden;
    overflow-y: auto;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }

  .mango-ui-live-workbench-panel__scan-table :deep(.arco-table-th),
  .mango-ui-live-workbench-panel__scan-table :deep(.arco-table-td) {
    background: var(--m-surface);
  }

  .mango-ui-live-workbench-panel__scan-table :deep(.arco-table-th) {
    height: 46px;
  }

  .mango-ui-live-workbench-panel__scan-text {
    display: block;
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-live-workbench-panel__scan-empty {
    margin: 0;
    padding: 24px 0;
    border: 1px dashed var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }
  .mango-ui-live-workbench-panel__scan-meta {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }
  .mango-ui-live-workbench-panel__scan-meta span {
    color: var(--m-text-3);
    font-size: 12px;
  }
  .mango-ui-live-workbench-panel__scan-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .mango-ui-live-workbench-panel__scan-meta strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-ui-live-workbench-panel__actuator-picker {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .mango-ui-live-workbench-panel__actuator-picker p {
    margin: 0;
    color: var(--m-text-3);
  }
  .mango-ui-live-workbench-panel__actuator-option {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .mango-ui-live-workbench-panel__actuator-option span {
    color: var(--m-text-3);
  }
  .mango-ui-live-workbench-panel__actuator-actions {
    justify-content: flex-end;
  }
</style>
