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
          <a-button  size="small" :loading="browserOpening" @click="onOpenStepBrowser" data-testid="qa-views-uitest-page-steps-details-button-打开浏览器">
            <template #icon><icon-desktop /></template>
            打开浏览器
          </a-button>
          <a-button  size="small" status="success" :loading="caseRunning" @click="onRunCase" data-testid="qa-views-uitest-page-steps-details-button-调试">
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

      <a-alert v-if="actionError || flowSave.error.value || elementChecks.error.value || stepDebug.error.value" type="error">{{ actionError || flowSave.error.value || elementChecks.error.value || stepDebug.error.value }}</a-alert>

      <a-spin v-if="stepResources.loading.steps" :size="scaleDensityPixels(16)" tip="加载步骤配置" />
      <a-spin v-if="stepResources.loading.aliases" :size="scaleDensityPixels(16)" tip="加载逻辑数据源" />
      <a-spin v-if="stepResources.loading.elements" :size="scaleDensityPixels(16)" tip="加载元素" />
      <a-spin v-if="stepResources.loading.details" :size="scaleDensityPixels(16)" tip="加载节点" />





      <div class="mango-workbench-scroll-x mango-ui-step-layout">
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
          :table-data="nodeDetails"
          :node-types="nodeTypes"
          :readonly="caseInputMode || canvasBusy || debugRunning"
          :context-key="[currentPageStepsId, props.caseId, props.caseStepId, userStore.selected_environment].join(':')"
          :before-node-delete="onNodeDelete"
          :compact="compact"
          :show-step-detail-action="caseInputMode"
          :show-cache-data-action="caseInputMode"
          :allow-drop="!caseInputMode"
          :healing-enabled="Boolean(currentStepRecord?.healing_enabled)"
          :healing-goal="currentStepRecord?.goal || ''"
          :healing-pending-review-count="pendingHealingReviewNodes.length"
          :healing-review-confirming="healingReviewConfirming"
          :result-data="runtimeResult"
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

          @node-duplicate="onNodeDuplicate"
          @canvas-beautify="beautifyCanvas"
          @canvas-save="saveFlow"
          @control-change="onStepControlChange"
          @open-step-detail="emit('openPageStepDetail')"
          @open-cache-data="emit('openCacheData')"
          @open-step-healing="openHealing"
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
                    <strong>{{ nodeDraft.id ?? '-' }}</strong>
                  </div>
                  <div>
                    <span>类型</span>
                    <strong>{{ getNodeTypeLabel(nodeDraft.type) }}</strong>
                  </div>
                  <div>
                    <span>方法</span>
                    <strong>{{ getMethodLabel(nodeDraft.ope_key) }}</strong>
                  </div>
                  <div>
                    <span>参数数</span>
                    <strong>{{ getConfigParamCount(nodeDraft) }}</strong>
                  </div>
                  <div
                    v-if="getElementName(nodeDraft.ele_name) !== '-'"
                    class="node-summary-wide"
                  >
                    <span>元素名称</span>
                    <strong>{{ getElementName(nodeDraft.ele_name) }}</strong>
                  </div>
                  <div
                    v-if="getConditionSummary(nodeDraft.condition_value) !== '-'"
                    class="node-summary-wide"
                  >
                    <span>条件</span>
                    <strong>{{ getConditionSummary(nodeDraft.condition_value) }}</strong>
                  </div>
                </div>
                <div v-if="getConfigParamSummary(nodeDraft).length" class="node-param-list">
                  <div
                    v-for="param in getConfigParamSummary(nodeDraft)"
                    :key="param.key"
                    class="node-param-item"
                  >
                    <span>{{ param.label }}</span>
                    <strong>{{ param.value }}</strong>
                  </div>
                </div>
              </section>

              <section class="inspector-section node-section-card config-editor">
                <div v-if="nodeFields.length > 0 || nodeType === 2">
                  <div class="node-section-head">
                    <div class="mango-section-title">编辑配置</div>
                    <a-space :size="6">
                      <a-button
                        v-if="nodeType === 2 && !configFormReadonly"
                        size="mini"
                        @click="addSqlOperation" data-testid="qa-views-uitest-page-steps-details-button-新增操作"
                      >
                        新增操作
                      </a-button>
                      <a-button
                        v-if="!caseInputMode || hasCaseEditableConfigItems"
                        size="mini"
                        type="primary"
                        :loading="caseInputMode ? caseNodeInputs.saving.value : formSaving"
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
                  <a-alert v-if="caseNodeInputs.error.value" type="error">
                    {{ caseNodeInputs.error.value }}
                  </a-alert>
                  <TipMessage
                    v-if="conditionTipMessage"
                    :message="conditionTipMessage"
                    margin-bottom="8px"
                  />

                  <DataSourceOperationList
                    v-if="nodeType === 2"
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
                    :element-options="elementOptions"
                    :element-cascader-options="elementCascaderOptions"
                    :file-options="uiTestFileOptions"
                    :file-loading="uiTestFileLoading"
                    :datasource-options="sqlAssertionDatasourceOptions"
                    :is-item-disabled="isConfigItemDisabled"
                    :is-item-inherited="isCaseInheritedConfigItem"
                    :get-inherited-value="getCaseInheritedConfigValue"
                    class="node-config-form"
                    @method-change="upDataOpeValue"
                    @update-field="updateNodeField"
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
                    :result="selectedRuntimeResult"
                    :fallback-ope-key="nodeDraft.ope_key"
                    :fallback-element-name="getElementName(nodeDraft.ele_name)"
                    :fallback-element="nodeDraft.ele_name"
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
          @step-debug-started="stepDebug.acceptWorkspace"
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
        v-if="pageElementsPanel.visible && currentPageId !== ''"
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
    :context-key="[currentPageStepsId, selectedNode?.id].join(':')"
    ref="elementEditPanelRef"
    :operation-options="useSelectValue.getOperationOptions(currentPageType)"
    @saved="handleElementSaved"
  />
  <UiElementAiHealPanel
    :context-key="[currentPageStepsId, selectedNode?.id].join(':')"
    ref="elementAiHealPanelRef"
    :test-env="userStore.selected_environment"
    @applied="handleElementSaved"
  />
  <UiElementDeepCheckVariablesDialog :key="[currentPageStepsId, selectedNode?.id].join(':')" ref="deepCheckVariablesDialogRef" />
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
    :element-options="elementOptions"
    @update:visible="healingPanelVisible = $event"
    @changed="doRefreshSteps(currentPageStepsId)"
  />
