<template>
  <TableBody
    ref="tableBody"
    :embedded="embedded"
    :show-embedded-header="embedded && !compact"
    :class="[
      'page-steps-workbench-page',
      'mango-detail-workbench-page',
      {
        'page-steps-workbench-page--compact': compact,
        'page-steps-workbench-page--embedded-scroll': embedded && !compact,
      },
    ]"
  >
    <template v-if="!compact" #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ stepsTitle }}</div>
          <div class="mango-detail-subtitle">
            编排页面步骤、维护节点配置，并查看最近一次调试结果
          </div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button v-permission="'ui.page_steps:debug'" size="small" :loading="browserOpening" @click="onOpenStepBrowser" data-testid="qa-views-uitest-page-steps-details-button-打开浏览器">
            <template #icon><icon-desktop /></template>
            打开浏览器
          </a-button>
          <a-button v-permission="'ui.page_steps:debug'" size="small" status="success" :loading="caseRunning" @click="onRunCase" data-testid="qa-views-uitest-page-steps-details-button-调试">
            调试
          </a-button>
          <a-button
            size="small"
            type="primary"
            :loading="liveWorkbenchOpening"
            @click="toggleStepLiveWorkbench"
          >
            <template #icon><icon-desktop /></template>
            {{ liveWorkbenchVisible ? '收起工作台' : '实时画面' }}
          </a-button>
          <a-button
            size="small"
            type="primary"
            @click="stepCachePanel.visible = true"
            data-testid="qa-views-uitest-page-steps-details-button-缓存数据"
          >
            缓存数据
          </a-button>
          <a-button
            v-if="!caseInputMode"
            size="small"
            @click="openPageElementsPanel"
          >
            页面元素
          </a-button>
          <VariableReferencePanel />
          <a-button class="mango-back-button" size="small" @click="doResetSearch" data-testid="qa-views-uitest-page-steps-details-button-返回">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <div
        :class="[
          'steps-workbench',
          {
            'mango-detail-workbench': !compact,
            'mango-detail-workbench--fill': !compact,
          },
        ]"
      >
        <FlowChart
          ref="flowChartRef"
          class="steps-flow-area"
          :flow-data="flowData"
          :table-data="data.dataList"
          :node-types="nodeTypes"
          :readonly="caseInputMode"
          :compact="compact"
          :show-step-detail-action="caseInputMode"
          :show-cache-data-action="caseInputMode"
          :allow-drop="!caseInputMode"
          :healing-enabled="Boolean(currentStepRecord.healing_enabled)"
          :healing-goal="currentStepRecord.goal || ''"
          :healing-pending-review-count="pendingHealingReviewNodes.length"
          :healing-review-confirming="healingReviewConfirming"
          :result-data="data.result_data"
          :step-control="stepControl"
          :flow-saving="flowSaving"
          :flow-save-status="flowSaveStatus"
          :debug-status-text="stepStatusText"
          :debug-status-type="stepStatusType"
          :debug-running="debugRunning"
          :decision-draft="decisionDraft"
          :draft-node-ids="draftNodeIds"
          @node-click="onNodeClick"
          @node-select="onNodeSelect"
          @flow-change="onFlowChange"
          @edge-delete="onEdgeDelete"
          @node-delete="onNodeDelete"
          @node-duplicate="onNodeDuplicate"
          @canvas-beautify="beautifyCanvas"
          @canvas-save="saveFlow"
          @control-change="onStepControlChange"
          @open-step-detail="emit('openPageStepDetail')"
          @open-cache-data="emit('openCacheData')"
          @open-step-healing="healingPanelVisible = true"
          @confirm-healing-review="confirmPendingStepHealing"
        />

        <aside class="inspector-panel">
          <div class="panel-head inspector-head">
            <div>
              <div class="panel-title">节点配置</div>
              <div class="panel-subtitle">
                {{ selectedNode ? selectedNodeDescription : '选择画布节点后维护配置' }}
              </div>
            </div>
            <div class="inspector-head-actions">
              <a-button
                v-if="selectedNodeSupportsSingleStep && !caseInputMode"
                size="small"
                status="success"
                :loading="singleStepRunning"
                :disabled="
                  !selectedConfigSaved ||
                  configEditing ||
                  caseRunning ||
                  (debugRunning && !singleStepRunning)
                "
                @click="onRunSelectedNode" data-testid="qa-views-uitest-page-steps-details-button-单步调试"
              >
                单步调试
              </a-button>
            </div>
          </div>

          <Scrollbar always class="inspector-content">
            <div v-if="selectedNode" class="node-details">
              <section class="inspector-section node-section-card">
                <div class="node-section-head">
                  <div class="mango-section-title">节点信息</div>
                  <a-space v-if="hasSelectedNodeElement" size="mini">
                    <a-button
                      size="mini"
                      type="outline"
                      :loading="elementEditLoading"
                      @click="openSelectedElementEditPanel" data-testid="qa-views-uitest-page-steps-details-button-查看元素"
                    >
                      查看元素
                    </a-button>
                    <a-button
                      v-if="!caseInputMode"
                      size="mini"
                      type="outline"
                      :loading="elementDeepCheckLoading"
                      @click="runSelectedElementDeepCheck"
                    >
                      深度检测
                    </a-button>
                    <a-button
                      size="mini"
                      type="outline"
                      :loading="elementAiHealLoading"
                      @click="openSelectedElementAiHeal"
                    >
                      AI自愈
                    </a-button>
                  </a-space>
                </div>
                <div class="node-summary-grid">
                  <div>
                    <span>步骤ID</span>
                    <strong>{{ data.selectData.id || '-' }}</strong>
                  </div>
                  <div>
                    <span>类型</span>
                    <strong>{{ getNodeTypeLabel(data.selectData.type) }}</strong>
                  </div>
                  <div>
                    <span>方法</span>
                    <strong>{{ getMethodLabel(data.selectData.ope_key) }}</strong>
                  </div>
                  <div>
                    <span>参数数</span>
                    <strong>{{ getConfigParamCount(data.selectData) }}</strong>
                  </div>
                  <div
                    v-if="getElementName(data.selectData.ele_name) !== '-'"
                    class="node-summary-wide"
                  >
                    <span>元素名称</span>
                    <strong>{{ getElementName(data.selectData.ele_name) }}</strong>
                  </div>
                  <div
                    v-if="getConditionSummary(data.selectData.condition_value) !== '-'"
                    class="node-summary-wide"
                  >
                    <span>条件</span>
                    <strong>{{ getConditionSummary(data.selectData.condition_value) }}</strong>
                  </div>
                </div>
                <div v-if="getConfigParamSummary(data.selectData).length" class="node-param-list">
                  <div
                    v-for="param in getConfigParamSummary(data.selectData)"
                    :key="param.key"
                    class="node-param-item"
                  >
                    <span>{{ param.label }}</span>
                    <strong>{{ param.value }}</strong>
                  </div>
                </div>
              </section>

              <section class="inspector-section node-section-card config-editor">
                <div v-if="data.formItems.length > 0 || data.type === 2">
                  <div class="node-section-head">
                    <div class="mango-section-title">编辑配置</div>
                    <a-space :size="6">
                      <a-button v-permission="'ui.page_steps:create'"
                        v-if="data.type === 2 && !configFormReadonly"
                        size="mini"
                        @click="addSqlOperation" data-testid="qa-views-uitest-page-steps-details-button-新增操作"
                      >
                        新增操作
                      </a-button>
                      <a-button
                        v-if="!caseInputMode || hasCaseEditableConfigItems"
                        size="mini"
                        type="primary"
                        :loading="formSaving"
                        @click="handleConfigAction"
                      >
                        {{ configActionText }}
                      </a-button>
                    </a-space>
                  </div>
                  <TipMessage
                    v-if="caseInputMode"
                    message="Case 中仅允许修改节点入参；流程、节点、元素和执行方法均继承页面步骤，不可在此修改。"
                    margin-bottom="8px"
                  />
                  <TipMessage
                    v-if="conditionTipMessage"
                    :message="conditionTipMessage"
                    margin-bottom="8px"
                  />

                  <DataSourceOperationList
                    v-if="data.type === 2"
                    ref="dataSourceOperationListRef"
                    :data-list="sqlOperationRows"
                    :datasource-options="datasourceAliasOptions"
                    :project-product-id="currentProjectProductId"
                    :test-env="userStore.selected_environment"
                    :show-environment="false"
                    :disabled="configFormReadonly"
                    operation-field="sql"
                    key-field="key_list"
                    key-label="缓存 Key"
                    key-placeholder="请输入查询结果缓存 Key"
                    :on-delete-item="removeSqlOperation"
                  />

                  <UiStepNodeConfigForm
                    v-else
                    :items="visibleFormItems"
                    :operation-options="useSelectValue.getOperationOptions(currentPageType)"
                    :assertion-options="useSelectValue.getAssertionOptions(currentPageType)"
                    :element-options="data.uiPageName"
                    :element-cascader-options="elementCascaderOptions"
                    :file-options="uiTestFileOptions"
                    :file-loading="uiTestFileLoading"
                    :datasource-options="sqlAssertionDatasourceOptions"
                    :is-item-disabled="isConfigItemDisabled"
                    :is-item-inherited="isCaseInheritedConfigItem"
                    :get-inherited-value="getCaseInheritedConfigValue"
                    class="node-config-form"
                    @method-change="upDataOpeValue"
                    @element-change="onElementCascaderChange"
                  >
                    <ExcelAssertionEditor
                      v-if="isExcelAssertionMethod"
                      ref="excelAssertionEditorRef"
                      :method-key="selectedMethodKey"
                      :method-label="selectedMethodDefinition?.label"
                      :parameters="selectedMethodDefinition?.parameter || []"
                      :actual-value="excelActualFormItem?.value"
                      :expect-value="excelExpectFormItem?.value"
                      :disabled="configFormReadonly"
                      :file-options="uiTestFileOptions"
                      :file-loading="uiTestFileLoading"
                      @update:actual-value="updateExcelFormItem('actual', $event)"
                      @update:expect-value="updateExcelFormItem('expect', $event)"
                    />
                  </UiStepNodeConfigForm>
                </div>
              </section>

              <section class="inspector-section node-section-card">
                <a-spin
                  :key="runtimeResultRenderRevision"
                  :loading="latestResultLoading"
                  class="mango-ui-step-result-loading"
                >
                  <UiStepRuntimeResult
                    frameless
                    :result="data.selectResultData"
                    :fallback-ope-key="data.selectData.ope_key"
                    :fallback-element-name="getElementName(data.selectData.ele_name)"
                    :fallback-element="data.selectData.ele_name"
                  />
                </a-spin>
              </section>
            </div>
            <div v-else class="no-selection">
              <div class="no-selection-title">暂未选择节点</div>
              <div class="no-selection-desc"
                >在左侧画布中点击一个节点后，这里会显示元素、操作和断言配置。</div
              >
            </div>
          </Scrollbar>
        </aside>
      </div>
      <section
        v-if="liveWorkbenchVisible"
        ref="liveWorkbenchSectionRef"
        class="steps-live-debug-area"
      >
        <UiLiveWorkbenchPanel
          ref="liveWorkbenchPanelRef"
          class="steps-live-debug-panel"
          mode="step"
          :page-id="currentPageId"
          :page-url="currentPageInfo.url"
          :page-step-id="currentPageStepsId"
          :test-env="userStore.selected_environment"
          :category="'未分类'"
          :operation-options="useSelectValue.getOperationOptions(currentPageType)"
          :page-type="currentPageType"
          :project-product-id="currentProjectProductId"
          :step-control="stepControl"
          @stream-ready="handleStepLiveReady"
          @element-check-started="handleStepElementCheckStarted"
          @element-check-result="handleStepElementCheckResult"
          @element-saved="handleStepWorkbenchElementSaved"
        />
      </section>
    </template>
  </TableBody>
  <BaseSidePanel
    :visible="pageElementsPanel.visible"
    title="页面元素"
    page-description="从页面步骤详情的页面元素入口打开，当前展示该页面下的完整元素管理内容"
    width="80%"
    mode="page"
    @update:visible="handlePageElementsPanelVisible"
  >
    <div class="mango-ui-step-page-elements-panel">
      <PageElements
        v-if="pageElementsPanel.visible && currentPageId"
        :key="String(currentPageId)"
        embedded
        :page-id="currentPageId"
        @close="closePageElementsPanel"
      />
    </div>
  </BaseSidePanel>
  <BaseSidePanel
    :visible="stepCachePanel.visible"
    title="步骤缓存数据"
    width="50%"
    @update:visible="
      (val) => {
        stepCachePanel.visible = val
      }
    "
    @cancel="stepCachePanel.visible = false"
  >
    <div class="mango-ui-step-cache-panel">
      <section class="mango-ui-step-cache-section">
        <div class="mango-ui-step-cache-section__head">
          <strong>当前可用缓存变量</strong>
          <span>
            {{ getSelectedNodeTitle() }} · 步骤执行完成后的运行时缓存
          </span>
        </div>
        <JsonDisplay
          :data="currentStepCacheData"
          :show-drawer-button="false"
          :default-expanded="true"
        />
      </section>
    </div>
  </BaseSidePanel>
  <UiElementEditPanel
    ref="elementEditPanelRef"
    :operation-options="useSelectValue.getOperationOptions(currentPageType)"
    @saved="handleElementSaved"
  />
  <UiElementAiHealPanel
    ref="elementAiHealPanelRef"
    :test-env="userStore.selected_environment"
    @applied="handleElementSaved"
  />
  <UiElementDeepCheckVariablesDialog ref="deepCheckVariablesDialogRef" />
  <UiElementCheckResultPanel
    v-model:visible="elementCheckResult.visible"
    :title="elementCheckResult.title"
    :data="elementCheckResult.data"
    :apply-loading="elementCheckApplyLoading"
    :applied="elementCheckApplied"
    @apply="applyStepElementDeepCheckUpdates"
  />
  <UiPageStepHealingPanel
    v-if="healingPanelVisible"
    :visible="true"
    :page-step-id="currentPageStepsId"
    :record="currentStepRecord"
    :element-options="data.uiPageName"
    @update:visible="healingPanelVisible = $event"
    @changed="doRefreshSteps(currentPageStepsId)"
  />
</template>
<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { IconDesktop } from '@arco-design/web-vue/es/icon'
  import FlowChart from './FlowChart.vue'
  import { FlowData, UINode, UIEdge, UiStepControl } from '@/types/components'
  import type { UiPageStepsDetailPayload } from '@/types/ui-test/case'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import {
    formItemsElement4,
    formItemsElementAss,
    formItemsElementCode,
    formItemsElementCondition,
    formItemsElementKey,
    formItemsElementOpe,
    formItemsForceWait,
  } from './config'
  import {
    deleteUiPageStepsDetailed,
    getUiPageStepsDetailed,
    getUiPageStepsDetailedById,
    postUiPageStepNodeCopy,
    postUiPageStepsDetailed,
  } from '@/api/uitest/page-steps-detailed'
  import {
    getUiSteps,
    getUiStepsTest,
    postUiPageStepHealApply,
    postUiPageStepOpenBrowser,
    putUiSteps,
  } from '@/api/uitest/page-steps'
  import { putUiCaseStepsDetailed } from '@/api/uitest/case-steps-detailed'
  import {
    getUiUiElementName,
    postUiElementCheck,
    putUiElementDeepCheckApply,
  } from '@/api/uitest/element'
  import { getUserFile } from '@/api/system/file_data'
  import useUserStore from '@/store/modules/user'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import { useProject } from '@/store/modules/get-project'
  import UiStepNodeConfigForm from '@/components/business/UiStepNodeConfigForm.vue'
  import ExcelAssertionEditor from '@/components/forms/ExcelAssertionEditor.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import UiElementEditPanel from '@/components/business/UiElementEditPanel.vue'
  import UiElementAiHealPanel from '@/components/business/UiElementAiHealPanel.vue'
  import UiElementDeepCheckVariablesDialog from '@/components/business/UiElementDeepCheckVariablesDialog.vue'
  import UiElementCheckResultPanel from '@/components/business/UiElementCheckResultPanel.vue'
  import UiPageStepHealingPanel from '@/components/business/UiPageStepHealingPanel.vue'
  import UiLiveWorkbenchPanel from '@/components/business/UiLiveWorkbenchPanel.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { createUiElementCheckSession } from '@/utils/ui-element-check-session.mjs'
  import UiStepRuntimeResult from '@/components/reports/UiStepRuntimeResult.vue'
  import { Scrollbar } from '@/components/Scrollbar'
  import PageElements from '@/views/uitest/page/elements/index.vue'
  import { useUiLiveWorkbench } from '@/hooks/use-ui-live-workbench'
  import { getExecutionResultLatestResolved } from '@/api/system/execution_result'
  import { getActiveExecutorTasks, getExecutorTask } from '@/api/system/executor-task'
  import {
    clearExecutorTaskObservation,
    loadExecutorTaskObservation,
    saveExecutorTaskObservation,
  } from '@/utils/executor-task-observer.mjs'
  import {
    buildUiUploadFileCascaderOptions,
    getUiUploadFileValueFromCascader,
    isUiUploadFileParam,
    normalizeUiUploadFileValue,
  } from '@/utils/ui-test-file'

  const excelAssertionEditorRef = ref<{ validate: () => boolean } | null>(null)
  const elementEditPanelRef = ref<InstanceType<typeof UiElementEditPanel> | null>(null)
  const elementAiHealPanelRef = ref<InstanceType<typeof UiElementAiHealPanel> | null>(null)
  const deepCheckVariablesDialogRef = ref<InstanceType<
    typeof UiElementDeepCheckVariablesDialog
  > | null>(null)
  const liveWorkbenchPanelRef = ref<{
    startStepDebug: (pageStepDetailId?: number | string) => Promise<boolean>
    checkElementInWorkspace: (
      record: any,
      checkMode?: 'normal' | 'deep',
      runtimeVariables?: Record<string, string>
    ) => Promise<boolean | string>
  } | null>(null)
  const elementEditLoading = ref(false)
  const elementDeepCheckLoading = ref(false)
  const elementDeepCheckId = ref('')
  const elementDeepCheckTaskId = ref('')
  const elementDeepCheckElementId = ref<number | string | null>(null)
  const elementDeepCheckSession = createUiElementCheckSession()
  let elementDeepCheckToken: number | null = null
  let elementDeepCheckTimer: ReturnType<typeof setTimeout> | null = null
  let elementDeepCheckPollTimer: ReturnType<typeof setTimeout> | null = null
  let elementDeepCheckPolling = false
  const elementAiHealLoading = ref(false)
  const elementCheckApplyLoading = ref(false)
  const elementCheckApplied = ref(false)
  const healingPanelVisible = ref(false)
  const healingReviewConfirming = ref(false)
  const elementCheckResult = reactive({
    visible: false,
    title: '元素深度检测结果',
    data: null as any,
  })

  const flowChartRef = ref()
  const selectedNode = ref<UINode | null>(null)
  const configText = ref('')

  const flowData = ref<FlowData>({
    nodes: [],
    edges: [],
  })
  const stepControl = ref<UiStepControl>({
    close_after_execution: false,
    before_wait_seconds: 1,
    after_wait_seconds: 1,
    close_live_after_execution: false,
  })
  const currentStepRecord = ref<any>({})
  const enumStore = useEnum()
  const pageData = usePageData()
  const userStore = useUserStore()
  const useSelectValue = useSelectValueStore()
  const projectInfo = useProject()
  const {
    visible: liveWorkbenchVisible,
    opening: liveWorkbenchOpening,
    sectionRef: liveWorkbenchSectionRef,
    open: openStepLiveWorkbench,
    toggle: toggleStepLiveWorkbench,
  } = useUiLiveWorkbench(() => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return false
    }
    return true
  })

  const props = withDefaults(
    defineProps<{
      pageStepsId?: string | number
      pageId?: string | number
      pageType?: string | number
      embedded?: boolean
      compact?: boolean
      caseInputMode?: boolean
      caseId?: string | number
      caseStepId?: string | number
      caseData?: any[]
      caseResult?: any
      refreshToken?: number
    }>(),
    {
      pageStepsId: '',
      pageId: '',
      pageType: '',
      embedded: false,
      compact: false,
      caseInputMode: false,
      caseId: '',
      caseStepId: '',
      caseData: () => [],
      caseResult: null,
      refreshToken: 0,
    }
  )
  const emit = defineEmits<{
    (event: 'close'): void
    (event: 'caseDataSaved', value: any[]): void
    (event: 'openPageStepDetail'): void
    (event: 'openCacheData'): void
  }>()
  const route = useRoute()
  const PYTHON_CODE_TEMPLATE = `def func(self):
  key = self.test_data.get_cache("key")
  print(key)`

  // 节点类型定义
  const nodeTypes = [
    { type: 0, label: '元素操作', color: 'var(--m-node-element)' },
    { type: 1, label: '断言操作', color: 'var(--m-node-assertion)' },
    { type: 2, label: '数据库操作', color: 'var(--m-node-sql)' },
    { type: 3, label: '自定义变量', color: 'var(--m-node-custom)' },
    { type: 4, label: '条件判断', color: 'var(--m-node-condition)' },
    { type: 5, label: 'python代码', color: 'var(--m-node-python)' },
    { type: 6, label: '强制等待', color: 'var(--m-node-wait)' },
  ]

  const selectedNodeTypeLabel = computed(() => {
    if (!selectedNode.value) return ''
    return nodeTypes.find((item) => item.type === selectedNode.value?.type)?.label || '未知节点'
  })
  const selectedNodeDescription = computed(() => {
    if (!selectedNode.value) return ''
    const descriptionMap: Record<number, string> = {
      0: '元素操作节点，请配置对元素的操作信息。',
      1: '断言操作节点，请配置断言对象、断言方法和期望值。',
      2: '数据库操作节点，请配置逻辑数据源、执行内容和缓存变量。',
      3: '自定义变量节点，请配置变量名称和变量值。',
      4: '条件判断节点，请配置判断方法和分支条件。',
      5: 'python代码节点，请配置需要执行的自定义代码。',
      6: '强制等待节点，请配置执行器暂停执行的时长。',
    }
    return descriptionMap[Number(selectedNode.value.type)] || '请配置当前节点的执行信息。'
  })

  const currentPageStepsId = computed(
    () => props.pageStepsId || route.query.id || pageData.record?.id
  )
  const currentPageId = computed(
    () =>
      props.pageId ||
      route.query.pageId ||
      currentStepRecord.value?.page?.id ||
      currentStepRecord.value?.page ||
      ''
  )
  const currentPageInfo = computed(() => {
    const page = currentStepRecord.value?.page
    if (page && typeof page === 'object') return page
    return {
      id: currentPageId.value,
      name: '',
      url: '',
    }
  })
  const currentPageType = computed(() =>
    String(
      props.pageType ||
        route.query.pageType ||
        currentStepRecord.value?.project_product?.ui_client_type ||
        '0'
    )
  )
  const currentProjectProductId = computed(
    () =>
      currentStepRecord.value?.project_product?.id ||
      currentStepRecord.value?.project_product ||
      pageData.record?.project_product?.id ||
      pageData.record?.project_product ||
      ''
  )
  const stepsTitle = computed(() => {
    const record = currentStepRecord.value || {}
    const id = record.id || currentPageStepsId.value || '-'
    const name = record.name || pageData.record?.name || '-'
    return `页面步骤工作台 / ${id} / ${name}`
  })
  const pendingHealingReviewNodes = computed(() =>
    (flowData.value.nodes || []).filter((node: any) => {
      const config = node?.config || {}
      return config.ai_healed && config.ai_review_status !== 'confirmed'
    })
  )
  const pendingHealingRecordIds = computed(() =>
    Array.from(
      new Set(
        pendingHealingReviewNodes.value
          .map((node: any) => node?.config?.ai_heal_record_id)
          .filter((recordId: any) => recordId !== null && recordId !== undefined && recordId !== '')
          .map(String)
      )
    )
  )
  const elementCascaderOptions = computed(() => buildElementCascaderOptions(data.uiPageName))

  const data: any = reactive({
    dataList: [],
    selectData: {}, // 选择的节点数据
    uiPageName: [], // 元素名称
    type: 0, // 点击的节点类型
    condition: 0, // 上一个节点是否是判断类型
    conditionId: 0, // 上一个节点是否是判断类型
    conditionNodeId: '',
    result_data: { element_result_list: [] }, // 测试结果数据
    selectResultData: {}, // 选择的节点数据
    formItems: [], // 表单数据
    isConditionExpect: true,
    isAdd: false,
  })
  const caseRunning = ref(false)
  const browserOpening = ref(false)
  const singleStepRunning = ref(false)
  const debugRunning = ref(false)
  const debugCompleted = ref(false)
  const debugRefreshError = ref(false)
  const debugStartedAt = ref(0)
  const debugBaselineResultId = ref<number | string | null>(null)
  const currentDebugSlotId = ref('')
  const debugExpectedNodeCount = ref(0)
  const debugPollFailures = ref(0)
  const latestResultLoading = ref(false)
  const runtimeResultRenderRevision = ref(0)
  let debugPollTimer: ReturnType<typeof setTimeout> | null = null
  const DEBUG_POLL_INTERVAL_MS = 2000
  const DEBUG_POLL_MAX_BACKOFF_MS = 10000
  const currentDebugTaskId = ref('')
  let debugCompletedTimer: ReturnType<typeof setTimeout> | null = null
  let debugPollRequesting = false
  const flowSaving = ref(false)
  const flowSaveStatus = ref<'saved' | 'dirty' | 'saving' | 'error'>('saved')
  const formSaving = ref(false)
  const dataSourceOperationListRef = ref<{ validate: () => boolean } | null>(null)
  const sqlOperationRows = ref<any[]>([])
  const datasourceAliasOptions = ref<any[]>([])
  const sqlAssertionDatasourceOptions = computed(() =>
    datasourceAliasOptions.value.filter((item: any) => [0, 1, 2].includes(Number(item.dbType)))
  )
  const configEditing = ref(false)
  const nodeDuplicating = ref(false)
  const nodeFormDrafts = reactive(new Map<string, Record<string, any>>())
  let flowRevision = 0
  let savedFlowRevision = 0
  let flowSaveTimer: ReturnType<typeof setTimeout> | null = null
  let flowSavePromise: Promise<void> | null = null
  const uiTestFileOptions = ref<any[]>([])
  const uiTestFileLoading = ref(false)
  const stepCachePanel = reactive({
    visible: false,
  })
  const pageElementsPanel = reactive({
    visible: false,
  })
  const currentStepCacheData = computed(() =>
    normalizeRuntimeObject(data.result_data?.cache_data)
  )
  const selectedConfigSaved = computed(() =>
    Boolean(data.selectData?.id || selectedNode.value?.config?.id)
  )
  const hasSelectedNodeElement = computed(() => {
    if (!data.selectData?.id) return false
    if (getElementIdFromCascader(data.selectData?.ele_name)) return true
    // Case 缓存只保存页面步骤绑定元素的名称；真正操作时仍按步骤明细 ID
    // 读取最新元素，兼容存量 Case 缓存且避免仅因缺少元素 ID 隐藏操作入口。
    return props.caseInputMode && getElementName(data.selectData?.ele_name) !== '-'
  })
  const selectedNodeSupportsSingleStep = computed(() =>
    [0, 1, 2, 3, 5, 6].includes(Number(selectedNode.value?.type))
  )
  const configFormReadonly = computed(() => selectedConfigSaved.value && !configEditing.value)
  const configActionText = computed(() => (configFormReadonly.value ? '编辑' : '保存'))
  const hasCaseEditableConfigItems = computed(
    () => data.type === 2 || data.formItems.some((item: any) => !isCaseInheritedConfigItem(item))
  )

  function isCaseInheritedConfigItem(item: any) {
    if (!props.caseInputMode) return false
    const key = String(item?.key || '')
    return (
      key === 'ope_key' ||
      key === 'ele_name' ||
      key === 'locating' ||
      key === 'actual' ||
      item?.type === 'element-cascader' ||
      (item?.type === 'cascader' && ['元素操作', '断言操作', '判断方法'].includes(item?.label))
    )
  }

  function getCaseInheritedConfigValue(item: any) {
    if (String(item?.key || '') === 'ope_key') {
      return getMethodLabel(item?.value || data.selectData?.ope_key)
    }
    const elementName = getElementName(data.selectData?.ele_name)
    if (elementName !== '-') return elementName
    return getElementName(item?.value)
  }

  function isConfigItemDisabled(item: any) {
    if (configFormReadonly.value) return true
    if (!props.caseInputMode) return false
    return isCaseInheritedConfigItem(item)
  }
  const selectedMethodKey = computed(
    () =>
      data.formItems.find((item: any) => item.key === 'ope_key')?.value ||
      data.selectData?.ope_key ||
      ''
  )
  const selectedMethodDefinition = computed(() =>
    useSelectValue.findItemByValue(selectedMethodKey.value)
  )
  const isExcelAssertionMethod = computed(() =>
    String(selectedMethodKey.value || '').startsWith('assert_excel_')
  )
  const excelActualFormItem = computed(() =>
    data.formItems.find((item: any) => item.key === 'actual-ope_value')
  )
  const excelExpectFormItem = computed(() =>
    data.formItems.find((item: any) => item.key === 'expect-ope_value')
  )
  const visibleFormItems = computed(() => {
    if (!isExcelAssertionMethod.value) return data.formItems
    return data.formItems.filter(
      (item: any) => !['actual-ope_value', 'expect-ope_value'].includes(item.key)
    )
  })

  function updateExcelFormItem(field: 'actual' | 'expect', value: string) {
    const item = field === 'actual' ? excelActualFormItem.value : excelExpectFormItem.value
    if (item) item.value = value
  }
  const selectedMethodRequiresBranchValue = computed(() =>
    (useSelectValue.findItemByValue(selectedMethodKey.value)?.parameter || []).some(
      (item: any) => item.f === 'expect'
    )
  )
  const decisionDraft = computed(() => ({
    nodeId: Number(selectedNode.value?.type) === 4 ? selectedNode.value?.id || '' : '',
    opeKey: Number(selectedNode.value?.type) === 4 ? selectedMethodKey.value : '',
  }))
  const draftNodeIds = computed(() => {
    const ids = new Set(nodeFormDrafts.keys())
    if (configEditing.value && selectedNode.value?.id) {
      ids.add(selectedNode.value.id)
    }
    return Array.from(ids)
  })
  const conditionTipMessage = computed(() => {
    if (data.condition) {
      return data.isAdd
        ? '请输入当前分支的判断值；判断成立时将执行该分支。'
        : '上一个判断节点返回 True 时走第一条线，返回 False 时走第二条线。'
    }
    if (data.type !== 4 || !selectedMethodKey.value) return ''
    return selectedMethodRequiresBranchValue.value
      ? '该方法需要判断值。保存判断节点后，请点击每个后续分支节点填写对应的判断值。'
      : '该方法无需填写判断值：成立时走 True 分支，不成立时走 False 分支。'
  })

  function openPageElementsPanel() {
    if (!currentPageId.value) {
      Message.warning('当前页面步骤未绑定页面')
      return
    }
    pageElementsPanel.visible = true
  }

  function closePageElementsPanel() {
    pageElementsPanel.visible = false
    getEleName()
  }

  function handlePageElementsPanelVisible(visible: boolean) {
    if (visible) {
      pageElementsPanel.visible = true
      return
    }
    closePageElementsPanel()
  }
  const runtimeResultList = computed(() =>
    Array.isArray(data.result_data?.element_result_list) ? data.result_data.element_result_list : []
  )
  const executableNodeCount = computed(() => {
    const savedNodeCount = flowData.value.nodes.filter((node) => node.config?.id).length
    return savedNodeCount || data.dataList.length || 0
  })
  const stepStatusText = computed(() => {
    if (debugRefreshError.value) return '结果刷新异常，正在重试'
    if (debugRunning.value) {
      return `调试中 · 已回传 ${runtimeResultList.value.length}/${debugExpectedNodeCount.value || '-'}`
    }
    const status = Number(
      props.caseInputMode ? props.caseResult?.status : currentStepRecord.value?.status
    )
    if (status === 1) return '成功'
    if (status === 0) return '失败'
    if (status === 3) return '进行中'
    if (status === 2) return '待开始'
    if (debugCompleted.value) return '已完成'
    return '未执行'
  })
  const stepStatusType = computed(() => {
    if (debugRefreshError.value) return 'warning'
    if (debugRunning.value) return 'running'
    const status = Number(
      props.caseInputMode ? props.caseResult?.status : currentStepRecord.value?.status
    )
    if (status === 1) return 'done'
    if (status === 0) return 'failed'
    if (status === 3) return 'running'
    if (status === 2) return 'pending'
    if (debugCompleted.value) return 'done'
    return 'pending'
  })

  // 美化画布布局
  const beautifyCanvas = () => {
    if (flowData.value.nodes.length === 0) {
      Message.warning('画布中没有节点')
      return
    }

    // 调用 FlowChart 组件的美化方法
    if (flowChartRef.value && flowChartRef.value.beautifyLayout) {
      flowChartRef.value.beautifyLayout()
      Message.success('画布已美化，正在自动保存')
    }
  }

  function clearFlowSaveTimer() {
    if (!flowSaveTimer) return
    clearTimeout(flowSaveTimer)
    flowSaveTimer = null
  }

  function markFlowSaved(revision = flowRevision) {
    savedFlowRevision = revision
    flowSaveStatus.value = flowRevision === savedFlowRevision ? 'saved' : 'dirty'
  }

  function scheduleFlowSave() {
    clearFlowSaveTimer()
    flowSaveTimer = setTimeout(() => {
      flowSaveTimer = null
      void persistFlow(false)
    }, 1000)
  }

  function persistFlow(manual: boolean): Promise<void> {
    if (props.caseInputMode) return Promise.resolve()
    if (!currentPageStepsId.value) return Promise.resolve()
    if (flowSaving.value && flowSavePromise) {
      return flowSavePromise.then(() => {
        if (flowRevision !== savedFlowRevision) return persistFlow(manual)
      })
    }
    clearFlowSaveTimer()
    const savingRevision = flowRevision
    flowSaving.value = true
    flowSaveStatus.value = 'saving'
    const value = {}
    value['id'] = currentPageStepsId.value
    value['flow_data'] = normalizeStepFlowData(flowData.value)
    flowSavePromise = putUiSteps(value)
      .then((res) => {
        if (savingRevision === flowRevision) {
          markFlowSaved(savingRevision)
        } else {
          flowSaveStatus.value = 'dirty'
          scheduleFlowSave()
        }
        if (manual) Message.success(res.msg)
      })
      .catch((error) => {
        flowSaveStatus.value = 'error'
        console.log(error)
      })
      .finally(() => {
        flowSaving.value = false
        flowSavePromise = null
        if (flowSaveStatus.value === 'dirty') scheduleFlowSave()
      })
    return flowSavePromise
  }

  const saveFlow = () => {
    void persistFlow(true)
  }

  async function ensureFlowSavedForRun() {
    if (
      flowSaveStatus.value !== 'saved' ||
      flowRevision !== savedFlowRevision ||
      flowSaving.value
    ) {
      await persistFlow(false)
    }
    if (flowSaveStatus.value === 'saved' && flowRevision === savedFlowRevision) return true
    Message.error('画布尚未保存成功，请点击“重试保存”后再调试')
    return false
  }

  function setSelectData(node: UINode) {
    data.selectData = {
      precondition: { operator: 'all', conditions: [] },
      postcondition: { operator: 'all', conditions: [] },
    }
    data.dataList.forEach((item: any) => {
      if (String(item.id) === String(node.config?.id)) {
        data.selectData = {
          ...item,
          precondition: item.precondition?.conditions
            ? cloneDraftValue(item.precondition)
            : { operator: 'all', conditions: [] },
          postcondition: item.postcondition?.conditions
            ? cloneDraftValue(item.postcondition)
            : { operator: 'all', conditions: [] },
        }
      }
    })
    syncSelectedResultData()
  }

  function syncSelectedResultData() {
    const selectedStepId = data.selectData?.id
    if (selectedStepId === undefined || selectedStepId === null) {
      data.selectResultData = {}
      return
    }
    data.selectResultData =
      runtimeResultList.value.find((item: any) => String(item.id) === String(selectedStepId)) || {}
  }

  function replaceRuntimeResult(result: any) {
    data.result_data = result || { element_result_list: [] }
    syncSelectedResultData()
    // 最近结果包含大量条件节点和 Arco 子组件。切换整份结果时主动重挂载结果区，
    // 避免 Vue 在旧结果子树已卸载后继续复用其 DOM。
    runtimeResultRenderRevision.value += 1
  }

  function doResetSearch() {
    if (props.embedded) {
      emit('close')
      return
    }
    window.history.back()
  }

  function doRefresh() {
    if (props.caseInputMode) {
      data.dataList = normalizeCaseData(props.caseData)
      replaceRuntimeResult(props.caseResult)
      return Promise.resolve()
    }
    if (!currentPageStepsId.value) return Promise.resolve()
    return getUiPageStepsDetailed(currentPageStepsId.value)
      .then((res) => {
        data.dataList = res.data || []
        if (selectedNode.value) setSelectData(selectedNode.value)
      })
      .catch(console.log)
  }

  function normalizeCaseData(items: any[] = []) {
    return (Array.isArray(items) ? items : []).map((item: any) => {
      const detail: any = {
        id: item.page_step_details_id,
        type: item.type,
        ope_key: item.ope_key,
        condition_value: item.condition_value,
        ele_name: item.page_step_details_name ? { name: item.page_step_details_name } : null,
      }
      if ([0, 1, 4].includes(Number(item.type))) {
        detail.ope_value = cloneDraftValue(item.page_step_details_data || [])
      } else if (Number(item.type) === 2) {
        detail.sql_execute = cloneDraftValue(item.page_step_details_data || [])
      } else if (Number(item.type) === 3) {
        detail.custom = cloneDraftValue(item.page_step_details_data || [])
      } else if (Number(item.type) === 5) {
        detail.func = item.page_step_details_data?.[0]?.func || ''
      }
      return detail
    })
  }

  function addSqlOperation() {
    sqlOperationRows.value.push({ sql: '', key_list: '', datasource_alias: null })
  }

  function removeSqlOperation(index: number) {
    sqlOperationRows.value.splice(index, 1)
  }

  async function loadDatasourceAliases() {
    datasourceAliasOptions.value = []
    if (!currentProjectProductId.value) return
    try {
      const res = await getDataFactoryDatasourceAlias({
        project_product: currentProjectProductId.value,
        status: 1,
        page: 1,
        pageSize: 999,
      })
      datasourceAliasOptions.value = (res.data || []).map((item: any) => ({
        label: item.name,
        value: item.id,
        dbType: Number(item.db_type),
      }))
    } catch (error) {
      console.log(error)
    }
  }

  function getEleName() {
    if (!currentPageId.value) return Promise.resolve()
    return getUiUiElementName(currentPageId.value)
      .then((res) => {
        data.uiPageName = Array.isArray(res.data) ? res.data : []
        if (data.selectData?.id && data.formItems.length) {
          formFeedback()
        }
      })
      .catch(console.log)
  }

  function buildElementCascaderOptions(elements: any[] = []) {
    const groups = new Map<string, any[]>()
    elements.forEach((element: any) => {
      const category = element?.category || '未分类'
      if (!groups.has(category)) groups.set(category, [])
      groups.get(category)!.push({
        label: element.name,
        value: element.id,
        expected_event: element.expected_event || {},
      })
    })
    return Array.from(groups.entries()).map(([category, children]) => ({
      label: category,
      value: category,
      children,
    }))
  }

  function getElementIdFromCascader(value: any) {
    if (Array.isArray(value)) return value[value.length - 1]
    if (typeof value === 'object' && value) return value.id
    return value
  }

  function getElementCascaderValue(value: any) {
    const elementId = getElementIdFromCascader(value)
    if (!elementId) return ''
    const element = data.uiPageName.find((item: any) => String(item.id) === String(elementId))
    if (!element) return value
    return [element.category || '未分类', element.id]
  }

  function formatElementCascaderLabel(options: any[] = []) {
    const labels = options
      .map((item: any) => item?.label)
      .filter((item: any) => item !== undefined && item !== null && item !== '')
    return labels.join(' / ')
  }

  function findExpectedEventByElementValue(value: any) {
    const elementId = getElementIdFromCascader(value)
    if (!elementId) return {}
    return (
      data.uiPageName.find((item: any) => String(item.id) === String(elementId))?.expected_event ||
      {}
    )
  }

  function presetOpeValueValue(presetValues: any[] = [], key: string, fallback: any) {
    const preset = presetValues.find((item: any) => item?.f === key)
    return preset && Object.prototype.hasOwnProperty.call(preset, 'v') ? preset.v : fallback
  }

  function onElementCascaderChange(value: any) {
    if (data.type !== 0 || configFormReadonly.value) return
    const expectedEvent = findExpectedEventByElementValue(value)
    if (!expectedEvent?.ope_key) return
    const opeKeyItem = data.formItems.find((item: any) => item.key === 'ope_key')
    if (!opeKeyItem) return
    opeKeyItem.value = expectedEvent.ope_key
    upDataOpeValue(expectedEvent.ope_key, expectedEvent.ope_value || [])
  }

  function upDataOpeValue(value: any, presetValues: any[] = []) {
    const inputItem = useSelectValue.findItemByValue(value)
    for (let i = data.formItems.length - 1; i >= 0; i--) {
      let key = data.formItems[i].key
      if (!['condition_value', 'ope_key', 'ele_name'].includes(key)) {
        data.formItems.splice(i, 1)
      }
    }
    if (inputItem && data.type === 0) {
      const requiresElement = (inputItem.parameter || []).some((item: any) =>
        ['locating', 'actual'].includes(item.f)
      )
      const elementItemIndex = data.formItems.findIndex((item: any) => item.key === 'ele_name')
      if (!requiresElement && elementItemIndex >= 0) {
        data.formItems.splice(elementItemIndex, 1)
      } else if (requiresElement && elementItemIndex < 0) {
        const operationItemIndex = data.formItems.findIndex((item: any) => item.key === 'ope_key')
        const elementFormItem = formItemsElementOpe.find((item: any) => item.key === 'ele_name')
        elementFormItem.value = ''
        data.formItems.splice(Math.max(0, operationItemIndex + 1), 0, elementFormItem)
      }
    }
    const label: any = useSelectValue.getTopLevelLabelByValue(value)
    if (String(value || '').startsWith('assert_excel_')) {
      loadUiTestFiles()
    }
    if (inputItem && inputItem.parameter) {
      inputItem.parameter.forEach((select: any) => {
        if (
          select.f === 'locating' &&
          data.type === 0 &&
          data.formItems.some((item) => item.key === 'ele_name')
        ) {
          return
        }
        if (
          !['函数断言', '文件断言', 'sql断言'].includes(label.label) &&
          (select.f === 'actual' || select.f === 'locating') &&
          !(select.f === 'locating' && data.formItems.some((item) => item.key === 'ele_name')) &&
          !data.formItems.some((item) => item.key === select.f)
        ) {
          data.formItems.push({
            label: '选择元素',
            key: select.f,
            value: ref(''),
            placeholder: '请选择一个元素',
            required: true,
            type: 'element-cascader',
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              return true
            },
          })
        } else if (
          select.d === true && data.type === 4
            ? ['函数断言', '文件断言', 'sql断言'].includes(label.label) &&
              select.f !== 'expect' &&
              select.n !== '函数代码'
            : !data.formItems.some((item) => item.key === select.f)
        ) {
          const isFileParam = isUiUploadFileParam(value, select.f)
          if (isFileParam) {
            loadUiTestFiles()
          }
          let d = {
            label: select.n ? select.n : select.f,
            key: `${select.f}-ope_value`,
            value:
              presetOpeValueValue(presetValues, select.f, select.v) !== null &&
              typeof presetOpeValueValue(presetValues, select.f, select.v) === 'object'
                ? JSON.stringify(presetOpeValueValue(presetValues, select.f, select.v))
                : presetOpeValueValue(presetValues, select.f, select.v),
            type: isFileParam
              ? 'file-select'
              : select.input_type === 'key_value'
              ? 'key-value'
              : 'textarea',
            required: true,
            placeholder: isFileParam ? '请选择测试文件' : select.p,
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              // this.value = JSON.parse(this.value)
              return true
            },
          }
          data.formItems.push(d)
        }
      })
    }
    if (
      label?.label === 'sql断言' &&
      !data.formItems.some((item: any) => item.key === 'datasource_alias-ope_value')
    ) {
      data.formItems.push({
        label: '逻辑数据源',
        key: 'datasource_alias-ope_value',
        value: presetOpeValueValue(presetValues, 'datasource_alias', ''),
        type: 'datasource-select',
        required: true,
        placeholder: '请选择 MySQL、PostgreSQL 或 SQLite 逻辑数据源',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder)
            return false
          }
          return true
        },
      })
    }
  }

  async function loadUiTestFiles() {
    uiTestFileLoading.value = true
    try {
      await projectInfo.projectProductName()
      const res = await getUserFile({
        page: 1,
        pageSize: 10000,
        type: 0,
      })
      uiTestFileOptions.value = buildUiUploadFileCascaderOptions(
        projectInfo.projectProduct,
        res.data || []
      )
    } catch (error) {
      console.log(error)
    } finally {
      uiTestFileLoading.value = false
    }
  }

  const onRunCase = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (!checkNodeConnections()) return
    if (!checkNodeConfigSaved()) return
    if (!(await ensureFlowSavedForRun())) return
    if (caseRunning.value) return
    caseRunning.value = true
    await prepareDebugPolling(executableNodeCount.value)
    try {
      if (liveWorkbenchVisible.value) {
        const started = await liveWorkbenchPanelRef.value?.startStepDebug()
        if (started) {
          startDebugPolling()
        } else {
          stopDebugPolling()
        }
        return
      }
      const res = await getUiStepsTest(
        currentPageStepsId.value,
        userStore.selected_environment,
        undefined,
        stepControl.value
      )
      currentDebugSlotId.value = String(res.data?.slot_id || '')
      currentDebugTaskId.value = String(res.data?.task_id || '')
      if (currentDebugTaskId.value) {
        saveExecutorTaskObservation('ui-page-step-debug', currentPageStepsId.value, {
          taskId: currentDebugTaskId.value,
          businessType: 'u_page_step',
        })
      }
      Message.loading(res.msg)
      startDebugPolling()
    } catch (e) {
      stopDebugPolling()
    } finally {
      caseRunning.value = false
    }
  }

  const onOpenStepBrowser = async () => {
    if (browserOpening.value) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    if (!currentPageStepsId.value) {
      Message.warning('当前页面步骤不存在')
      return
    }
    if (currentPageType.value !== '0') {
      Message.warning('当前步骤不是 Web 页面步骤')
      return
    }
    browserOpening.value = true
    try {
      const res = await postUiPageStepOpenBrowser({
        page_step_id: currentPageStepsId.value,
        test_env: userStore.selected_environment,
      })
      Message.success(res.msg || '已通知执行器打开目标页面')
    } finally {
      browserOpening.value = false
    }
  }

  const onRunSelectedNode = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (!selectedNodeSupportsSingleStep.value) return
    const detailId = data.selectData?.id || selectedNode.value.config?.id
    if (!detailId || configEditing.value) {
      Message.warning('请先保存当前节点配置')
      return
    }
    if (caseRunning.value || debugRunning.value || singleStepRunning.value) return
    await prepareDebugPolling(1)
    singleStepRunning.value = true
    try {
      if (liveWorkbenchVisible.value) {
        const started = await liveWorkbenchPanelRef.value?.startStepDebug(detailId)
        if (started) {
          startDebugPolling()
        } else {
          stopDebugPolling()
        }
        return
      }
      const res = await getUiStepsTest(
        currentPageStepsId.value,
        userStore.selected_environment,
        undefined,
        stepControl.value,
        detailId
      )
      currentDebugSlotId.value = String(res.data?.slot_id || '')
      currentDebugTaskId.value = String(res.data?.task_id || '')
      if (currentDebugTaskId.value) {
        saveExecutorTaskObservation('ui-page-step-debug', currentPageStepsId.value, {
          taskId: currentDebugTaskId.value,
          businessType: 'u_page_step',
          meta: { detailId },
        })
      }
      Message.loading(res.msg)
      startDebugPolling()
    } catch (error) {
      stopDebugPolling()
    }
  }

  function handleStepLiveReady() {
    Message.success('实时画面连接成功，可以点击调试')
  }

  async function handleStepWorkbenchElementSaved() {
    await getEleName()
  }

  function doRefreshSteps(pageStepsId: any) {
    if (!pageStepsId) return Promise.resolve()
    return getUiSteps({ id: pageStepsId })
      .then((res) => {
        currentStepRecord.value = res.data?.[0] || {}
        flowData.value = normalizeStepFlowData(currentStepRecord.value.flow_data)
        markFlowSaved()
        syncSelectedResultData()
      })
      .catch(console.log)
  }

  async function confirmPendingStepHealing() {
    if (!pendingHealingRecordIds.value.length) {
      Message.warning('待检查节点缺少修复记录，暂时无法确认，请进入修复记录查看详情')
      return
    }
    healingReviewConfirming.value = true
    try {
      for (const recordId of pendingHealingRecordIds.value) {
        await postUiPageStepHealApply(recordId)
      }
      await doRefreshSteps(currentPageStepsId.value)
      Message.success('AI 流程修复已确认')
    } finally {
      healingReviewConfirming.value = false
    }
  }

  async function loadLatestStepExecutionResult(showLoading = false) {
    if (!currentPageStepsId.value) return null
    if (showLoading) latestResultLoading.value = true
    try {
      const res = await getExecutionResultLatestResolved({
        source_type: 'page',
        target_type: 'ui_page_step',
        target_id: currentPageStepsId.value,
        test_env: userStore.selected_environment,
        page: 1,
        pageSize: 1,
      })
      // 画布默认选中节点会同时切换右侧插槽树，先等待该轮挂载完成，
      // 避免最新结果在旧组件尚未挂载时触发 Vue 的组件复用分支。
      await nextTick()
      replaceRuntimeResult(res.data?.result_data)
      return res.data || null
    } finally {
      if (showLoading) latestResultLoading.value = false
    }
  }

  async function prepareDebugPolling(expectedNodeCount: number) {
    stopDebugPolling({ keepCompleted: false })
    clearDebugCompletedTimer()
    try {
      const res = await getExecutionResultLatestResolved({
        source_type: 'page',
        target_type: 'ui_page_step',
        target_id: currentPageStepsId.value,
        test_env: userStore.selected_environment,
        page: 1,
        pageSize: 1,
      })
      debugBaselineResultId.value = res.data?.id || null
    } catch (error) {
      debugBaselineResultId.value = null
    }
    debugStartedAt.value = Date.now()
    currentDebugSlotId.value = ''
    currentDebugTaskId.value = ''
    debugExpectedNodeCount.value = Math.max(1, Number(expectedNodeCount) || 1)
    replaceRuntimeResult(null)
    debugRunning.value = true
    debugCompleted.value = false
    debugRefreshError.value = false
    debugPollFailures.value = 0
  }

  function scheduleDebugPolling(delay = DEBUG_POLL_INTERVAL_MS) {
    if (debugPollTimer) clearTimeout(debugPollTimer)
    if (!debugRunning.value) return
    debugPollTimer = setTimeout(() => {
      debugPollTimer = null
      void pollDebugResult()
    }, delay)
  }

  function startDebugPolling() {
    scheduleDebugPolling(0)
  }

  async function resumeActiveDebugTask() {
    if (!currentPageStepsId.value || currentDebugTaskId.value) return
    try {
      const observation = loadExecutorTaskObservation(
        'ui-page-step-debug',
        currentPageStepsId.value
      )
      if (observation?.taskId) {
        currentDebugTaskId.value = String(observation.taskId)
        debugRunning.value = true
        debugCompleted.value = false
        debugRefreshError.value = false
        debugExpectedNodeCount.value = Math.max(1, Number(executableNodeCount.value) || 1)
        startDebugPolling()
        return
      }
      const res = await getActiveExecutorTasks({
        business_type: 'u_page_step',
        business_id: currentPageStepsId.value,
      })
      const task = (res.data || [])[0]
      if (!task?.task_id) return
      currentDebugTaskId.value = String(task.task_id)
      saveExecutorTaskObservation('ui-page-step-debug', currentPageStepsId.value, {
        taskId: currentDebugTaskId.value,
        businessType: 'u_page_step',
      })
      debugRunning.value = true
      debugCompleted.value = false
      debugRefreshError.value = false
      debugExpectedNodeCount.value = Math.max(1, Number(executableNodeCount.value) || 1)
      startDebugPolling()
    } catch (error) {
      console.log(error)
    }
  }

  function stopDebugPolling(options: { keepCompleted?: boolean } = {}) {
    if (debugPollTimer) {
      clearTimeout(debugPollTimer)
      debugPollTimer = null
    }
    debugPollRequesting = false
    debugRunning.value = false
    currentDebugSlotId.value = ''
    debugExpectedNodeCount.value = 0
    singleStepRunning.value = false
    debugRefreshError.value = false
    if (!options.keepCompleted) {
      debugCompleted.value = false
      clearDebugCompletedTimer()
    }
  }

  async function pollDebugResult() {
    if (!currentPageStepsId.value) return
    if (debugPollRequesting) {
      scheduleDebugPolling(250)
      return
    }
    debugPollRequesting = true
    try {
      if (currentDebugTaskId.value) {
        const taskRes = await getExecutorTask(currentDebugTaskId.value)
        const task = taskRes.data || {}
        if (task.progress?.current_node_id) {
          // 任务事实优先提供当前节点；节点明细结果仍沿用既有结果接口。
          currentStepRecord.value = { ...currentStepRecord.value, status: 3 }
        }
        if (task.terminal) {
          const finishedTaskId = currentDebugTaskId.value
          if (task.result?.element_result_list) {
            replaceRuntimeResult(task.result)
          }
          await finishDebugPolling(Boolean(task.result))
          clearExecutorTaskObservation(
            'ui-page-step-debug',
            currentPageStepsId.value,
            finishedTaskId
          )
          currentDebugTaskId.value = ''
          return
        }
      }
      const res = await getUiSteps({ id: currentPageStepsId.value })
      debugPollFailures.value = 0
      debugRefreshError.value = false
      const record = res.data?.[0] || {}
      applyRuntimeStepRecord(record)
      if (await isDebugFinished(record)) {
        await finishDebugPolling(true)
      }
    } catch (error) {
      debugPollFailures.value += 1
      debugRefreshError.value = true
    } finally {
      debugPollRequesting = false
      if (debugRunning.value) {
        const retryDelay = debugRefreshError.value
          ? Math.min(
              1000 * 2 ** Math.max(0, debugPollFailures.value - 1),
              DEBUG_POLL_MAX_BACKOFF_MS
            )
          : DEBUG_POLL_INTERVAL_MS
        scheduleDebugPolling(retryDelay)
      }
    }
  }

  function applyRuntimeStepRecord(record: any) {
    if (!record?.id) return
    currentStepRecord.value = record
    flowData.value = normalizeStepFlowData(record.flow_data || flowData.value)
  }

  async function finishDebugPolling(resultLoaded = false) {
    stopDebugPolling({ keepCompleted: true })
    if (!resultLoaded) {
      await loadLatestStepExecutionResult()
    }
    // 流程自愈报告会在任务收尾阶段原子回写画布和节点明细；两份数据必须
    // 一起刷新，否则新节点找不到 ope_key，卡片会把节点名称误显示为执行方法。
    await doRefreshSteps(currentPageStepsId.value)
    await doRefresh()
    debugCompleted.value = true
    clearDebugCompletedTimer()
    debugCompletedTimer = setTimeout(() => {
      debugCompleted.value = false
    }, 1800)
  }

  function handleStepResultMessage(event: Event) {
    const message = (event as CustomEvent).detail
    if (message?.data?.func_name !== 'u_page_steps' || !debugRunning.value) return
    const result = message?.data?.func_args
    if (!result || result.case_step_details_id) return
    if (String(result.id || '') !== String(currentPageStepsId.value || '')) return
    if (
      currentDebugSlotId.value &&
      result.slot_id &&
      String(result.slot_id) !== currentDebugSlotId.value
    ) {
      return
    }
    replaceRuntimeResult(result)
    currentStepRecord.value = {
      ...currentStepRecord.value,
      status: result.is_final ? result.status : 3,
    }
    if (result.is_final) {
      void finishDebugPolling(true)
    }
  }

  function clearDebugCompletedTimer() {
    if (debugCompletedTimer) {
      clearTimeout(debugCompletedTimer)
      debugCompletedTimer = null
    }
  }

  async function isDebugFinished(record: any) {
    if (!debugRunning.value) return false
    const total = debugExpectedNodeCount.value
    const hasFinishedStatus = record.status === 0 || record.status === 1
    const hasCompleteRuntimeResult = total > 0 && runtimeResultList.value.length >= total
    if (!hasFinishedStatus && !hasCompleteRuntimeResult) return false

    const latestResult = await loadLatestStepExecutionResult()
    if (!latestResult?.id) return false
    if (debugBaselineResultId.value !== null) {
      return String(latestResult.id) !== String(debugBaselineResultId.value)
    }
    return parseTime(latestResult.create_time) >= debugStartedAt.value - 1000
  }

  function parseTime(value: any) {
    if (!value) return 0
    if (typeof value === 'number') return value
    const text = String(value).replace(' ', 'T')
    const time = Date.parse(text)
    return Number.isNaN(time) ? 0 : time
  }

  // 监听选中节点变化，更新配置文本
  watch(
    selectedNode,
    (node) => {
      if (node) {
        configText.value = JSON.stringify(node.config || {}, null, 2)
      } else {
        configText.value = ''
      }
    },
    { immediate: true }
  )

  // 查找指定节点的上一个节点
  const findPreviousNode = (nodeId: string): UINode | null => {
    // 查找连接到当前节点的边
    const incomingEdge = flowData.value.edges.find((edge) => edge.target.node_id === nodeId)
    if (!incomingEdge) {
      return null // 没有上一个节点
    }
    // 查找上一个节点
    const previousNode = flowData.value.nodes.find(
      (node) => node.id === incomingEdge.source.node_id
    )
    return previousNode || null
  }

  const onNodeClick = (node: UINode) => {
    captureSelectedNodeDraft()
    setSelectData(node)
    configEditing.value = !node.config?.id
    // 检查上一个节点是否为判断类型（type: 4）
    const previousNode = findPreviousNode(node.id)
    data.isAdd = false
    if (previousNode && previousNode.type === 4) {
      data.conditionId = previousNode.config.id
      data.conditionNodeId = previousNode.id
      data.condition = true
    } else {
      data.conditionId = 0
      data.conditionNodeId = ''
      data.condition = false
    }
    // 先清空表单项，重新构建基础表单
    changeStatus(node.type)

    const draft = nodeFormDrafts.get(node.id)
    const draftOpeKey = draft?.ope_key
    // 如果有选中的数据，需要处理回显和动态表单项
    if (Object.keys(data.selectData).length > 0 || draftOpeKey) {
      // 先处理操作类型选择，触发动态表单生成
      const opeKeyItem = data.formItems.find((item: any) => item.key === 'ope_key')
      const opeKey = draftOpeKey || data.selectData.ope_key
      if (opeKeyItem && opeKey) {
        opeKeyItem.value = opeKey
        // 触发动态表单项生成
        upDataOpeValue(opeKey)
      }
    }
    formFeedback()
    fillDefaultPythonCode()
    restoreNodeDraft(node.id)
    if (draft) {
      configEditing.value = true
    }
  }

  function cloneDraftValue(value: any) {
    if (value === undefined || value === null) return value
    if (typeof value !== 'object') return value
    return JSON.parse(JSON.stringify(value))
  }

  function textareaModelValue(value: unknown): string {
    if (value === null || value === undefined) return ''
    if (typeof value === 'string') return value
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value)
      } catch {
        return String(value)
      }
    }
    return String(value)
  }

  function captureSelectedNodeDraft() {
    const nodeId = selectedNode.value?.id
    if (!nodeId || configFormReadonly.value || (!data.formItems.length && data.type !== 2)) return
    const draft = Object.fromEntries(
      data.formItems.map((item: any) => [item.key, cloneDraftValue(item.value)])
    )
    if (data.type === 2) draft.__sql_execute = cloneDraftValue(sqlOperationRows.value)
    nodeFormDrafts.set(nodeId, draft)
  }

  function restoreNodeDraft(nodeId: string) {
    const draft = nodeFormDrafts.get(nodeId)
    if (!draft) return
    if (Object.prototype.hasOwnProperty.call(draft, '__sql_execute')) {
      sqlOperationRows.value = cloneDraftValue(draft.__sql_execute || [])
    }
    data.formItems.forEach((item: any) => {
      if (Object.prototype.hasOwnProperty.call(draft, item.key)) {
        item.value = cloneDraftValue(draft[item.key])
      }
    })
  }

  function changeStatus(event: number) {
    data.type = event
    // 清空表单项，重新构建
    data.formItems = []
    if (data.condition) {
      let placeholder: any = null
      const conditionDraft = nodeFormDrafts.get(data.conditionNodeId)
      const hasDraftMethod = Boolean(
        conditionDraft && Object.prototype.hasOwnProperty.call(conditionDraft, 'ope_key')
      )
      const savedCondition = data.dataList.find((item: any) => item.id === data.conditionId)
      const conditionMethod = hasDraftMethod ? conditionDraft?.ope_key : savedCondition?.ope_key
      const byValue = useSelectValue.findItemByValue(conditionMethod)
      const conditionParameters = byValue?.parameter || []
      conditionParameters.forEach((parameter: any) => {
        if (parameter.f === 'expect') {
          placeholder = parameter.p
          data.isAdd = true
        }
      })
      if (data.isAdd) {
        if (placeholder) {
          formItemsElementCondition[0].placeholder = placeholder
        }
        data.formItems.push(...formItemsElementCondition)
      }
    }
    if (event === 0) {
      data.formItems.push(...formItemsElementOpe)
      // 元素断言
    } else if (event === 1) {
      data.formItems.push(...formItemsElementAss)
      // sql操作
    } else if (event === 2) {
      sqlOperationRows.value = []
      // 自定义变量
    } else if (event === 3) {
      data.formItems.push(...formItemsElementKey)
      // 条件判断
    } else if (event === 4) {
      data.formItems.push(...formItemsElement4)
    } else if (event === 5) {
      data.formItems.push(...formItemsElementCode)
    } else if (event === 6) {
      data.formItems.push(...formItemsForceWait)
    }
  }

  function fillDefaultPythonCode() {
    if (data.type !== 5) return
    const codeItem = data.formItems.find((item: any) => item.key === 'func')
    if (codeItem && !codeItem.value) {
      codeItem.value = PYTHON_CODE_TEMPLATE
    }
  }

  // 处理所有表单项的回显
  function formFeedback() {
    if (data.type === 2) {
      sqlOperationRows.value = cloneDraftValue(data.selectData?.sql_execute || [])
      if (!sqlOperationRows.value.length && !configFormReadonly.value) addSqlOperation()
      return
    }
    data.formItems.forEach((it: any) => {
      let propName: any = data.selectData[it.key]
      if (it.key === 'key') {
        propName = data.selectData?.custom ? data.selectData?.custom[0]['key'] : ''
      } else if (it.key === 'value') {
        propName = data.selectData?.custom ? data.selectData?.custom[0]['value'] : ''
      } else if (it.key === 'sql') {
        propName = data.selectData?.sql_execute ? data.selectData?.sql_execute[0]['sql'] : ''
      } else if (it.key === 'key_list') {
        propName = data.selectData?.sql_execute ? data.selectData?.sql_execute[0]['key_list'] : ''
      }
      if (
        (it.key.includes('locating') || it.key.includes('actual') || it.key === 'ele_name') &&
        it.label !== '函数代码'
      ) {
        propName = getElementCascaderValue(data.selectData.ele_name)
      } else if (it.key.includes('ope_value')) {
        if (data.selectData.ope_value) {
          data.selectData.ope_value.forEach((item1: any) => {
            if ((item1.d || data.type === 6) && it.key.includes(item1.f)) {
              propName = item1.v
              if (isUiUploadFileParam(data.selectData.ope_key, item1.f)) {
                loadUiTestFiles()
                propName = normalizeUiUploadFileValue(propName, uiTestFileOptions.value)
              }
            }
          })
        }
      } else if (typeof propName === 'undefined' && data.selectData.ope_value) {
        data.selectData.ope_value.forEach((item: any) => {
          if (item.f === it.key) {
            propName = item.v
          }
        })
      }
      if (Array.isArray(propName)) {
        it.value = propName
      } else if (typeof propName === 'object' && propName !== null) {
        it.value = propName.id ? propName?.id : propName?.expect
      } else {
        it.value = propName
      }
    })
  }

  // 节点选中事件
  const onNodeSelect = (node: UINode | null) => {
    selectedNode.value = node
  }

  // 流程图数据变化事件
  const onFlowChange = (newFlowData: FlowData) => {
    flowData.value = normalizeStepFlowData(newFlowData)
    flowRevision += 1
    flowSaveStatus.value = 'dirty'
    scheduleFlowSave()
  }

  async function onNodeDuplicate(sourceNode: UINode) {
    if (nodeDuplicating.value) return
    captureSelectedNodeDraft()
    const sourceDraft = nodeFormDrafts.get(sourceNode.id)
    const nodeId = `${sourceNode.type}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    const duplicateNode: UINode = {
      ...sourceNode,
      id: nodeId,
      position: {
        x: Number(sourceNode.position?.x || 0) + 40,
        y: Number(sourceNode.position?.y || 0) + 40,
      },
      config: {},
    }
    const duplicateFlow = normalizeStepFlowData({
      nodes: [...flowData.value.nodes, duplicateNode],
      edges: [...flowData.value.edges],
    })

    if (!sourceNode.config?.id || sourceDraft) {
      if (sourceDraft) {
        nodeFormDrafts.set(nodeId, cloneDraftValue(sourceDraft))
      }
      flowData.value = duplicateFlow
      flowRevision += 1
      flowSaveStatus.value = 'dirty'
      scheduleFlowSave()
      await nextTick()
      flowChartRef.value?.selectNode(nodeId)
      Message.success('节点已复制，请保存副本配置')
      return
    }

    nodeDuplicating.value = true
    clearFlowSaveTimer()
    Message.loading('正在复制节点')
    try {
      if (flowSavePromise) await flowSavePromise
      const res = await postUiPageStepNodeCopy({
        page_step_id: currentPageStepsId.value,
        source_detail_id: sourceNode.config.id,
        node_id: nodeId,
        flow_data: duplicateFlow,
      })
      flowData.value = normalizeStepFlowData(res.data.flow_data)
      flowRevision += 1
      markFlowSaved(flowRevision)
      await doRefresh()
      await nextTick()
      flowChartRef.value?.selectNode(nodeId)
      Message.success(res.msg)
    } catch (error) {
      console.log(error)
    } finally {
      nodeDuplicating.value = false
    }
  }

  const onStepControlChange = (value: UiStepControl) => {
    stepControl.value = { ...value }
  }

  function normalizeStepFlowData(value?: FlowData): FlowData {
    return {
      nodes: Array.isArray(value?.nodes) ? value.nodes : [],
      edges: Array.isArray(value?.edges) ? value.edges : [],
    }
  }

  // 连接线删除事件
  const onEdgeDelete = (edge: UIEdge) => {
    Message.success('连接线已删除')
  }

  // 节点删除事件
  const onNodeDelete = (node: UINode) => {
    nodeFormDrafts.delete(node.id)
    if (selectedNode.value?.id === node.id) {
      selectedNode.value = null
    }
    if (!node.config?.id) {
      return
    }
    deleteUiPageStepsDetailed(node.config.id, currentPageStepsId.value)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  // 检查是否有节点没有进行连接
  const checkNodeConnections = (): boolean => {
    if (flowData.value.nodes.length === 0) {
      Message.warning('画布中没有可执行节点，请先添加并配置节点')
      return false
    }

    if (flowData.value.nodes.length === 1) {
      return true
    }

    const nodeIds = new Set(flowData.value.nodes.map((node) => node.id))
    const validEdges = flowData.value.edges.filter(
      (edge) => nodeIds.has(edge.source.node_id) && nodeIds.has(edge.target.node_id)
    )
    const roots = flowData.value.nodes.filter(
      (node) => !validEdges.some((edge) => edge.target.node_id === node.id)
    )
    if (roots.length !== 1) {
      Message.warning(`画布需要且只能有一个起始节点，当前检测到 ${roots.length} 个`)
      return false
    }

    for (const node of flowData.value.nodes) {
      const inputConnections = validEdges.filter((edge) => edge.target.node_id === node.id)
      const outputConnections = validEdges.filter((edge) => edge.source.node_id === node.id)
      if (node.type !== 4) {
        if (inputConnections.length > 1 || outputConnections.length > 1) {
          Message.warning(`普通节点“${node.label || node.id}”最多只能有一条输入线和一条输出线`)
          return false
        }
      } else if (outputConnections.length === 0) {
        Message.warning(`判断节点“${node.label || node.id}”尚未连接任何分支`)
        return false
      }
    }

    const visited = new Set<string>()
    const visiting = new Set<string>()
    const visit = (nodeId: string): boolean => {
      if (visiting.has(nodeId)) return false
      if (visited.has(nodeId)) return true
      visiting.add(nodeId)
      for (const edge of validEdges.filter((item) => item.source.node_id === nodeId)) {
        if (!visit(edge.target.node_id)) return false
      }
      visiting.delete(nodeId)
      visited.add(nodeId)
      return true
    }
    if (!visit(roots[0].id)) {
      Message.warning('画布中存在循环连线，请调整后再调试')
      return false
    }
    if (visited.size !== flowData.value.nodes.length) {
      Message.warning('画布中存在未接入主流程的节点，请连接完整后再调试')
      return false
    }

    return true
  }

  const checkNodeConfigSaved = (): boolean => {
    const invalidNodes = flowData.value.nodes.filter((node) => !node.config?.id)
    if (invalidNodes.length) {
      const nodeNames = invalidNodes
        .map((node) => node.label || node.id)
        .filter(Boolean)
        .join('、')
      flowChartRef.value?.selectNode(invalidNodes[0].id)
      Message.warning({
        id: 'page-step-debug-validation',
        content: `未保存节点：${nodeNames}。已定位到第一个问题节点，请完成配置并保存。`,
        duration: 5000,
        closable: true,
      })
      return false
    }
    const dirtyNodeIds = draftNodeIds.value
    if (dirtyNodeIds.length) {
      const dirtyNodes = dirtyNodeIds
        .map((nodeId) => flowData.value.nodes.find((node) => node.id === nodeId))
        .filter((node): node is UINode => Boolean(node))
      const nodeNames = dirtyNodes
        .map((node) => getDraftNodeDisplayName(node))
        .filter(Boolean)
        .join('、')
      if (dirtyNodes[0]) {
        flowChartRef.value?.selectNode(dirtyNodes[0].id)
      }
      Message.warning({
        id: 'page-step-debug-validation',
        content: `以下节点存在未保存的编辑内容：${
          nodeNames || '当前节点'
        }。已定位到第一个问题节点，请点击右侧“保存”。`,
        duration: 5000,
        closable: true,
      })
      return false
    }
    return true
  }

  function getDraftNodeDisplayName(node: UINode) {
    const detail = data.dataList.find((item: any) => String(item.id) === String(node.config?.id))
    return (
      detail?.ele_name?.name ||
      useSelectValue.getSelectLabel(detail?.ope_key) ||
      node.label ||
      node.id
    )
  }

  // 保存表单数据
  const handleConfigAction = () => {
    if (configFormReadonly.value) {
      configEditing.value = true
      return
    }
    saveFormData()
  }

  const saveFormData = async () => {
    if (!selectedNode.value) return
    if (formSaving.value) return
    const savingNode = selectedNode.value
    const savingNodeId = savingNode.id

    if (
      isExcelAssertionMethod.value &&
      excelAssertionEditorRef.value &&
      !excelAssertionEditorRef.value.validate()
    ) {
      return
    }

    // 添加必填校验
    if (
      !data.formItems.every((it: any) =>
        isCaseInheritedConfigItem(it) ? true : it.validator ? it.validator() : true
      )
    ) {
      return
    }

    if (data.type === 2 && !dataSourceOperationListRef.value?.validate()) {
      Message.warning('请完整填写逻辑数据源和执行内容')
      return
    }

    formSaving.value = true
    clearFlowSaveTimer()
    try {
      if (flowSavePromise) await flowSavePromise
      const value = (
        data.type === 2
          ? { sql_execute: cloneDraftValue(sqlOperationRows.value) }
          : getFormItems(data.formItems)
      ) as UiPageStepsDetailPayload
      value['page_step'] = currentPageStepsId.value
      value['type'] = data.type
      if (data?.selectData?.id) {
        value['id'] = data.selectData.id
      }
      value['flow_data'] = normalizeStepFlowData(flowData.value)
      value['node_id'] = savingNodeId
      value['step_sort'] = 0
      value['precondition'] = data.selectData.precondition || { operator: 'all', conditions: [] }
      value['postcondition'] = data.selectData.postcondition || { operator: 'all', conditions: [] }
      value['page_type'] = Number(currentPageType.value)
      if (props.caseInputMode) {
        const saved = await saveCaseNodeInputs(value)
        if (!saved) return
        nodeFormDrafts.delete(savingNodeId)
        configEditing.value = false
        return
      }
      if (value.condition_value) {
        value['condition_value'] = { expect: value.condition_value }
      }
      if (value.key || value.value) {
        value['custom'] = [{ key: value.key, value: value.value }]
        delete value.key
        delete value.value
      }
      if (value.sql || value.key_list) {
        value['sql_execute'] = [{ sql: value.sql, key_list: value.key_list }]
        delete value.sql
        delete value.key_list
      }
      if (data.type === 6) {
        value['ope_key'] = null
        value['ope_value'] = [
          { f: 'seconds', v: Number(value['seconds-ope_value']) },
        ]
        delete value['seconds-ope_value']
      }

      const res = await postUiPageStepsDetailed(
        { ...value, ...processOptionData(value) },
        currentPageStepsId.value
      )
      Message.success(res.msg)
      nodeFormDrafts.delete(savingNodeId)
      flowData.value = normalizeStepFlowData(res.data.flow_data)
      flowRevision += 1
      markFlowSaved(flowRevision)
      const updatedNode = flowData.value.nodes.find((node) => node.id === savingNodeId)
      if (selectedNode.value?.id === savingNodeId && updatedNode) {
        selectedNode.value = updatedNode
        data.selectData = {
          ...data.selectData,
          ...res.data,
          id: res.data.id,
        }
        configEditing.value = false
      }
      await doRefresh()
    } catch (error) {
      console.log(error)
    } finally {
      formSaving.value = false
      if (flowRevision !== savedFlowRevision) scheduleFlowSave()
    }
  }

  async function saveCaseNodeInputs(value: any) {
    if (!props.caseStepId || !props.caseId || !data.selectData?.id) {
      Message.error('未找到 Case 页面步骤或节点信息')
      return false
    }
    const nextCaseData = cloneDraftValue(props.caseData || [])
    const target = nextCaseData.find(
      (item: any) => String(item.page_step_details_id) === String(data.selectData.id)
    )
    if (!target) {
      Message.error('Case 节点缓存不存在，请返回用例编排并对该步骤执行“同步数据”')
      return false
    }
    const nodeType = Number(target.type)
    if ([0, 1, 4, 6].includes(nodeType)) {
      target.page_step_details_data = (target.page_step_details_data || []).map((param: any) => {
        const nextParam = cloneDraftValue(param)
        const dynamicKey = `${param.f}-ope_value`
        if (Object.prototype.hasOwnProperty.call(value, dynamicKey)) {
          nextParam.v = value[dynamicKey]
        } else if (
          !['locating', 'actual'].includes(param.f) &&
          Object.prototype.hasOwnProperty.call(value, param.f)
        ) {
          nextParam.v = value[param.f]
        }
        return nextParam
      })
      if (value.condition_value !== undefined) {
        target.condition_value = { expect: value.condition_value }
      }
    } else if (nodeType === 2) {
      target.page_step_details_data = cloneDraftValue(value.sql_execute || [])
    } else if (nodeType === 3) {
      target.page_step_details_data = [{ key: value.key, value: value.value }]
    } else if (nodeType === 5) {
      target.page_step_details_data = [{ func: value.func }]
    }
    const res = await putUiCaseStepsDetailed(
      {
        id: props.caseStepId,
        case_data: nextCaseData,
      },
      Number(props.caseId)
    )
    Message.success(res.msg)
    data.dataList = normalizeCaseData(nextCaseData)
    setSelectData(selectedNode.value!)
    emit('caseDataSaved', nextCaseData)
    return true
  }

  function processOptionData(value: any) {
    const extractedValues = []
    if (!value.ope_key) {
      return {}
    }
    const parameter = useSelectValue.findItemByValue(value.ope_key)?.parameter
    if (!parameter) {
      return {}
    }
    const datasourceAlias = value['datasource_alias-ope_value']
    delete value['datasource_alias-ope_value']
    const requiresElement = parameter.some((item: any) => ['locating', 'actual'].includes(item.f))
    for (const key in value) {
      const newKey = key.replace('-ope_value', '')
      parameter.forEach((item: any) => {
        const isDuplicate = extractedValues.some(
          (existingItem) => existingItem.d === item.d && existingItem.f === item.f
        )
        if (key == 'locating' || key == 'actual') {
          value['ele_name'] = getElementIdFromCascader(value[key])
          if (!isDuplicate) {
            extractedValues.push(item)
          }
        } else if (key === 'ele_name') {
          value['ele_name'] = getElementIdFromCascader(value[key])
        } else if (newKey && item.f === newKey) {
          item['v'] = isUiUploadFileParam(value.ope_key, newKey)
            ? getUiUploadFileValueFromCascader(value[key], uiTestFileOptions.value)
            : value[key]
          if (!isDuplicate) {
            extractedValues.push(item)
          }
          delete value[key]
        }
      })
    }
    if (value['ele_name']) {
      const locatingItem = parameter.find((item: any) => item.f === 'locating')
      const hasLocating = extractedValues.some((item: any) => item.f === 'locating')
      if (locatingItem && !hasLocating) {
        extractedValues.push(locatingItem)
      }
    }
    if (String(value.ope_key || '').startsWith('assert_sql_')) {
      extractedValues.push({
        f: 'datasource_alias',
        n: '逻辑数据源',
        p: '请选择逻辑数据源',
        d: true,
        v: datasourceAlias,
      })
    }
    return {
      ope_value: extractedValues,
      ele_name: requiresElement ? value['ele_name'] : null,
    }
  }

  function getNodeTypeLabel(type: any) {
    const enumLabel = enumStore.element_ope?.[type]?.title
    return enumLabel || nodeTypes.find((item) => item.type === Number(type))?.label || '未知类型'
  }

  function getMethodLabel(value: any) {
    if (!value) return '-'
    return useSelectValue.findItemByValue(value)?.label || value
  }

  function getElementName(value: any) {
    if (!value) return '-'
    if (typeof value === 'object') return value.name || value.label || value.id || '-'
    const element = data.uiPageName.find((item: any) => String(item.id) === String(value))
    if (element) return element.name || value
    return value
  }

  function getSelectedNodeTitle() {
    const elementName = getElementName(data.selectData?.ele_name)
    const methodLabel = getMethodLabel(data.selectData?.ope_key)
    return (
      (elementName !== '-' ? elementName : '') ||
      data.selectData?.name ||
      (methodLabel !== '-' ? methodLabel : '') ||
      selectedNode.value?.label ||
      '未命名节点'
    )
  }

  function getConfigParams(item: any) {
    if (Array.isArray(item?.ope_value)) return item.ope_value
    if (Array.isArray(item?.custom)) return item.custom
    if (Array.isArray(item?.sql_execute)) return item.sql_execute
    if (item?.condition_value) return [item.condition_value]
    return []
  }

  function getVisibleConfigParams(item: any) {
    const params = getConfigParams(item)
    if (item?.type === 0) {
      return params.filter((param: any) => param?.d)
    }
    if (item?.type === 1) {
      return params.filter((param: any) => param?.f !== 'actual')
    }
    return params
  }

  function getConfigParamCount(item: any) {
    return getVisibleConfigParams(item).length
  }

  function stringifyValue(value: any) {
    if (value === undefined || value === null || value === '') return '-'
    if (Array.isArray(value)) return value.join(', ')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  function getConfigParamLabel(param: any, index: number) {
    return param?.n || param?.key || param?.f || param?.name || `参数${index + 1}`
  }

  function getConfigParamValue(param: any) {
    return stringifyValue(
      param?.v ?? param?.value ?? param?.sql ?? param?.key_list ?? param?.func ?? param?.expect
    )
  }

  function getConfigParamSummary(item: any) {
    return getVisibleConfigParams(item)
      .map((param: any, index: number) => ({
        key: `${item?.id || 'node'}-${index}`,
        label: getConfigParamLabel(param, index),
        value: getConfigParamValue(param),
      }))
      .filter((param: any) => param.value !== '-')
      .slice(0, 6)
  }

  function getConditionSummary(value: any) {
    if (!value) return '-'
    if (typeof value === 'string') return value
    return stringifyValue(value.expect ?? value.value ?? value)
  }

  async function loadSelectedNodeElement() {
    if (!data.selectData?.id) {
      Message.error('未找到页面步骤明细ID')
      return null
    }
    const res = await getUiPageStepsDetailedById(data.selectData.id)
    const element = (res.data || [])[0]?.ele_name
    if (!element?.id) {
      Message.error('当前节点没有绑定页面元素')
      return null
    }
    return element
  }

  async function openSelectedElementEditPanel() {
    if (elementEditLoading.value) return
    elementEditLoading.value = true
    try {
      const element = await loadSelectedNodeElement()
      if (!element) return
      elementEditPanelRef.value?.openEdit(element)
    } catch (error) {
      console.log(error)
      Message.error('元素信息获取失败')
    } finally {
      elementEditLoading.value = false
    }
  }

  async function runSelectedElementDeepCheck() {
    if (elementDeepCheckLoading.value) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    try {
      const element = await loadSelectedNodeElement()
      if (!element) return
      const runtimeVariables = await deepCheckVariablesDialogRef.value?.open({
        ...element,
        page_url: currentPageInfo.value.url,
      })
      if (runtimeVariables === null) return
      elementCheckResult.visible = false
      elementDeepCheckLoading.value = true
      elementDeepCheckId.value = ''
      elementDeepCheckTaskId.value = ''
      elementDeepCheckElementId.value = element.id
      elementDeepCheckSession.cancel()
      elementDeepCheckToken = elementDeepCheckSession.start(element.id)
      clearElementDeepCheckTimer()
      elementDeepCheckTimer = setTimeout(() => {
        if (!elementDeepCheckLoading.value) return
        if (elementDeepCheckToken != null) {
          elementDeepCheckSession.cancel(elementDeepCheckToken)
        }
        elementDeepCheckToken = null
        elementDeepCheckLoading.value = false
        elementDeepCheckId.value = ''
        elementDeepCheckTaskId.value = ''
        elementDeepCheckElementId.value = null
        Message.warning('元素深度检测超时，请确认执行器在线后重试')
      }, 180000)
      if (liveWorkbenchVisible.value) {
        const started = await liveWorkbenchPanelRef.value?.checkElementInWorkspace(
          element,
          'deep',
          runtimeVariables || {}
        )
        if (!started) {
          clearElementDeepCheckTimer()
          if (elementDeepCheckToken != null) {
            elementDeepCheckSession.cancel(elementDeepCheckToken)
          }
          elementDeepCheckToken = null
          elementDeepCheckId.value = ''
          elementDeepCheckTaskId.value = ''
          elementDeepCheckElementId.value = null
          elementDeepCheckLoading.value = false
        } else if (typeof started === 'string' && elementDeepCheckLoading.value) {
          elementDeepCheckId.value = started
          if (elementDeepCheckToken != null) {
            elementDeepCheckSession.bindCheckId(elementDeepCheckToken, started)
          }
        }
        return
      }
      const res = await postUiElementCheck({
        element_id: element.id,
        test_env: userStore.selected_environment,
        check_mode: 'deep',
        runtime_variables: runtimeVariables || {},
      })
      elementDeepCheckId.value = String(res.data?.check_id || '')
      elementDeepCheckTaskId.value = String(res.data?.task_id || '')
      if (elementDeepCheckTaskId.value) {
        saveExecutorTaskObservation('ui-step-element-check', element.id, {
          taskId: elementDeepCheckTaskId.value,
          businessType: 'u_element_check',
          meta: { checkId: elementDeepCheckId.value },
        })
      }
      if (elementDeepCheckToken != null) {
        elementDeepCheckSession.bindCheckId(elementDeepCheckToken, elementDeepCheckId.value)
      }
      if (elementDeepCheckTaskId.value) scheduleElementDeepCheckPoll(0)
      Message.success(res.msg)
    } catch (error) {
      console.log(error)
      clearElementDeepCheckTimer()
      elementDeepCheckId.value = ''
      elementDeepCheckTaskId.value = ''
      elementDeepCheckElementId.value = null
      if (elementDeepCheckToken != null) {
        elementDeepCheckSession.cancel(elementDeepCheckToken)
      }
      elementDeepCheckToken = null
      elementDeepCheckLoading.value = false
    }
  }

  function clearElementDeepCheckTimer() {
    if (elementDeepCheckTimer) {
      clearTimeout(elementDeepCheckTimer)
      elementDeepCheckTimer = null
    }
    if (elementDeepCheckPollTimer) {
      clearTimeout(elementDeepCheckPollTimer)
      elementDeepCheckPollTimer = null
    }
    elementDeepCheckPolling = false
  }

  function scheduleElementDeepCheckPoll(delay = 1000) {
    if (!elementDeepCheckLoading.value || !elementDeepCheckTaskId.value) return
    if (elementDeepCheckPollTimer) clearTimeout(elementDeepCheckPollTimer)
    elementDeepCheckPollTimer = setTimeout(() => {
      void pollElementDeepCheckResult()
    }, delay)
  }

  async function pollElementDeepCheckResult() {
    if (
      elementDeepCheckPolling ||
      !elementDeepCheckLoading.value ||
      !elementDeepCheckTaskId.value ||
      !elementDeepCheckElementId.value
    ) {
      return
    }
    elementDeepCheckPolling = true
    try {
      const res = await getExecutorTask(elementDeepCheckTaskId.value)
      const task = res.data || {}
      if (!task.terminal) {
        scheduleElementDeepCheckPoll()
        return
      }
      const result =
        task.result?.check_id || task.result?.element_id
          ? task.result
          : {
              check_id: elementDeepCheckId.value,
              element_id: elementDeepCheckElementId.value,
              element_name: getElementName(data.selectData?.ele_name),
              check_mode: 'deep',
              status: 0,
              check_status: 'invalid',
              error_message: task.error_message || '执行器任务未返回检测结果',
            }
      handleStepElementCheckResult({
        ...result,
        executor_task_id: elementDeepCheckTaskId.value,
      })
      return
    } catch (error) {
      console.log(error)
    } finally {
      elementDeepCheckPolling = false
    }
    scheduleElementDeepCheckPoll()
  }

  function handleStepElementCheckResult(result: any) {
    if (!result) return
    if (!elementDeepCheckSession.accept(result)) return
    clearElementDeepCheckTimer()
    elementDeepCheckLoading.value = false
    elementDeepCheckId.value = String(result.check_id || elementDeepCheckId.value)
    const finishedTaskId = elementDeepCheckTaskId.value
    const finishedElementId = elementDeepCheckElementId.value
    elementDeepCheckTaskId.value = ''
    elementDeepCheckElementId.value = null
    elementDeepCheckToken = null
    elementCheckApplied.value = false
    elementCheckResult.data = result
    elementCheckResult.title = `${
      result.check_mode === 'deep' ? '元素深度检测结果' : '元素检测结果'
    } / ${result.element_name || getElementName(data.selectData?.ele_name) || '页面元素'}`
    elementCheckResult.visible = true
    if (finishedElementId && finishedTaskId) {
      clearExecutorTaskObservation(
        'ui-step-element-check',
        finishedElementId,
        finishedTaskId
      )
    }
  }

  function handleStepElementCheckStarted(payload: any) {
    if (!elementDeepCheckLoading.value || elementDeepCheckToken == null) return
    if (
      elementDeepCheckElementId.value &&
      String(payload?.element_id || '') !== String(elementDeepCheckElementId.value)
    ) {
      return
    }
    // 工作区在实时组件准备完成后才确定，因此开始事件到达时补充到当前会话。
    elementDeepCheckSession.cancel(elementDeepCheckToken)
    elementDeepCheckToken = elementDeepCheckSession.start(
      payload?.element_id,
      payload?.workspace_id || ''
    )
  }

  async function applyStepElementDeepCheckUpdates() {
    if (elementCheckApplyLoading.value || elementCheckApplied.value) return
    const elementId = elementCheckResult.data?.element_id
    const taskId = String(elementCheckResult.data?.executor_task_id || '')
    if (!elementId || !taskId) return
    elementCheckApplyLoading.value = true
    try {
      const res = await putUiElementDeepCheckApply({ element_id: elementId, task_id: taskId })
      elementCheckApplied.value = true
      const slots = res.data?.applied_slots || []
      Message.success(slots.length ? `已写入第 ${slots.join('、')} 组定位` : res.msg)
      await handleElementSaved()
    } finally {
      elementCheckApplyLoading.value = false
    }
  }

  async function openSelectedElementAiHeal() {
    if (elementAiHealLoading.value) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    elementAiHealLoading.value = true
    try {
      const element = await loadSelectedNodeElement()
      if (!element) return
      await elementAiHealPanelRef.value?.open(element)
    } catch (error) {
      console.log(error)
      Message.error('AI自愈信息获取失败')
    } finally {
      elementAiHealLoading.value = false
    }
  }

  async function handleElementSaved() {
    doRefresh()
    await getEleName()
  }

  function hasRuntimeValue(value: unknown) {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
    return true
  }

  function normalizeRuntimeObject(value: unknown) {
    return hasRuntimeValue(value) ? value : {}
  }

  function getElementExpTitle(value: any) {
    return enumStore.element_exp.find((item: any) => item.key === value)?.title || value || '-'
  }

  onMounted(async () => {
    // 元素深度检测也会在用例详情嵌入的步骤半屏窗口中触发，
    // 因此结果监听不能跟随 caseInputMode 关闭；步骤执行消息仍由处理函数按运行态过滤。
    window.addEventListener('mango:websocket-message', handleStepResultMessage)
    await doRefreshSteps(currentPageStepsId.value)
    await loadDatasourceAliases()
    await doRefresh()
    await resumeActiveDebugTask()
    if (!props.caseInputMode) {
      await Promise.all([
        getEleName(),
        loadLatestStepExecutionResult().catch((error) => {
          console.log(error)
          return null
        }),
      ])
    }
    useSelectValue.getSelectValue()
  })

  watch(
    () => [props.caseData, props.caseResult],
    () => {
      if (props.caseInputMode) void doRefresh()
    },
    { deep: true }
  )

  // 外部（如用例详情页同步按钮）请求刷新：重拉页面步骤 flow_data 与配置面板数据
  watch(
    () => props.refreshToken,
    () => {
      if (props.refreshToken <= 0) return
      void doRefreshSteps(currentPageStepsId.value)
      void doRefresh()
    }
  )

  onBeforeUnmount(() => {
    window.removeEventListener('mango:websocket-message', handleStepResultMessage)
    stopDebugPolling()
    clearElementDeepCheckTimer()
    clearFlowSaveTimer()
  })
</script>
<style scoped>
  .page-steps-workbench-page {
    --steps-panel-gap: var(--m-page-gap);
    --steps-left-panel-width: 220px;
    --steps-right-panel-width: 400px;
    --steps-canvas-min-width: 420px;
  }

  .page-steps-workbench-page--compact {
    --steps-left-panel-width: 0px;
    --steps-right-panel-width: 460px;
    --steps-canvas-min-width: 560px;
  }

  .page-steps-workbench-page--compact .steps-workbench {
    grid-template-columns:
      minmax(var(--steps-canvas-min-width), 1fr)
      var(--steps-right-panel-width);
  }

  .page-steps-workbench-page--embedded-scroll {
    flex: 1 1 auto;
    height: auto;
    min-height: 0;
    overflow: hidden;
  }

  .page-steps-workbench-page--embedded-scroll :deep(.arco-card-body) {
    display: flex;
    min-height: 0;
    overflow: hidden;
  }

  .page-steps-workbench-page--embedded-scroll :deep(.mango-table-body__content) {
    display: flex;
    min-height: 0;
    flex-direction: column;
  }

  .page-steps-workbench-page--embedded-scroll .steps-workbench {
    height: auto;
    min-height: 0;
    flex: 1;
  }

  .steps-workbench {
    display: grid;
    grid-template-columns:
      minmax(
        calc(
          var(--steps-left-panel-width) + var(--steps-panel-gap) + var(--steps-canvas-min-width)
        ),
        1fr
      )
      var(--steps-right-panel-width);
    gap: var(--steps-panel-gap);
    overflow-x: auto;
  }

  .steps-live-debug-area {
    position: relative;
    display: flex;
    min-height: min(760px, calc(100vh - 128px));
    margin-top: var(--steps-panel-gap);
    flex-direction: column;
    overflow: hidden;
  }

  .steps-live-debug-panel {
    flex: 1;
    min-height: 0;
  }

  .steps-live-debug-area :deep(.mango-ui-live-workbench-panel) {
    height: 100%;
    min-height: 0;
    grid-template-columns: minmax(0, 3fr) minmax(360px, 1.25fr);
    background: var(--m-bg-soft);
    gap: var(--steps-panel-gap);
  }

  .steps-live-debug-area :deep(.mango-ui-live-workbench-panel__stage) {
    padding: 0;
    gap: var(--steps-panel-gap);
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .steps-live-debug-area :deep(.mango-ui-live-workbench-panel__tools) {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .steps-flow-area {
    width: 100%;
    min-width: 0;
    min-height: 0;
  }

  .inspector-panel {
    display: flex;
    flex-direction: column;
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    overflow: hidden;
  }

  .inspector-panel {
    width: var(--steps-right-panel-width);
    min-width: var(--steps-right-panel-width);
    max-width: var(--steps-right-panel-width);
  }

  .panel-head {
    display: flex;
    flex: none;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .panel-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .panel-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .inspector-head {
    align-items: flex-start;
  }

  .inspector-head-actions {
    display: flex;
    flex: none;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 6px;
  }

  .inspector-content {
    flex: 1;
    height: auto;
    min-height: 0;
    overflow: hidden;
  }

  .node-details {
    padding: 12px;
  }

  .inspector-section + .inspector-section {
    margin-top: 10px;
  }

  .mango-section-title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 18px;
  }

  .detail-item {
    margin-bottom: 12px;
    font-size: 13px;
    padding: 0;
  }

  .detail-item label {
    flex: 0 0 60px;
    color: var(--m-text-2);
    font-weight: 500;
  }

  .detail-item span {
    color: var(--m-text);
  }

  .detail-item > div > div > div > span:last-child {
    color: var(--m-text);
    word-break: break-all;
  }

  .node-section-card {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .node-section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
  }

  .node-section-head .mango-section-title {
    margin-bottom: 0;
  }

  .node-summary-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .node-summary-grid > div {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
    padding: 5px 8px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .node-summary-grid span,
  .node-param-item span,
  .element-result-row span {
    display: block;
    flex: 0 0 auto;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 16px;
  }

  .node-summary-grid strong,
  .node-param-item strong,
  .element-result-row strong {
    display: block;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    line-height: 18px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    word-break: break-word;
  }

  .node-summary-wide {
    grid-column: 1 / -1;
  }

  .node-param-list {
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
    margin-top: 8px;
  }

  .node-param-item {
    display: flex;
    align-items: flex-start;
    min-width: 0;
    gap: 6px;
    padding: 5px 8px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .node-runtime-error {
    margin-top: 10px;
    padding: 8px 10px;
    color: var(--m-danger);
    font-size: 12px;
    line-height: 18px;
    word-break: break-word;
    border: 1px solid color-mix(in srgb, var(--m-danger) 34%, var(--m-border));
    border-radius: var(--m-radius-sm);
    background: color-mix(in srgb, var(--m-danger) 7%, var(--m-surface));
  }

  .element-result-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 10px;
  }

  .element-result-card {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .element-result-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-width: 0;
    gap: 8px;
    margin-bottom: 8px;
  }

  .element-result-head strong {
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .element-result-row + .element-result-row {
    margin-top: 8px;
  }

  .locator-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 4px;
  }

  .locator-item {
    min-width: 0;
    padding: 7px 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .locator-item span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .locator-item strong {
    display: block;
    margin-top: 2px;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    line-height: 18px;
    word-break: break-all;
  }

  .locator-sub {
    display: inline-block;
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
    font-style: normal;
    line-height: 18px;
  }

  .runtime-shot {
    margin-top: 10px;
  }

  .runtime-shot-head {
    margin-bottom: 6px;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 600;
    line-height: 18px;
  }

  .element-summary {
    margin-bottom: 10px;
    padding: 10px 12px;
    background: var(--m-surface-soft);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
  }

  .element-summary__title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-weight: 600;
  }

  .element-summary__rows {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .element-summary__row {
    display: grid;
    grid-template-columns: 76px minmax(0, 1fr);
    gap: 8px;
    line-height: 18px;
  }

  .element-summary__row span:first-child {
    color: var(--m-muted);
  }

  .element-summary__row span:last-child {
    min-width: 0;
    color: var(--m-text);
    word-break: break-word;
  }

  .config-editor > div {
    padding: 0 !important;
  }

  .node-config-form {
    width: 100%;
  }

  .node-config-form :deep(.arco-form-item) {
    display: grid;
    grid-template-columns: 60px minmax(0, 1fr);
    align-items: flex-start;
    width: 100%;
    gap: 4px;
    margin-bottom: 6px;
  }

  .node-config-form :deep(.arco-form-item-label-col) {
    flex: none;
    width: 60px;
    padding: 5px 0 0;
    text-align: right;
  }

  .node-config-form :deep(.arco-form-item-label) {
    justify-content: flex-end;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }

  .node-config-form :deep(.arco-form-item-wrapper-col) {
    flex: 1 1 auto;
    min-width: 0;
    width: 100%;
  }

  .node-config-form :deep(.arco-form-item-content),
  .node-config-form :deep(.arco-form-item-content-flex) {
    min-width: 0;
    width: 100%;
  }

  .node-config-form :deep(.arco-input-wrapper),
  .node-config-form :deep(.arco-select-view),
  .node-config-form :deep(.arco-cascader-view),
  .node-config-form :deep(.arco-textarea-wrapper),
  .node-config-form :deep(.code-editor) {
    width: 100%;
  }

  .case-inherited-config {
    display: flex;
    min-width: 0;
    width: 100%;
    min-height: 32px;
    padding: 4px 8px;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .case-inherited-config__value {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .case-inherited-config :deep(.arco-tag) {
    flex: none;
  }

  .empty-hint {
    padding: 18px 12px;
    color: var(--m-muted);
    text-align: center;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .no-selection {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 280px;
    padding: 48px 24px;
    text-align: center;
  }

  .no-selection-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .no-selection-desc {
    max-width: 260px;
    margin-top: 6px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .form-actions {
    margin-top: 16px;
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .mango-ui-step-cache-panel {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    padding: 0;
  }

  .mango-ui-step-result-loading {
    display: block;
    width: 100%;
  }

  .mango-ui-step-page-elements-panel {
    display: flex;
    flex: 1 1 auto;
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .mango-ui-step-page-elements-panel :deep(.mango-detail-workbench-page) {
    flex: 1 1 auto;
    height: 100%;
    min-height: 0;
  }

  .mango-ui-step-cache-section {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-ui-step-cache-section__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }

  .mango-ui-step-cache-section__head strong {
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-ui-step-cache-section__head span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-align: right;
  }

  :deep(.arco-form-item) {
    margin-bottom: 12px;
  }

  @media (max-width: 1px) {
    .steps-flow-area {
      min-height: 560px;
    }

    .inspector-panel {
      flex: none;
      min-width: 0;
      min-height: 520px;
    }
  }
</style>