</template>
<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { IconDesktop } from '@arco-design/web-vue/es/icon'
  import FlowChart from './FlowChart.vue'
  import type { UIEdge, UiStepControl } from '@/types/components'
  import { createNodeDraft, readStepDetail, readStepRecord, readStepFlow, readStepResult, stepResponse, stepArray, defaultStepControl, requiredStepId, readStepFiles, type StepDetail, type StepElement, type StepField, type StepId, type StepRecord, type StepResult, type StepFlow as FlowData, type StepNode as UINode, type StepSql, type StepDatasource, type StepFileOption, type StepCanvasPort } from '@/components/business/ui-page-step'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import type { UiPageStepsDetailPayload } from '@/types/ui-test/case'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { createNodeFields, isEmptyStepField } from './config'
  import {
    deleteUiPageStepsDetailed,
    getUiPageStepsDetailed,
    getUiPageStepsDetailedById,
    postUiPageStepNodeCopy,
    postUiPageStepsDetailed,
  } from '@/api/uitest/page-steps-detailed'
  import {
    getUiSteps,
    postUiPageStepHealApply,
    postUiPageStepOpenBrowser,
  } from '@/api/uitest/page-steps'
  import { useCaseNodeInputs } from '@/views/uitest/case/details/composables/useCaseNodeInputs'
  import { useStepResources } from './composables/useStepResources'
  import { uiCaseAssetId, uiCaseAssetObject } from '@/components/business/ui-case-step-create'
  import type { CaseNodeInputContext } from '@/views/uitest/case/details/case-node-inputs'
  import {
    getUiUiElementName,
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
  import { useElementChecks, type ElementWorkbenchPort } from '@/hooks/use-ui-element-checks'
  import { liveId, liveObject } from '@/components/business/ui-live-workbench'
  import UiStepRuntimeResult from '@/components/reports/UiStepRuntimeResult.vue'
  import { Scrollbar } from '@/components/Scrollbar'
  import PageElements from '@/views/uitest/page/elements/index.vue'
  import { useUiLiveWorkbench } from '@/hooks/use-ui-live-workbench'
  import { useStepFlowSave } from './composables/useStepFlowSave'
  import { useStepDebug } from './composables/useStepDebug'
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
    checkElementInWorkspace: ElementWorkbenchPort['checkElementInWorkspace']
    acceptElementCheckResult: ElementWorkbenchPort['acceptElementCheckResult']
  } | null>(null)
  const methodsLoading = ref(false), methodsError = ref('')
  let methodsSequence = 0
  async function loadMethods() {
    const current = stepResources.capture(), sequence = ++methodsSequence
    methodsLoading.value = true; methodsError.value = ''
    try { await Promise.all([useSelectValue.getSelectValue(), enumStore.getEnum()]); if (current() && sequence === methodsSequence && selectedNode.value) onNodeClick(selectedNode.value) }
    catch (loadFailure0) { if (current() && sequence === methodsSequence) (reportLoadError(loadFailure0, "操作和断言定义加载失败，请重试", false), methodsError.value = '操作和断言定义加载失败，请重试') }
    finally { if (current() && sequence === methodsSequence) methodsLoading.value = false }
  }
  const actionError = ref('')
  const elementEditLoading = ref(false)
  let elementSelectionVersion = 0
  const elementAiHealLoading = ref(false)
  const healingPanelVisible = ref(false)
  const healingReviewConfirming = ref(false)
  const flowChartRef = ref<StepCanvasPort | null>(null)
  const selectedNode = ref<UINode | null>(null)

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
  const currentStepRecord = ref<StepRecord | null>(null)
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
    close: closeStepLiveWorkbench,
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
      caseData?: unknown[]
      caseResult?: unknown
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
    (event: 'caseDataSaved', value: unknown[], context: CaseNodeInputContext): void
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

  function inputStepId(value: unknown) { try { return uiCaseAssetId(value) } catch { return null } }
  const currentPageStepsId = computed(
    () => props.pageStepsId !== '' ? inputStepId(props.pageStepsId) ?? '' : Object.prototype.hasOwnProperty.call(route.query, 'id') ? inputStepId(route.query.id) ?? '' : inputStepId(bootstrapStep.value.id) ?? ''
  )
  const bootstrapStep = computed(() => pageData.record ? uiCaseAssetObject(pageData.record) : {})
  const bootstrapProduct = computed(() => {
    const value = bootstrapStep.value.project_product
    return value && typeof value === 'object' ? uiCaseAssetObject(value).id : value
  })
  const currentPageId = computed(
    () => props.pageId !== '' ? inputStepId(props.pageId) ?? ''
      : Object.prototype.hasOwnProperty.call(route.query, 'pageId') ? inputStepId(route.query.pageId) ?? ''
      : inputStepId(currentStepRecord.value?.page?.id) ?? inputStepId(currentStepRecord.value?.page) ?? ''
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
      inputStepId(props.pageType) ??
        inputStepId(route.query.pageType) ??
        currentStepRecord.value?.project_product?.ui_client_type ??
        '0'
    )
  )
  const currentProjectProductId = computed(
    () =>
      uiCaseAssetId(currentStepRecord.value?.project_product?.id) ??
      uiCaseAssetId(currentStepRecord.value?.project_product) ??
      uiCaseAssetId(bootstrapProduct.value) ??
      ''
  )
  const stepsTitle = computed(() => {
    const record = currentStepRecord.value
    const id = record?.id ?? currentPageStepsId.value ?? '-'
    const name = record?.name || bootstrapStep.value.name || '-'
    return `页面步骤工作台 / ${id} / ${name}`
  })
  const pendingHealingReviewNodes = computed(() =>
    (flowData.value.nodes || []).filter((node) => {
      const config = node?.config || {}
      return config.ai_healed && config.ai_review_status !== 'confirmed'
    })
  )
  const pendingHealingRecordIds = computed(() =>
    Array.from(
      new Set(
        pendingHealingReviewNodes.value
          .map((node) => node?.config?.ai_heal_record_id)
          .filter((recordId) => recordId !== null && recordId !== undefined && recordId !== '')
          .map(String)
      )
    )
  )
  const elementCascaderOptions = computed(() => buildElementCascaderOptions(elementOptions.value))

  const nodeDetails = ref<StepDetail[]>([])
  const nodeDraft = ref<StepDetail>(createNodeDraft())
  const elementOptions = ref<StepElement[]>([])
  const nodeType = ref(0), hasPreviousCondition = ref(false), previousConditionId = ref<StepId | null>(null), previousConditionNodeId = ref('')
  const runtimeResult = ref<StepResult>(readStepResult(null)), selectedRuntimeResult = ref<StepResult | null>(null)
  const nodeFields = ref<StepField[]>([]), requiresBranchValue = ref(false)
  const browserOpening = ref(false)
  const runtimeResultRenderRevision = ref(0)
  const formSaving = ref(false)
  const dataSourceOperationListRef = ref<{ validate: () => boolean } | null>(null)
  const sqlOperationRows = ref<StepSql[]>([])
  const datasourceAliasOptions = ref<StepDatasource[]>([])
  const sqlAssertionDatasourceOptions = computed(() =>
    datasourceAliasOptions.value.filter((item) => [0, 1, 2].includes(Number(item.dbType)))
  )
  const configEditing = ref(false)
  const nodeDuplicating = ref(false), nodeDeleting = ref(false)
  const canvasBusy = computed(() => formSaving.value || nodeDuplicating.value || nodeDeleting.value || healingReviewConfirming.value || flowSaving.value)
  const nodeFormDrafts = reactive(new Map<string, Record<string, unknown>>())
  const caseNodeInputs = useCaseNodeInputs({
    enabled: () => props.caseInputMode,
    caseId: () => props.caseId,
    caseStepId: () => props.caseStepId,
    pageStepId: () => props.pageStepsId,
    nodeId: () => nodeDraft.value?.id,
    selection: () => selectedNode.value?.id,
    data: () => props.caseData,
    saved(values, context) {
      nodeDetails.value = normalizeCaseData(values)
      if (selectedNode.value) {
        nodeFormDrafts.delete(selectedNode.value.id)
        setSelectData(selectedNode.value)
      }
      configEditing.value = false
      emit('caseDataSaved', values, context)
    },
  })
  const uiTestFileOptions = ref<StepFileOption[]>([])
  const uiTestFileLoading = computed(() => stepResources.loading.files)
  const stepCachePanel = reactive({
    visible: false,
  })
  const pageElementsPanel = reactive({
    visible: false,
  })
  const stepResources = useStepResources({
    enabled: () => true,
    context: () => [props.pageStepsId, props.pageId, props.caseId, props.caseStepId, props.caseInputMode, route.query.id, props.refreshToken],
    invalidated() {
      invalidateElementContext()
      currentStepRecord.value = null
      flowData.value = { nodes: [], edges: [] }
      nodeDetails.value = []
      selectedNode.value = null
      nodeFormDrafts.clear()
      datasourceAliasOptions.value = []
      elementOptions.value = []
      flowSave.invalidate()
      stepCachePanel.visible = false
      pageElementsPanel.visible = false
      healingPanelVisible.value = false
      elementCheckResult.visible = false
      methodsSequence++; methodsLoading.value = false; methodsError.value = ''
      actionError.value = ''
      uiTestFileOptions.value = []
      replaceRuntimeResult(null)
      nodeDraft.value = createNodeDraft()
      nodeFields.value = []
      configEditing.value = false
      closeStepLiveWorkbench()
      stepDebug.invalidate()

    },
    resume: () => { void initializeStep() },
  })
  const flowSave = useStepFlowSave({ capture: () => stepResources.capture(), id: () => uiCaseAssetId(currentPageStepsId.value), enabled: () => !props.caseInputMode, flow: () => flowData.value, reconcile: id => { void doRefreshSteps(id) } })
  const flowSaving = flowSave.saving, flowSaveStatus = flowSave.status, flowRevision = flowSave.revision, savedFlowRevision = flowSave.savedRevision
  const stepDebug = useStepDebug({ capture: () => stepResources.capture(), id: () => uiCaseAssetId(currentPageStepsId.value), environment: () => liveId(userStore.selected_environment), owner: () => JSON.stringify([userStore.userId, userStore.roleId, userStore.selected_environment]), control: () => stepControl.value, count: () => executableNodeCount.value,
    ready: async () => !props.caseInputMode && !canvasBusy.value && checkNodeConnections() && checkNodeConfigSaved() && await ensureFlowSavedForRun(), workspace: () => liveWorkbenchVisible.value, startWorkspace: id => liveWorkbenchPanelRef.value?.startStepDebug(id) ?? Promise.resolve(false),
    result: replaceRuntimeResult, status: value => { if (currentStepRecord.value) currentStepRecord.value.status = value }, refresh: async () => { await doRefreshSteps(currentPageStepsId.value); await doRefresh() },
  })
  const caseRunning = stepDebug.submitting, singleStepRunning = stepDebug.singleSubmitting, debugRunning = stepDebug.running, debugCompleted = stepDebug.completed, debugRefreshError = computed(() => Boolean(stepDebug.error.value)), latestResultLoading = stepDebug.resultLoading
  const elementChecks = useElementChecks({ scope: { available: () => stepResources.capture()(), capture: captureElementContext }, pageId: () => liveId(currentPageId.value), environment: () => liveId(userStore.selected_environment), owner: () => JSON.stringify([userStore.userId, userStore.roleId, userStore.selected_environment]), pageUrl: () => currentPageInfo.value.url,
    rows: () => elementOptions.value.flatMap(row => row.id == null ? [] : [{ id: row.id, name: row.name }]), liveVisible: () => liveWorkbenchVisible.value, workbench: () => liveWorkbenchPanelRef.value,
    variables: record => deepCheckVariablesDialogRef.value?.open(record) ?? Promise.resolve(null), applyRuntime: () => {}, refresh: handleElementSaved,
  })
  const elementPreparing = ref(false)
  const elementCheckResult = elementChecks.result, elementCheckApplyLoading = elementChecks.applying, elementCheckApplied = elementChecks.applied, elementDeepCheckLoading = computed(() => elementPreparing.value || elementChecks.busy.value)
  function invalidateElementContext() {
    elementSelectionVersion++
    elementChecks.invalidate()
  }
  watch(() => selectedNode.value?.id, invalidateElementContext, { flush: 'sync' })
  function captureElementContext() {
    const current = stepResources.capture(), revision = elementSelectionVersion
    return () => current() && revision === elementSelectionVersion
  }
  async function refreshEmbeddedStep() {
    const current = stepResources.capture()
    await doRefreshSteps(currentPageStepsId.value)
    if (!current()) return
    await loadDatasourceAliases()
    if (!current()) return
    await doRefresh()
  }
  const currentStepCacheData = computed(() =>
    normalizeRuntimeObject(runtimeResult.value?.cache_data)
  )
  const selectedConfigSaved = computed(() =>
    uiCaseAssetId(nodeDraft.value?.id) !== null || uiCaseAssetId(selectedNode.value?.config?.id) !== null
  )
  const hasSelectedNodeElement = computed(() => {
    if (uiCaseAssetId(nodeDraft.value?.id) === null) return false
    const elementId = getElementIdFromCascader(nodeDraft.value?.ele_name)
    if (elementId !== null && elementId !== undefined && elementId !== '') return true
    // Case 缓存只保存页面步骤绑定元素的名称；真正操作时仍按步骤明细 ID
    // 读取最新元素，兼容存量 Case 缓存且避免仅因缺少元素 ID 隐藏操作入口。
    return props.caseInputMode && getElementName(nodeDraft.value?.ele_name) !== '-'
  })
  const selectedNodeSupportsSingleStep = computed(() =>
    [0, 1, 2, 3, 5, 6].includes(Number(selectedNode.value?.type))
  )
  const configFormReadonly = computed(() => selectedConfigSaved.value && !configEditing.value)
  const configActionText = computed(() => (configFormReadonly.value ? '编辑' : '保存'))
  const hasCaseEditableConfigItems = computed(
    () => nodeType.value === 2 || nodeFields.value.some((item) => !isCaseInheritedConfigItem(item))
  )

  function isCaseInheritedConfigItem(item) {
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

  function getCaseInheritedConfigValue(item) {
    if (String(item?.key || '') === 'ope_key') {
      return getMethodLabel(item?.value || nodeDraft.value?.ope_key)
    }
    const elementName = getElementName(nodeDraft.value?.ele_name)
    if (elementName !== '-') return elementName
    return getElementName(item?.value)
  }

  function isConfigItemDisabled(item) {
    if (configFormReadonly.value || formSaving.value || caseNodeInputs.saving.value || methodsLoading.value || debugRunning.value) return true
    if (!props.caseInputMode) return false
    return isCaseInheritedConfigItem(item)
  }
  const selectedMethodKey = computed(
    () =>
      String(nodeFields.value.find((item) => item.key === 'ope_key')?.value ||
      nodeDraft.value?.ope_key ||
      '')
  )
  const selectedMethodDefinition = computed(() =>
    useSelectValue.findItemByValue(selectedMethodKey.value)
  )
  const isExcelAssertionMethod = computed(() =>
    String(selectedMethodKey.value || '').startsWith('assert_excel_')
  )
  const excelActualFormItem = computed(() =>
    nodeFields.value.find((item) => item.key === 'actual-ope_value')
  )
  const excelExpectFormItem = computed(() =>
    nodeFields.value.find((item) => item.key === 'expect-ope_value')
  )
  const visibleFormItems = computed(() => {
    if (!isExcelAssertionMethod.value) return nodeFields.value
    return nodeFields.value.filter(
      (item) => !['actual-ope_value', 'expect-ope_value'].includes(item.key)
    )
  })

  function updateExcelFormItem(field: 'actual' | 'expect', value: string) {
    const item = field === 'actual' ? excelActualFormItem.value : excelExpectFormItem.value
    if (item) item.value = value
  }
  function updateNodeField(key: string, value: unknown) {
    const field = nodeFields.value.find(field => field.key === key)
    if (field && !isConfigItemDisabled(field)) field.value = cloneDraftValue(value)
  }
  const selectedMethodRequiresBranchValue = computed(() =>
    (useSelectValue.findItemByValue(selectedMethodKey.value)?.parameter || []).some(
      (item) => item.f === 'expect'
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
    if (hasPreviousCondition.value) {
      return requiresBranchValue.value
        ? '请输入当前分支的判断值；判断成立时将执行该分支。'
        : '上一个判断节点返回 True 时走第一条线，返回 False 时走第二条线。'
    }
    if (nodeType.value !== 4 || !selectedMethodKey.value) return ''
    return selectedMethodRequiresBranchValue.value
      ? '该方法需要判断值。保存判断节点后，请点击每个后续分支节点填写对应的判断值。'
      : '该方法无需填写判断值：成立时走 True 分支，不成立时走 False 分支。'
  })

  function openPageElementsPanel() {
    if (currentPageId.value === '') {
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
    Array.isArray(runtimeResult.value?.element_result_list) ? runtimeResult.value.element_result_list : []
  )
  const executableNodeCount = computed(() => {
    const savedNodeCount = flowData.value.nodes.filter((node) => node.config?.id != null).length
    return savedNodeCount || nodeDetails.value.length || 0
  })
  const stepStatusText = computed(() => {
    if (debugRefreshError.value) return '结果刷新异常，正在重试'
    if (debugRunning.value) {
      return `调试中 · 已回传 ${runtimeResultList.value.length}`
    }
    const status = Number(
      props.caseInputMode ? readStepResult(props.caseResult).status : currentStepRecord.value?.status
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
      props.caseInputMode ? readStepResult(props.caseResult).status : currentStepRecord.value?.status
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

  const clearFlowSaveTimer = flowSave.cancelTimer, markFlowSaved = flowSave.markSaved, scheduleFlowSave = flowSave.schedule
  const persistFlow = (_manual = false) => flowSave.persist()
  const saveFlow = () => { void flowSave.persist() }

  async function ensureFlowSavedForRun() {
    if (
      flowSaveStatus.value !== 'saved' ||
      flowRevision.value !== savedFlowRevision.value ||
      flowSaving.value
    ) {
      await persistFlow(false)
    }
    if (flowSaveStatus.value === 'saved' && flowRevision.value === savedFlowRevision.value) return true
    Message.error('画布尚未保存成功，请点击“重试保存”后再调试')
    return false
  }

  function setSelectData(node: UINode) {
    nodeDraft.value = createNodeDraft()
    nodeDetails.value.forEach((item) => {
      if (String(item.id) === String(node.config?.id)) {
        nodeDraft.value = {
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
    const selectedStepId = nodeDraft.value?.id
    if (selectedStepId === undefined || selectedStepId === null) {
      selectedRuntimeResult.value = null
      return
    }
    selectedRuntimeResult.value =
      runtimeResultList.value.find((item) => String(item.id) === String(selectedStepId)) || null
  }

  function replaceRuntimeResult(result: unknown) {
    runtimeResult.value = readStepResult(result)
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
      nodeDetails.value = normalizeCaseData(props.caseData)
      replaceRuntimeResult(props.caseResult)
      return Promise.resolve()
    }
    if (currentPageStepsId.value === '') return Promise.resolve(false)
    return stepResources.read('details', () => getUiPageStepsDetailed(currentPageStepsId.value), (res) => {
        nodeDetails.value = stepArray(stepResponse(res)).map(readStepDetail)
        if (selectedNode.value) setSelectData(selectedNode.value)
      })
  }

  function normalizeCaseData(items: unknown[] = []) {
    return (Array.isArray(items) ? items : []).map(uiCaseAssetObject).map((item) => {
      const detail = readStepDetail({
        id: item.page_step_details_id,
        type: item.type,
        ope_key: item.ope_key,
        condition_value: item.condition_value,
        ele_name: item.page_step_details_name ? { name: item.page_step_details_name } : null,
      })
      if ([0, 1, 4, 6].includes(Number(item.type))) {
        detail.ope_value = readStepDetail({ ope_value: item.page_step_details_data || [] }).ope_value
      } else if (Number(item.type) === 2) {
        detail.sql_execute = readStepDetail({ sql_execute: item.page_step_details_data || [] }).sql_execute
      } else if (Number(item.type) === 3) {
        detail.custom = readStepDetail({ custom: item.page_step_details_data || [] }).custom
      } else if (Number(item.type) === 5) {
        const rows = Array.isArray(item.page_step_details_data) ? item.page_step_details_data : []
        detail.func = rows.length ? String(uiCaseAssetObject(rows[0]).func ?? '') : ''
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
    const projectProduct = currentProjectProductId.value
    if (projectProduct === '') return
    return stepResources.read('aliases', async () => {
      const res = await getDataFactoryDatasourceAlias({
        project_product: projectProduct,
        status: 1,
        page: 1,
        pageSize: 999,
      })
      if (!Array.isArray(res.data)) throw Error('Invalid datasource aliases')
      return res.data.map(uiCaseAssetObject).map(item => ({ label: String(item.name ?? ''), value: requiredStepId(item.id), dbType: Number(item.db_type) }))
    }, values => { datasourceAliasOptions.value = values })
  }

  function getEleName() {
    const pageId = currentPageId.value
    if (pageId === '') return Promise.resolve(false)
    return stepResources.read('elements', () => getUiUiElementName(pageId), (res) => {
        elementOptions.value = stepArray(stepResponse(res)).map(value => readStepDetail({ ele_name: value }).ele_name).filter((value): value is StepElement => value !== null)
        if (nodeDraft.value.id !== null && nodeFields.value.length && !configEditing.value) formFeedback()
      })
  }

  function buildElementCascaderOptions(elements: StepElement[] = []) {
    const groups = new Map<string, Array<{ label: string; value: StepId; expected_event: StepElement['expected_event'] }>>()
    elements.forEach(element => {
      if (element.id == null) return
      const category = element.category || '未分类'
      if (!groups.has(category)) groups.set(category, [])
      groups.get(category)?.push({ label: element.name || '', value: element.id, expected_event: element.expected_event })
    })
    return Array.from(groups.entries()).map(([category, children]) => ({ label: category, value: category, children }))
  }

  function getElementIdFromCascader(value: unknown): StepId | null {
    if (Array.isArray(value)) return uiCaseAssetId(value[value.length - 1])
    if (value && typeof value === 'object') return uiCaseAssetId(liveObject(value).id)
    return uiCaseAssetId(value)
  }

  function getElementCascaderValue(value: unknown) {
    const elementId = getElementIdFromCascader(value)
    if (elementId == null || elementId === '') return ''
    const element = elementOptions.value.find((item) => String(item.id) === String(elementId))
    if (!element) return value
    return [element.category || '未分类', element.id]
  }

  function findExpectedEventByElementValue(value: unknown) {
    const elementId = getElementIdFromCascader(value)
    if (elementId == null || elementId === '') return null
    return (
      elementOptions.value.find((item) => String(item.id) === String(elementId))?.expected_event ||
      null
    )
  }

  function presetOpeValueValue(presetValues: StepDetail['ope_value'] = [], key: string, fallback: unknown) {
    const preset = presetValues.find((item) => item?.f === key)
    return preset && Object.prototype.hasOwnProperty.call(preset, 'v') ? preset.v : fallback
  }

  function onElementCascaderChange(value: unknown) {
    if (nodeType.value !== 0 || configFormReadonly.value) return
    const expectedEvent = findExpectedEventByElementValue(value)
    if (!expectedEvent?.ope_key) return
    const opeKeyItem = nodeFields.value.find((item) => item.key === 'ope_key')
    if (!opeKeyItem) return
    opeKeyItem.value = expectedEvent.ope_key
    upDataOpeValue(expectedEvent.ope_key, expectedEvent.ope_value || [])
  }

  function upDataOpeValue(value: unknown, presetValues: StepDetail['ope_value'] = []) {
    const method = typeof value === 'string' ? value : Array.isArray(value) ? String(value[value.length - 1] ?? '') : ''
    const inputItem = useSelectValue.findItemByValue(method)
    for (let i = nodeFields.value.length - 1; i >= 0; i--) {
      let key = nodeFields.value[i].key
      if (!['condition_value', 'ope_key', 'ele_name'].includes(key)) {
        nodeFields.value.splice(i, 1)
      }
    }
    if (inputItem && nodeType.value === 0) {
      const requiresElement = (inputItem.parameter || []).some((item) =>
        ['locating', 'actual'].includes(item.f)
      )
      const elementItemIndex = nodeFields.value.findIndex((item) => item.key === 'ele_name')
      if (!requiresElement && elementItemIndex >= 0) {
        nodeFields.value.splice(elementItemIndex, 1)
      } else if (requiresElement && elementItemIndex < 0) {
        const operationItemIndex = nodeFields.value.findIndex((item) => item.key === 'ope_key')
        const elementFormItem = createNodeFields().formItemsElementOpe.find((item) => item.key === 'ele_name')
        if (!elementFormItem) return
        elementFormItem.value = ''
        nodeFields.value.splice(Math.max(0, operationItemIndex + 1), 0, elementFormItem)
      }
    }
    const label = liveObject(useSelectValue.getTopLevelLabelByValue(method))
    if (String(value || '').startsWith('assert_excel_')) {
      loadUiTestFiles()
    }
    if (inputItem && inputItem.parameter) {
      inputItem.parameter.forEach((select) => {
        if (
          select.f === 'locating' &&
          nodeType.value === 0 &&
          nodeFields.value.some((item) => item.key === 'ele_name')
        ) {
          return
        }
        if (
          !['函数断言', '文件断言', 'sql断言'].includes(String(label.label)) &&
          (select.f === 'actual' || select.f === 'locating') &&
          !(select.f === 'locating' && nodeFields.value.some((item) => item.key === 'ele_name')) &&
          !nodeFields.value.some((item) => item.key === select.f)
        ) {
          nodeFields.value.push({
            label: '选择元素',
            key: select.f,
            value: ref(''),
            placeholder: '请选择一个元素',
            required: true,
            type: 'element-cascader',
            validator: function () {
              if (isEmptyStepField(this.value)) {
                Message.error(this.placeholder || '')
                return false
              }
              return true
            },
          })
        } else if (
          select.d === true && nodeType.value === 4
            ? ['函数断言', '文件断言', 'sql断言'].includes(String(label.label)) &&
              select.f !== 'expect' &&
              select.n !== '函数代码'
            : !nodeFields.value.some((item) => item.key === select.f)
        ) {
          const isFileParam = isUiUploadFileParam(method, select.f)
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
              if (isEmptyStepField(this.value)) {
                Message.error(this.placeholder || '')
                return false
              }
              // this.value = JSON.parse(this.value)
              return true
            },
          }
          nodeFields.value.push(d)
        }
      })
    }
    if (
      label?.label === 'sql断言' &&
      !nodeFields.value.some((item) => item.key === 'datasource_alias-ope_value')
    ) {
      nodeFields.value.push({
        label: '逻辑数据源',
        key: 'datasource_alias-ope_value',
        value: presetOpeValueValue(presetValues, 'datasource_alias', ''),
        type: 'datasource-select',
        required: true,
        placeholder: '请选择 MySQL、PostgreSQL 或 SQLite 逻辑数据源',
        validator: function () {
          if (isEmptyStepField(this.value)) {
            Message.error(this.placeholder || '请完整填写配置')
            return false
          }
          return true
        },
      })
    }
  }

  async function loadUiTestFiles() {
    const current = stepResources.capture()
    return stepResources.read('files', async () => {
      await projectInfo.projectProductName()
      if (!current()) throw Error('Expired file selection')
      const res = await getUserFile({
        page: 1,
        pageSize: 10000,
        type: 0,
      })
      return readStepFiles(buildUiUploadFileCascaderOptions(
        projectInfo.projectProduct,
        stepArray(stepResponse(res))
      ))
    }, values => { uiTestFileOptions.value = values })
  }

  const onRunCase = () => stepDebug.run()
  const onOpenStepBrowser = async () => {
    const current = stepResources.capture(), id = currentPageStepsId.value, environment = userStore.selected_environment
    if (!current() || browserOpening.value) return
    if (environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    if (currentPageStepsId.value === '') {
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
        page_step_id: id,
        test_env: environment,
      })
      stepResponse(res)
      if (current()) Message.success(res.msg || '已通知执行器打开目标页面')
    } catch { if (current()) actionError.value = '打开浏览器失败，请重试' } finally {
      browserOpening.value = false
    }
  }

  const onRunSelectedNode = () => {
    const id = uiCaseAssetId(nodeDraft.value.id ?? selectedNode.value?.config?.id)
    if (id === null || configEditing.value || !selectedNodeSupportsSingleStep.value) return Promise.resolve(false)
    return stepDebug.run(id)
  }
  function handleStepLiveReady() {
    Message.success('实时画面连接成功，可以点击调试')
  }

  async function handleStepWorkbenchElementSaved() {
    await getEleName()
  }

  function doRefreshSteps(pageStepsId: unknown) {
    const id = uiCaseAssetId(pageStepsId)
    if (id === null) return Promise.resolve(false)
    return stepResources.read('steps', () => getUiSteps({ id }), (res) => {
        const records = stepArray(stepResponse(res))
        const record = records.find(item => String(uiCaseAssetObject(item).id) === String(id))
        if (!record) throw Error('Missing page step')
        currentStepRecord.value = readStepRecord(record)
        flowData.value = normalizeStepFlowData(currentStepRecord.value.flow_data)
        markFlowSaved()
        syncSelectedResultData()
      })
  }

  async function openHealing() {
    const current = stepResources.capture()
    if (!current() || props.caseInputMode || canvasBusy.value || debugRunning.value || !checkNodeConfigSaved()) return
    if (await ensureFlowSavedForRun() && current()) healingPanelVisible.value = true
  }
  async function confirmPendingStepHealing() {
    const current = stepResources.capture(), id = currentPageStepsId.value, ids = [...pendingHealingRecordIds.value]
    if (!current() || healingReviewConfirming.value || props.caseInputMode || canvasBusy.value) return
    if (!ids.length) { Message.warning('待检查节点缺少修复记录，请进入修复记录查看详情'); return }
    healingReviewConfirming.value = true; actionError.value = ''
    try {
      for (const recordId of ids) {
        if (!current()) return
        stepResponse(await postUiPageStepHealApply(recordId))
        if (!current()) return
        flowData.value.nodes.forEach(node => { if (String(node.config?.ai_heal_record_id) === recordId && node.config) node.config.ai_review_status = 'confirmed' })
      }
      if (current()) { Message.success('AI 流程修复已确认'); await doRefreshSteps(id) }
    } catch { if (current()) actionError.value = '确认修复失败，已接受的记录不会重复提交，请重试剩余记录' }
    finally { healingReviewConfirming.value = false }
  }

  const loadLatestStepExecutionResult = stepDebug.latest
  const resumeActiveDebugTask = stepDebug.recover
  const stopDebugPolling = stepDebug.invalidate
  const handleStepResultMessage = stepDebug.message
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
    configEditing.value = uiCaseAssetId(node.config?.id) === null
    // 检查上一个节点是否为判断类型（type: 4）
    const previousNode = findPreviousNode(node.id)
    requiresBranchValue.value = false
    if (previousNode && previousNode.type === 4) {
      previousConditionId.value = previousNode.config?.id ?? null
      previousConditionNodeId.value = previousNode.id
      hasPreviousCondition.value = true
    } else {
      previousConditionId.value = null
      previousConditionNodeId.value = ''
      hasPreviousCondition.value = false
    }
    // 先清空表单项，重新构建基础表单
    changeStatus(node.type)

    const draft = nodeFormDrafts.get(node.id)
    const draftOpeKey = draft?.ope_key
    // 如果有选中的数据，需要处理回显和动态表单项
    if (Object.keys(nodeDraft.value).length > 0 || draftOpeKey) {
      // 先处理操作类型选择，触发动态表单生成
      const opeKeyItem = nodeFields.value.find((item) => item.key === 'ope_key')
      const opeKey = draftOpeKey || nodeDraft.value.ope_key
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

  function cloneDraftValue<T>(value: T): T { return cloneLosslessJson(value) }

  function captureSelectedNodeDraft() {
    const nodeId = selectedNode.value?.id
    if (!nodeId || configFormReadonly.value || (!nodeFields.value.length && nodeType.value !== 2)) return
    const draft = Object.fromEntries(
      nodeFields.value.map((item) => [item.key, cloneDraftValue(item.value)])
    )
    if (nodeType.value === 2) draft.__sql_execute = cloneDraftValue(sqlOperationRows.value)
    nodeFormDrafts.set(nodeId, draft)
  }

  function restoreNodeDraft(nodeId: string) {
    const draft = nodeFormDrafts.get(nodeId)
    if (!draft) return
    if (Object.prototype.hasOwnProperty.call(draft, '__sql_execute')) {
      sqlOperationRows.value = readStepDetail({ sql_execute: draft.__sql_execute || [] }).sql_execute
    }
    nodeFields.value.forEach((item) => {
      if (Object.prototype.hasOwnProperty.call(draft, item.key)) {
        item.value = cloneDraftValue(draft[item.key])
      }
    })
  }

  function changeStatus(event: number) {
    const { formItemsElementOpe, formItemsElementAss, formItemsElement4, formItemsElementKey, formItemsElementCondition, formItemsElementCode, formItemsForceWait } = createNodeFields()
    nodeType.value = event
    // 清空表单项，重新构建
    nodeFields.value = []
    if (hasPreviousCondition.value) {
      let placeholder: string | null = null
      const conditionDraft = nodeFormDrafts.get(previousConditionNodeId.value)
      const hasDraftMethod = Boolean(
        conditionDraft && Object.prototype.hasOwnProperty.call(conditionDraft, 'ope_key')
      )
      const savedCondition = nodeDetails.value.find((item) => item.id === previousConditionId.value)
      const conditionMethod = hasDraftMethod ? conditionDraft?.ope_key : savedCondition?.ope_key
      const byValue = useSelectValue.findItemByValue(String(conditionMethod ?? ''))
      const conditionParameters = byValue?.parameter || []
      conditionParameters.forEach((parameter) => {
        if (parameter.f === 'expect') {
          placeholder = parameter.p
          requiresBranchValue.value = true
        }
      })
      if (requiresBranchValue.value) {
        if (placeholder) {
          formItemsElementCondition[0].placeholder = placeholder
        }
        nodeFields.value.push(...formItemsElementCondition)
      }
    }
    if (event === 0) {
      nodeFields.value.push(...formItemsElementOpe)
      // 元素断言
    } else if (event === 1) {
      nodeFields.value.push(...formItemsElementAss)
      // sql操作
    } else if (event === 2) {
      sqlOperationRows.value = []
      // 自定义变量
    } else if (event === 3) {
      nodeFields.value.push(...formItemsElementKey)
      // 条件判断
    } else if (event === 4) {
      nodeFields.value.push(...formItemsElement4)
    } else if (event === 5) {
      nodeFields.value.push(...formItemsElementCode)
    } else if (event === 6) {
      nodeFields.value.push(...formItemsForceWait)
    }
  }

  function fillDefaultPythonCode() {
    if (nodeType.value !== 5) return
    const codeItem = nodeFields.value.find((item) => item.key === 'func')
    if (codeItem && !codeItem.value) {
      codeItem.value = PYTHON_CODE_TEMPLATE
    }
  }

  // 处理所有表单项的回显
  function formFeedback() {
    const detail = nodeDraft.value
    if (nodeType.value === 2) { sqlOperationRows.value = cloneDraftValue(detail.sql_execute); if (!sqlOperationRows.value.length && !configFormReadonly.value) addSqlOperation(); return }
    nodeFields.value.forEach(field => {
      let value: unknown
      if (field.key === 'ope_key') value = detail.ope_key
      else if (field.key === 'condition_value') value = typeof detail.condition_value === 'object' && detail.condition_value !== null ? detail.condition_value.expect ?? detail.condition_value.value : detail.condition_value
      else if (field.key === 'func') value = detail.func
      else if (field.key === 'key') value = detail.custom[0]?.key ?? ''
      else if (field.key === 'value') value = detail.custom[0]?.value ?? ''
      else if (field.key === 'sql') value = detail.sql_execute[0]?.sql ?? ''
      else if (field.key === 'key_list') value = detail.sql_execute[0]?.key_list ?? ''
      else value = detail.ope_value.find(item => item.f === field.key.replace('-ope_value', ''))?.v
      if ((field.key.includes('locating') || field.key === 'actual' || field.key === 'ele_name') && field.label !== '函数代码') value = getElementCascaderValue(detail.ele_name)
      if (isUiUploadFileParam(detail.ope_key, field.key.replace('-ope_value', ''))) { void loadUiTestFiles(); value = normalizeUiUploadFileValue(value, uiTestFileOptions.value) }
      field.value = cloneDraftValue(value)
    })
  }

  // 节点选中事件
  const onNodeSelect = (node: UINode | null) => {
    selectedNode.value = node
  }

  // 流程图数据变化事件
  const onFlowChange = (newFlowData: FlowData) => {
    flowData.value = normalizeStepFlowData(newFlowData)
    flowRevision.value += 1
    flowSaveStatus.value = 'dirty'
    scheduleFlowSave()
  }

  async function onNodeDuplicate(sourceNode: UINode) {
    const current = stepResources.capture(), pageStepId = currentPageStepsId.value
    const sourceDetailId = uiCaseAssetId(sourceNode.config?.id)
    if (!current() || canvasBusy.value || props.caseInputMode) return
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

    if (sourceNode.config?.id == null || sourceDraft) {
      if (sourceDraft) {
        nodeFormDrafts.set(nodeId, cloneDraftValue(sourceDraft))
      }
      flowData.value = duplicateFlow
      flowRevision.value += 1
      flowSaveStatus.value = 'dirty'
      scheduleFlowSave()
      await nextTick()
      if (current()) flowChartRef.value?.selectNode(nodeId)
      Message.success('节点已复制，请保存副本配置')
      return
    }

    nodeDuplicating.value = true
    clearFlowSaveTimer()
    Message.loading('正在复制节点')
    try {
      await flowSave.wait()
      if (!current()) return
      const res = await postUiPageStepNodeCopy({
        page_step_id: pageStepId,
        source_detail_id: sourceDetailId!,
        node_id: nodeId,
        flow_data: cloneDraftValue(duplicateFlow),
      })
      if (!current()) return
      stepResponse(res)
      flowData.value = normalizeStepFlowData(res.data.flow_data)
      flowRevision.value += 1
      markFlowSaved(flowRevision.value)
      await doRefresh()
      await nextTick()
      if (current()) flowChartRef.value?.selectNode(nodeId)
      if (current()) Message.success(res.msg)
    } catch {
      if (current()) actionError.value = '节点复制失败，请重试'
    } finally {
      nodeDuplicating.value = false
    }
  }

  const onStepControlChange = (value: UiStepControl) => {
    stepControl.value = { ...value }
  }

  function normalizeStepFlowData(value?: unknown): FlowData { return readStepFlow(value) }

  // 连接线删除事件
  const onEdgeDelete = (edge: UIEdge) => {
    Message.success('连接线已删除')
  }

  // 节点删除事件
  const onNodeDelete = async (node: UINode): Promise<boolean> => {
    const current = stepResources.capture(), id = uiCaseAssetId(node.config?.id), pageStepId = uiCaseAssetId(currentPageStepsId.value)
    if (!current() || canvasBusy.value || props.caseInputMode || pageStepId === null) return false
    nodeDeleting.value = true; actionError.value = ''; clearFlowSaveTimer()
    try {
      await flowSave.wait(); if (!current()) return false
      if (id !== null) stepResponse(await deleteUiPageStepsDetailed(id, pageStepId))
      if (!current()) return false
      nodeFormDrafts.delete(node.id); nodeDetails.value = nodeDetails.value.filter(item => String(item.id) !== String(id))
      if (selectedNode.value?.id === node.id) { selectedNode.value = null; nodeDraft.value = createNodeDraft(); nodeFields.value = [] }
      Message.success('节点已删除'); return true
    } catch { if (current()) actionError.value = '节点删除失败，请重试'; return false }
    finally { nodeDeleting.value = false }
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
    const invalidNodes = flowData.value.nodes.filter((node) => node.config?.id == null)
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
    const detail = nodeDetails.value.find((item) => String(item.id) === String(node.config?.id))
    return (
      detail?.ele_name?.name ||
      useSelectValue.getSelectLabel(detail?.ope_key || '') ||
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
    if (!stepResources.capture()() || !selectedNode.value || methodsLoading.value || methodsError.value || nodeDuplicating.value || nodeDeleting.value) return
    if (formSaving.value || caseNodeInputs.saving.value) return
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
      !nodeFields.value.every((it) =>
        isCaseInheritedConfigItem(it) ? true : it.validator ? it.validator() : true
      )
    ) {
      return
    }

    if (nodeType.value === 2 && !dataSourceOperationListRef.value?.validate()) {
      Message.warning('请完整填写逻辑数据源和执行内容')
      return
    }

    if (props.caseInputMode) {
      const value = nodeType.value === 2
        ? { sql_execute: cloneDraftValue(sqlOperationRows.value) }
        : getFormItems(nodeFields.value)
      await caseNodeInputs.save(value)
      return
    }
    formSaving.value = true
    const current = stepResources.capture(), selectionCurrent = captureElementContext(), pageStepId = currentPageStepsId.value
    const inputSnapshot = cloneDraftValue(nodeType.value === 2 ? { sql_execute: sqlOperationRows.value } : getFormItems(nodeFields.value))
    const detailSnapshot = cloneDraftValue(nodeDraft.value), typeSnapshot = nodeType.value, flowSnapshot = cloneDraftValue(flowData.value)
    clearFlowSaveTimer()
    try {
      const value: UiPageStepsDetailPayload = { ...inputSnapshot, page_step: pageStepId }
      value['page_step'] = pageStepId
      value['type'] = typeSnapshot
      if (detailSnapshot.id !== null) {
        value['id'] = detailSnapshot.id
      }
      value['flow_data'] = flowSnapshot
      value['node_id'] = savingNodeId
      value['step_sort'] = 0
      value['precondition'] = detailSnapshot.precondition || { operator: 'all', conditions: [] }
      value['postcondition'] = detailSnapshot.postcondition || { operator: 'all', conditions: [] }
      value['page_type'] = Number(currentPageType.value)
      if (value.condition_value !== undefined && value.condition_value !== null && value.condition_value !== '') {
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
      if (typeSnapshot === 6) {
        value['ope_key'] = null
        value['ope_value'] = [
          { f: 'seconds', v: Number(value['seconds-ope_value']) },
        ]
        delete value['seconds-ope_value']
      }

      Object.assign(value, processOptionData(value))
      const fields = ['id', 'type', 'flow_data', 'node_id', 'step_sort', 'precondition', 'postcondition', 'page_type', 'condition_value', 'custom', 'sql_execute', 'func', 'ope_key', 'ope_value', 'ele_name'] as const
      const payload: UiPageStepsDetailPayload = { page_step: pageStepId, ...Object.fromEntries(fields.filter(key => value[key] !== undefined).map(key => [key, value[key]])) }
      await flowSave.wait()
      if (!current()) return
      const res = await postUiPageStepsDetailed(payload, pageStepId)
      if (!current()) return
      stepResponse(res)
      Message.success(res.msg)
      nodeFormDrafts.delete(savingNodeId)
      flowData.value = normalizeStepFlowData(res.data.flow_data)
      flowRevision.value += 1
      markFlowSaved(flowRevision.value)
      const updatedNode = flowData.value.nodes.find((node) => node.id === savingNodeId)
      if (selectionCurrent() && selectedNode.value?.id === savingNodeId && updatedNode) {
        selectedNode.value = updatedNode
        nodeDraft.value = readStepDetail({ ...detailSnapshot, ...res.data })
        configEditing.value = false
      }
      await doRefresh()
    } catch (error) {
      if (current()) actionError.value = '节点保存失败，草稿已保留，请重试'
    } finally {
      formSaving.value = false
      if (current() && flowRevision.value !== savedFlowRevision.value) scheduleFlowSave()
    }
  }

  function processOptionData(value: UiPageStepsDetailPayload) {
    const extractedValues: Array<{ f: string; n: string; p: string; d: boolean; v: unknown; value_type?: string; input_type?: string }> = []
    if (!value.ope_key) {
      return {}
    }
    const method = typeof value.ope_key === 'string' ? value.ope_key : ''
    const parameter = cloneDraftValue(useSelectValue.findItemByValue(method)?.parameter)
    if (!parameter) {
      return {}
    }
    const datasourceAlias = value['datasource_alias-ope_value']
    delete value['datasource_alias-ope_value']
    const requiresElement = parameter.some((item) => ['locating', 'actual'].includes(item.f))
    for (const key in value) {
      const newKey = key.replace('-ope_value', '')
      parameter.forEach((item) => {
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
          item['v'] = isUiUploadFileParam(method, newKey)
            ? getUiUploadFileValueFromCascader(value[key], uiTestFileOptions.value)
            : value[key]
          if (!isDuplicate) {
            extractedValues.push(item)
          }
          delete value[key]
        }
      })
    }
    if (uiCaseAssetId(value['ele_name']) !== null) {
      const locatingItem = parameter.find((item) => item.f === 'locating')
      const hasLocating = extractedValues.some((item) => item.f === 'locating')
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

  function getNodeTypeLabel(type: unknown) {
    const enumLabel = enumStore.element_ope?.find(item => String(item.key) === String(type))?.title
    return enumLabel || nodeTypes.find((item) => item.type === Number(type))?.label || '未知类型'
  }

  function getMethodLabel(value: unknown): string {
    if (value == null || value === '') return '-'
    return useSelectValue.findItemByValue(String(value))?.label || String(value)
  }
  function getElementName(value: unknown): string {
    if (value == null || value === '') return '-'
    if (typeof value === 'object') { const row = liveObject(value); return String(row.name || row.label || row.id || '-') }
    return elementOptions.value.find(item => String(item.id) === String(value))?.name || String(value)
  }

  function getSelectedNodeTitle() {
    const elementName = getElementName(nodeDraft.value?.ele_name)
    const methodLabel = getMethodLabel(nodeDraft.value?.ope_key)
    return (
      (elementName !== '-' ? elementName : '') ||
      nodeDraft.value?.name ||
      (methodLabel !== '-' ? methodLabel : '') ||
      selectedNode.value?.label ||
      '未命名节点'
    )
  }

  function getConfigParams(item) {
    if (Array.isArray(item?.ope_value)) return item.ope_value
    if (Array.isArray(item?.custom)) return item.custom
    if (Array.isArray(item?.sql_execute)) return item.sql_execute
    if (item?.condition_value) return [item.condition_value]
    return []
  }

  function getVisibleConfigParams(item) {
    const params = getConfigParams(item).map(liveObject)
    if (item?.type === 0) {
      return params.filter((param) => param?.d)
    }
    if (item?.type === 1) {
      return params.filter((param) => param?.f !== 'actual')
    }
    return params
  }

  function getConfigParamCount(item) {
    return getVisibleConfigParams(item).length
  }

  function stringifyValue(value: unknown) {
    if (value === undefined || value === null || value === '') return '-'
    if (Array.isArray(value)) return value.join(', ')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  function getConfigParamLabel(param, index) {
    return param?.n || param?.key || param?.f || param?.name || `参数${index + 1}`
  }

  function getConfigParamValue(param) {
    return stringifyValue(
      param?.v ?? param?.value ?? param?.sql ?? param?.key_list ?? param?.func ?? param?.expect
    )
  }

  function getConfigParamSummary(item) {
    return getVisibleConfigParams(item)
      .map((param, index) => ({
        key: `${item?.id || 'node'}-${index}`,
        label: getConfigParamLabel(param, index),
        value: getConfigParamValue(param),
      }))
      .filter((param) => param.value !== '-')
      .slice(0, 6)
  }

  function getConditionSummary(value: unknown) {
    if (value == null || value === '') return '-'
    if (typeof value === 'string') return value
    return stringifyValue(liveObject(value).expect ?? liveObject(value).value ?? value)
  }

  async function loadSelectedNodeElement() {
    const id = uiCaseAssetId(nodeDraft.value?.id), current = captureElementContext()
    if (id === null) {
      Message.error('未找到页面步骤明细ID')
      return null
    }
    const res = await getUiPageStepsDetailedById(id)
    if (!current()) return null
    const rows = stepArray(stepResponse(res)).map(readStepDetail)
    const element = rows.find(row => String(row.id) === String(id))?.ele_name
    if (uiCaseAssetId(element?.id) === null) {
      Message.error('当前节点没有绑定页面元素')
      return null
    }
    return element
  }

  async function openSelectedElementEditPanel() {
    if (elementEditLoading.value) return
    const current = captureElementContext()
    elementEditLoading.value = true
    try {
      const element = await loadSelectedNodeElement()
      if (!element || !current()) return
      elementEditPanelRef.value?.openEdit(element)
    } catch (error) {
      console.log(error)
      if (current()) Message.error('元素信息获取失败')
    } finally {
      elementEditLoading.value = false
    }
  }

  async function runSelectedElementDeepCheck() {
    const current = captureElementContext()
    if (elementDeepCheckLoading.value) return
    elementPreparing.value = true
    try { const element = await loadSelectedNodeElement(); if (element && current()) await elementChecks.start(element, 'deep') }
    catch { if (current()) actionError.value = '元素深度检测准备失败，请重试' }
    finally { elementPreparing.value = false }
  }
  const handleStepElementCheckResult = elementChecks.workbenchResult
  const handleStepElementCheckStarted = elementChecks.workbenchStarted
  const applyStepElementDeepCheckUpdates = elementChecks.apply
  async function openSelectedElementAiHeal() {
    const environment = userStore.selected_environment
    if (elementAiHealLoading.value) return
    if (environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    elementAiHealLoading.value = true
    const current = captureElementContext()
    try {
      const element = await loadSelectedNodeElement()
      if (!element || !current()) return
      await elementAiHealPanelRef.value?.open(element)
    } catch (error) {
      console.log(error)
      if (current()) Message.error('AI自愈信息获取失败')
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

  async function initializeStep() {
    const current = stepResources.capture()
    const methods = loadMethods()
    const loaded = await doRefreshSteps(currentPageStepsId.value)
    if (!current() || !loaded) return
    await Promise.all([loadDatasourceAliases(), doRefresh(), getEleName(), props.caseInputMode ? Promise.resolve() : loadLatestStepExecutionResult(true)])
    if (!current()) return
    if (!props.caseInputMode) await resumeActiveDebugTask()
    await methods
  }
  onMounted(() => {
    window.addEventListener('mango:websocket-message', handleStepResultMessage)
    void initializeStep()
  })

  watch(
    () => [props.caseData, props.caseResult],
    () => {
      if (props.caseInputMode) void doRefresh()
    },
    { deep: true }
  )

  onBeforeUnmount(() => {
    window.removeEventListener('mango:websocket-message', handleStepResultMessage)
    stopDebugPolling()

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
    min-width: var(--mango-workbench-min-width);
    height: 100%;
    overflow: hidden;
  }

  .mango-ui-step-layout {
    --mango-workbench-min-width: calc(var(--steps-left-panel-width) + var(--steps-canvas-min-width) + var(--steps-right-panel-width) + var(--steps-panel-gap) * 2);
    flex: 1 1 auto;
  }

  .page-steps-workbench-page--compact .mango-ui-step-layout {
    --mango-workbench-min-width: calc(var(--steps-canvas-min-width) + var(--steps-right-panel-width) + var(--steps-panel-gap));
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
