<template>
  <TableBody
    ref="tableBody"
    plain
    class="mango-api-case-page mango-detail-workbench-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header>
      <TableHeader title="测试用例"> </TableHeader>
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        show-modules
        :model-value="getConditionValue('project_product')"
        :module-value="getConditionValue('module')"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <ApiCaseSearchFilters
            :items="headerConditionItems"
            :user-list="userOptions"
            :users-loading="userOptionsLoading"
            :enum-store="enumStore"
            :field-names="fieldNames"
            @search="onSearchRefresh"
          />
        </template>
        <template #tabs>
          <TableTabs :active-key="activePublicationStatus" @tab-click="switchPublicationTab">
            <a-tab-pane v-for="tab in publicationTabs" :key="tab.key" :title="tab.title" />
            <template #extra>
              <a-space wrap>
                <div>
                  <a-button
                    size="small"
                    type="primary"
                    @click="onAdd"
                    data-testid="qa-views-apitest-case-button-新增"
                    >新增</a-button
                  >
                </div>
                <div>
                  <a-button
                    size="small"
                    status="success"
                    :loading="caseRunning"
                    :disabled="batchPublicationAction !== null"
                    @click="onCaseBatchRun"
                    data-testid="qa-views-apitest-case-button-批量执行"
                    >批量执行
                  </a-button>
                </div>
                <div>
                  <a-button
                    size="small"
                    status="warning"
                    :disabled="batchPublicationAction !== null"
                    @click="handleClick"
                    data-testid="qa-views-apitest-case-button-绑定到手动指定任务"
                    >绑定到手动定时任务</a-button
                  >
                </div>
                <div>
                  <a-button
                    size="small"
                    :loading="batchPublicationAction === 'submit'"
                    :disabled="publicationActionCaseId !== null || batchPublicationAction !== null"
                    @click="batchSubmitPrepublication"
                    data-testid="qa-views-apitest-case-button-批量提交预发布"
                    >批量预发布</a-button
                  >
                </div>
                <div>
                  <a-button
                    size="small"
                    :loading="batchPublicationAction === 'publish'"
                    :disabled="publicationActionCaseId !== null || batchPublicationAction !== null"
                    @click="batchUpdatePrepublication('publish')"
                    data-testid="qa-views-apitest-case-button-批量发布"
                    >批量发布</a-button
                  >
                </div>
                <div>
                  <a-button
                    size="small"
                    :loading="batchPublicationAction === 'revert'"
                    :disabled="publicationActionCaseId !== null || batchPublicationAction !== null"
                    @click="batchUpdatePrepublication('revert')"
                    data-testid="qa-views-apitest-case-button-批量未发布"
                    >批量未发布</a-button
                  >
                </div>
                <div>
                  <a-button
                    size="small"
                    status="danger"
                    :disabled="batchPublicationAction !== null"
                    @click="onDelete(null)"
                    data-testid="qa-views-apitest-case-button-批量删除"
                    >批量删除</a-button
                  >
                </div>
              </a-space>
            </template>
          </TableTabs>
        </template>
        <StickyHorizontalTable :scroll-x="2520">
          <a-table
            :bordered="false"
            :columns="tableColumns"
            :data="batchSelectableDataList"
            :loading="table.tableLoading.value"
            :pagination="false"
            :row-selection="{ selectedRowKeys, showCheckedAll }"
            :rowKey="rowKey"
            :scroll="{ x: 2520, y: '100%' }"
            @selection-change="onApiCaseSelectionChange"
          >
            <template #columns>
              <a-table-column
                v-for="item of tableColumns"
                :key="item.key"
                :align="item.align"
                :data-index="item.key"
                :ellipsis="item.ellipsis"
                :fixed="item.fixed"
                :title="item.title"
                :tooltip="item.tooltip"
                :width="item.width"
              >
                <template v-if="item.key === 'execution_configuration'" #title>
                  <CaseExecutionConfigurationTitle />
                </template>
                <template v-else-if="item.key === 'status'" #title>
                  <CaseResultTitle />
                </template>
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.scenario_type]" size="small">
                    {{ getEnumTitle(enumStore.api_case_scenario_type, record.scenario_type) }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.scenario_layer]" size="small">
                    {{ getEnumTitle(enumStore.api_case_scenario_layer, record.scenario_layer) }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
                  <ExecutionSceneTagGrid
                    :values="record.scenario_tags"
                    :options="enumStore.api_case_scenario_tag"
                    :colors="enumStore.colors"
                  />
                </template>
                <template v-else-if="item.key === 'scenario_description'" #cell="{ record }">
                  {{ record.scenario_description || '-' }}
                </template>
                <template v-else-if="item.key === 'case_flow'" #cell="{ record }">
                  {{ record.case_flow || '-' }}
                </template>
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ formatProjectProductPath(record.project_product) }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ formatModulePath(record.module) }}
                </template>
                <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                  {{ record.case_people?.name }}
                </template>
                <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                  {{ record.update_user?.name || '-' }}
                </template>
                <template v-else-if="item.key === 'level'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.level]" size="small">
                    {{
                      record.level !== null ? enumStore.case_level[record.level]?.title || '-' : '-'
                    }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <CaseVersionResultPopover :case-id="record.id"
                    :version-token="record.list_result?.version_token">
                    <a-button v-if="record.list_result?.trace_id" type="text" size="mini"
                      :aria-label="listResultHint(record)"
                      @click="showExecutionTrace({ trace_id: record.list_result.trace_id })">
                      <a-tag :color="enumStore.status_colors[record.list_result.status ?? 2]" size="small">
                        {{ record.list_result.status === 3 && record.list_result.phase === 'automatic_recovery'
                          ? enumStore.report_execution_phase[record.list_result.phase]?.title || '自动恢复中'
                          : record.list_result.status === 2 ? '待测试'
                          : enumStore.task_status[record.list_result.status ?? 2]?.title || '-' }}
                      </a-tag>
                    </a-button>
                    <a-tag v-else-if="record.list_result?.status != null"
                      :color="enumStore.status_colors[record.list_result.status]" size="small">
                      {{ record.list_result.status === 2 ? '待测试' : enumStore.task_status[record.list_result.status]?.title || '-' }}
                    </a-tag>
                    <a-tag v-else :color="enumStore.status_colors[2]" size="small">待测试</a-tag>
                  </CaseVersionResultPopover>
                </template>
                <template v-else-if="item.key === 'execution_configuration'" #cell="{ record }">
                  <a-spin v-if="configurationLoading && !configurationSummaries[record.id]" />
                  <a-button
                    v-else-if="!configurationSummaries[record.id]"
                    type="text"
                    size="mini"
                    @click="reloadConfigurationSummaries"
                    >重试</a-button
                  >
                  <a-button
                    v-else-if="
                      configurationSummaries[record.id].has_sql ||
                      configurationSummaries[record.id].has_data_factory
                    "
                    type="text"
                    size="mini"
                    :disabled="false"
                    @click="configurationDrawerRef?.open(Number(record.id), record.name)"
                  >
                    <CaseExecutionConfigurationTags
                      :sql-count="configurationSummaries[record.id].sql_count"
                      :factory-count="configurationSummaries[record.id].data_factory_count"
                    />
                  </a-button>
                  <CaseExecutionConfigurationTags
                    v-else
                    :sql-count="configurationSummaries[record.id].sql_count"
                    :factory-count="configurationSummaries[record.id].data_factory_count"
                  />
                </template>
                <template v-else-if="item.key === 'publication_status'" #cell="{ record }">
                  <a-tag
                    :color="
                      getApiCasePublicationMeta(
                        record.publication_status,
                        record.published_version_label,
                        record.has_unpublished_changes,
                        record.prepublished_revision_no
                      ).color
                    "
                    size="small"
                  >
                    {{
                      getApiCasePublicationMeta(
                        record.publication_status,
                        record.published_version_label,
                        record.has_unpublished_changes,
                        record.prepublished_revision_no
                      ).label
                    }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      {
                        label: '执行',
                        tooltip: listExecutionLabel(record),
                        loading: caseRunning,
                        disabled: batchPublicationAction !== null || caseRunning,
                        onClick: () => caseRun(record),
                      },
                      { label: '步骤', onClick: () => onStep(record) },
                      { label: '套件', onClick: () => clickSuite(record) },
                      { label: '历史结果', onClick: () => openResultHistory(record) },
                      { label: '关联任务', onClick: () => onBoundTasks(record) },
                      {
                        label: '提交预发布',
                        hidden: !canSubmitCasePrepublication(record),
                        loading: publicationActionCaseId === record.id,
                        onClick: () => submitCasePrepublication(record),
                      },
                      {
                        label: '通过发布',
                        hidden: !canApproveCasePrepublication(record),
                        loading: publicationActionCaseId === record.id,
                        onClick: () => approveCasePrepublication(record),
                      },
                      {
                        label: '退回未发布',
                        hidden: !canApproveCasePrepublication(record),
                        loading: publicationActionCaseId === record.id,
                        onClick: () => revertCasePrepublication(record),
                      },
                      {
                        label: '取消发布',
                        hidden: !hasPublishedCaseVersion(record) || !record.is_product_owner,
                        danger: true,
                        loading: publicationActionCaseId === record.id,
                        onClick: () => unpublishCaseVersion(record),
                      },
                      { label: '编辑', disabled: batchPublicationAction !== null, onClick: () => onUpdate(record) },
                      {
                        label: '复制',
                        loading: copyingIds.has(record.id),
                        disabled: copyingIds.has(record.id),
                        onClick: () => pageStepsCody(record),
                      },
                      { label: '删除', danger: true, disabled: batchPublicationAction !== null, onClick: () => onDelete(record) },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </StickyHorizontalTable>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <CasePublicationReviewModal
    v-if="pageActive"
    :key="panelSession"
    ref="publicationReviewRef"
    @published="onReviewPublished"
  />
  <ApiCaseConfigurationDrawer ref="configurationDrawerRef" />
  <TestExecutionModal
    ref="batchRunModalRef"
    title="批量执行 API 用例"
    name-editable
    version-selectable
    :platform-limit="apiPlatformLimit"
    @confirm="onConfirmCaseBatchRun"
    @cancel="onCancelBatchRun"
  />
  <ExecutionResultHistoryDrawer
    :key="`${panelSession}-${historySession}`"
    v-model:visible="resultHistory.visible"
    :title="resultHistory.title"
    :case-id="resultHistory.caseId"
    @show-trace="showExecutionTrace"
  />
  <ApiCaseExecutionTraceDrawer ref="traceDrawerRef" />
  <ApiCaseMetadataEditor
    ref="metadataEditorRef"
    :user-options="userOptions"
    :users-loading="userOptionsLoading"
    @saved="onAssetsChanged"
  />
  <ApiCaseTaskBindingModal ref="taskBindingRef" @saved="onAssetsChanged" />
  <ApiCaseRelatedTasksDrawer ref="relatedTasksRef" />
  <ApiCaseParametrizePanel ref="parametrizeRef" @saved="onAssetsChanged" />
</template>

<script lang="ts" setup>
  import { usePagePolling } from '@/hooks/use-page-polling'
  import CasePublicationReviewModal from '@/components/business/CasePublicationReviewModal.vue'
  import ApiCaseConfigurationDrawer from './components/ApiCaseConfigurationDrawer.vue'
  import CaseExecutionConfigurationTags from '@/components/display/CaseExecutionConfigurationTags.vue'
  import CaseExecutionConfigurationTitle from '@/components/display/CaseExecutionConfigurationTitle.vue'
  import CaseResultTitle from './components/CaseResultTitle.vue'
  import CaseVersionResultPopover from './components/CaseVersionResultPopover.vue'
  import { formatCaseResultTime } from './result-presentation'
  import { useCaseConfigurationSummary } from './composables/useCaseConfigurationSummary'

  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { useProjectLockedRowSelection } from '@/hooks/use-project-locked-row-selection'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    computed,
    onMounted,
    ref,
    reactive,
    onUnmounted,
    onActivated,
    onDeactivated,
    watch,
  } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useRoute, useRouter } from 'vue-router'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import { formatProjectProductPath, formatModulePath, getOptionId } from '@/utils/business-format'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import ApiCaseSearchFilters from './components/ApiCaseSearchFilters.vue'
  import TestExecutionModal from '@/components/overlays/TestExecutionModal.vue'
  import ApiCaseExecutionTraceDrawer from './details/components/ApiCaseExecutionTraceDrawer.vue'
  import type { ApiCaseExecutionTraceQuery } from './details/types'
  import { tableColumns, createConditionItems, publicationTabs } from './config'
  import type { CaseListRow, UserOption } from './types'
  import ApiCaseMetadataEditor from './components/ApiCaseMetadataEditor.vue'
  import ApiCaseTaskBindingModal from './components/ApiCaseTaskBindingModal.vue'
  import ApiCaseRelatedTasksDrawer from './components/ApiCaseRelatedTasksDrawer.vue'
  import ApiCaseParametrizePanel from './components/ApiCaseParametrizePanel.vue'

  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import {
    getApiCase,
    deleteApiCase,
    postApiCaseCody,
    getApiCaseRun,
    getApiCaseExecutionOptions,
    postApiCaseBatchRun,
  } from '@/api/apitest/case'
  import type { ApiCaseVersionListRow } from '@/types/api-test/case-version'
  import {
    buildPublishedBatchItems,
    getApiCasePublicationMeta,
    toApiCaseBatchRunItems,
  } from '@/utils/api-case-version'
  import {
    createApiCaseRevision,
    revertApiCasePrepublication,
    submitApiCasePrepublication,
    unpublishApiCaseRelease,
  } from '@/api/apitest/case-version'
  import { NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const router = useRouter()

  const configurationDrawerRef = ref<InstanceType<typeof ApiCaseConfigurationDrawer> | null>(null)
  const {
    summaries: configurationSummaries,
    loading: configurationLoading,
    load: loadConfigurationSummaries,
    reset: resetConfigurationSummaries,
  } = useCaseConfigurationSummary()
  function reloadConfigurationSummaries() {
    void loadConfigurationSummaries(table.dataList.map((row) => Number(row.id)))
  }
  const publicationReviewRef = ref<InstanceType<typeof CasePublicationReviewModal> | null>(null)
  function onReviewPublished(ids: number[]) {
    const published = new Set(ids.map(String))
    selectedRowKeys.value = selectedRowKeys.value.filter((id) => !published.has(String(id)))
    doRefresh(null, false, true)
  }
  const route = useRoute()
  const conditionItems = createConditionItems()
  const metadataEditorRef = ref<InstanceType<typeof ApiCaseMetadataEditor> | null>(null)
  const taskBindingRef = ref<InstanceType<typeof ApiCaseTaskBindingModal> | null>(null)
  const relatedTasksRef = ref<InstanceType<typeof ApiCaseRelatedTasksDrawer> | null>(null)
  const parametrizeRef = ref<InstanceType<typeof ApiCaseParametrizePanel> | null>(null)
  const userOptions = ref<UserOption[]>([])
  const userOptionsLoading = ref(false)
  const pageActive = ref(true),
    panelSession = ref(0),
    historySession = ref(0)
  let pageVersion = 0
  const copyingIds = reactive(new Set<number>())
  const batchRunModalRef = ref<InstanceType<typeof TestExecutionModal> | null>(null)
  const table = useTable()
  const pagination = usePagination(
    () => doRefresh(null, false, true),
    () => table.tableLoading
  )
  const {
    selectedRowKeys,
    showCheckedAll,
    selectableDataList: batchSelectableDataList,
    onSelectionChange: onApiCaseSelectionChange,
    validateSingleProject,
  } = useProjectLockedRowSelection<ApiCaseVersionListRow>(
    () => table.dataList as ApiCaseVersionListRow[],
    (row) => row?.project_product?.project
  )
  const { beginRequest, isLatestRequest, invalidateRequests } = useLatestRequest()
  const rowKey = useRowKey('id')
  const enumStore = useEnum()
  const activePublicationStatus = ref('all')

  function switchPublicationTab(key: string | number) {
    activePublicationStatus.value = String(key)
    pagination.page = 1
    selectedRowKeys.value = []
    doRefresh(null, false, true)
  }
  const userStore = useUserStore()
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product' && item.key !== 'module')
  )

  const caseRunning = ref(false)
  const publicationActionCaseId = ref<number | null>(null)
  const batchPublicationAction = ref<'submit' | 'publish' | 'revert' | null>(null)
  const sidebarModuleIds = ref<Array<string | number>>([])
  const sidebarResetKey = ref(0)
  const apiPlatformLimit = ref(1)
  const pendingBatchRunCaseIds = ref<number[]>([])
  const pendingBatchRows = ref<CaseListRow[]>([])
  let runNoticeTimer: ReturnType<typeof setTimeout> | null = null
  const pagePolling = usePagePolling(
    () => doRefresh(null, false, false),
    () => {
      if (table.tableLoading.value) pagePolling.start()
      beginRequest()
      table.tableLoading.value = false
    }
  )
  const traceDrawerRef = ref<InstanceType<typeof ApiCaseExecutionTraceDrawer> | null>(null)
  const resultHistory = reactive({
    visible: false,
    caseId: '' as number | string,
    title: '用例执行历史',
  })
  function clearPollingTimer() {
    pagePolling.stop()
  }

  function getItemValue(items: import('@/types/components').FormItem[], key: string) {
    return items.find((item) => item.key === key)?.value ?? ''
  }

  function setItemValue(
    items: import('@/types/components').FormItem[],
    key: string,
    value: unknown
  ) {
    const item = items.find((option) => option.key === key)
    if (item) {
      item.value = value
    }
  }

  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }

  function onSidebarFilterChange(filter: {
    projectProduct: string | number | null
    module: string | number | null
    moduleIds?: Array<string | number>
  }) {
    setItemValue(conditionItems, 'project_product', filter.projectProduct)
    setItemValue(conditionItems, 'module', filter.module)
    sidebarModuleIds.value = filter.moduleIds || []
    selectedRowKeys.value = []
    pagination.page = 1
    doRefresh(null, false, true)
  }

  function onSearchRefresh() {
    pagination.page = 1
    selectedRowKeys.value = []
    doRefresh(null, false, true)
  }

  function doRefresh(
    projectProductId: string | number | null = null,
    bool_ = false,
    showLoading = false
  ) {
    if (!pageActive.value) return Promise.resolve()
    if (showLoading) resetConfigurationSummaries(true)
    const requestId = beginRequest()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    for (const key of Object.keys(value))
      if (
        value[key] === null ||
        value[key] === undefined ||
        value[key] === '' ||
        (Array.isArray(value[key]) && !value[key].length)
      )
        delete value[key]
    if (value.project_product != null) value.project_product = getOptionId(value.project_product)
    if (value.module != null) value.module = getOptionId(value.module)
    if (activePublicationStatus.value !== 'all') {
      value.publication_status = activePublicationStatus.value
    }
    if (sidebarModuleIds.value.length) value['module__in'] = sidebarModuleIds.value.join(',')
    if (Array.isArray(value.scenario_tags) && !value.scenario_tags.length) {
      delete value.scenario_tags
    }
    value['page'] = pagination.page
    value.result_scope = 'displayed_version'
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    return getApiCase(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        if (showLoading || !pagePolling.isRunning())
          void loadConfigurationSummaries((res.data || []).map((row: any) => Number(row.id)))
        pagination.setTotalSize(res.totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((row: CaseListRow) =>
            row.list_result?.is_active === true)

        if (hasRunningItem) pagePolling.start()
        else pagePolling.stop()
      })
      .catch(() => {
        if (isLatestRequest(requestId) && !pagePolling.isRunning()) resetConfigurationSummaries()
      })
      .finally(() => {
        if (isLatestRequest(requestId)) {
          table.tableLoading.value = false
        }
      })
  }

  function onResetSearch() {
    pagination.page = 1
    selectedRowKeys.value = []
    sidebarModuleIds.value = []
    sidebarResetKey.value += 1
    conditionItems.forEach((it) => {
      if (it.key === 'project_product' || it.key === 'module') {
        it.value = null
      } else if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    doRefresh(null, false, true)
  }

  function getEnumTitle(options: any[] | null, value: any) {
    return options?.find((item: any) => Number(item.key) === Number(value))?.title || '-'
  }

  function onAssetsChanged() {
    selectedRowKeys.value = []
    void doRefresh(null, false, true)
  }
  function onAdd() {
    const defaults = navigationCreateRef.value?.getCreateDefaults()
    metadataEditorRef.value?.open(undefined, {
      projectProduct: defaults?.projectProduct,
      module: defaults?.module,
    })
  }
  function onUpdate(record: CaseListRow) {
    metadataEditorRef.value?.open(record)
  }
  function clickSuite(record: CaseListRow) {
    parametrizeRef.value?.open(record)
  }
  function onBoundTasks(record: CaseListRow) {
    void relatedTasksRef.value?.open(record)
  }
  function handleClick() {
    const selectedIds = new Set(selectedRowKeys.value.map(String))
    if (!selectedIds.size) {
      Message.error('请选择要添加定时任务的用例')
      return
    }
    const rows = (table.dataList as CaseListRow[]).filter((row) => selectedIds.has(String(row.id)))
    const plan = buildPublishedBatchItems(rows)
    if (rows.length !== selectedIds.size || plan.blocked.length) {
      Message.warning('所选用例必须全部存在可执行的已发布版本')
      return
    }
    taskBindingRef.value?.open(toApiCaseBatchRunItems(plan.executable))
  }
  function onDelete(record: CaseListRow | null) {
    const batch = record === null
    const ids = record?.id ?? [...selectedRowKeys.value],
      version = pageVersion
    if (batch) {
      if (selectedRowKeys.value.length === 0) {
        Message.error('请选择要删除的数据')
        return
      }
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此用例？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        if (version !== pageVersion || !pageActive.value) return false
        return deleteApiCase(ids)
          .then((res) => {
            if (version === pageVersion && pageActive.value) Message.success(res.msg)
          })
          .then(() => {
            if (version === pageVersion) onAssetsChanged()
            return true
          })
          .catch(() => false)
      },
    })
  }

  async function getNickName() {
    const version = pageVersion
    userOptionsLoading.value = true
    try {
      const response = await getUserName()
      if (version === pageVersion && pageActive.value) userOptions.value = response.data || []
    } catch {
      /* 公共请求层反馈错误，重新进入页面时重试。 */
    } finally {
      if (version === pageVersion) userOptionsLoading.value = false
    }
  }

  const caseRun = async (param: CaseListRow) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true

    const version = pageVersion
    runNoticeTimer = setTimeout(() => {
      if (version !== pageVersion || !pageActive.value || document.visibilityState === 'hidden')
        return
      Message.info('测试用例异步执行中，请稍后刷新页面查看该用例的测试结果~')
      if (version === pageVersion && pageActive.value) void doRefresh()
    }, 30000)

    try {
      const token = param.list_result?.version_token
      if (!token) {
        Message.info('请刷新列表后执行')
        return
      }
      const res = await getApiCaseRun(param.id, userStore.selected_environment, null, undefined, undefined, token)
      if (runNoticeTimer !== null) {
        clearTimeout(runNoticeTimer)
        runNoticeTimer = null
      }
      if (version !== pageVersion || !pageActive.value) return
      Message.success(res.msg)
      doRefresh()
      caseRunning.value = false
    } catch (e) {
      if (runNoticeTimer !== null) {
        clearTimeout(runNoticeTimer)
        runNoticeTimer = null
      }
      caseRunning.value = false
    } finally {
      if (runNoticeTimer !== null) {
        clearTimeout(runNoticeTimer)
        runNoticeTimer = null
      }
      caseRunning.value = false
    }
  }

  function listExecutionLabel(record: CaseListRow) {
    if (record.publication_status === 'published') return `执行已发布 ${record.published_version_label || ''}`
    if (record.publication_status === 'prepublished') return `执行预发布 r${record.prepublished_revision_no}`
    return '执行当前编辑态'
  }

  function listResultHint(record: CaseListRow) {
    const result = record.list_result
    if (!result) return '悬停查看各版本最近一次执行结果'
    const version = listExecutionLabel(record).replace(/^执行/, '')
    if (!result.trace_id && result.status != null) return `${version}已排队，等待开始执行`
    return result.started_at ? `${version} · ${formatCaseResultTime(result.started_at)} · 点击查看执行详情`
      : result.state === 'needs_validation' ? '编辑配置已变更或历史结果无法匹配，请重新验证'
      : `${version}尚无匹配的执行结果`
  }

  function hasPublishedCaseVersion(record: CaseListRow) {
    return Boolean(record?.published_release_id && record?.published_revision_id)
  }

  function canSubmitCasePrepublication(record: ApiCaseVersionListRow) {
    if (record.prepublished_revision_id || !record.has_product_owner) return false
    return !hasPublishedCaseVersion(record) || record.has_unpublished_changes
  }

  function canApproveCasePrepublication(record: ApiCaseVersionListRow) {
    return Boolean(
      record.publication_status === 'prepublished' &&
        record.prepublished_revision_id &&
        record.is_product_owner
    )
  }

  function prepublicationActionWarning(rows: ApiCaseVersionListRow[], action: 'publish' | 'revert') {
    const reasons = new Set<string>()
    for (const row of rows) {
      if (row.publication_status === 'published') {
        reasons.add(action === 'publish' ? '包含已发布用例，无需重复发布' : '包含已发布用例，请使用取消发布')
      } else if (row.publication_status === 'unpublished') {
        reasons.add(action === 'publish' ? '包含未发布用例，请先提交预发布' : '包含未发布用例，无需重复退回')
      } else if (row.publication_status !== 'prepublished' || !row.prepublished_revision_id) {
        reasons.add('预发布版本信息异常，请刷新后重试')
      } else if (!row.is_product_owner) {
        reasons.add('包含非本人负责产品的用例，请联系产品负责人处理')
      }
    }
    return [...reasons].join('；')
  }

  function batchUpdatePrepublication(action: 'publish' | 'revert') {
    const version = pageVersion
    if (publicationActionCaseId.value !== null || batchPublicationAction.value !== null) return
    const selectedIds = new Set(selectedRowKeys.value.map(String))
    if (!selectedIds.size) {
      Message.warning('请选择要处理的用例')
      return
    }
    const selectedRows = (table.dataList as ApiCaseVersionListRow[]).filter((row) =>
      selectedIds.has(String(row.id))
    )
    if (selectedRows.length !== selectedIds.size) {
      Message.warning('部分选中用例已不在当前列表，请刷新后重新选择')
      return
    }
    const warning = prepublicationActionWarning(selectedRows, action)
    if (warning) {
      Message.warning(warning)
      return
    }
    if (action === 'publish') {
      void publicationReviewRef.value?.open(
        'api',
        selectedRows.map((row) => Number(row.id))
      )
      return
    }
    const title = '批量未发布'
    Modal.confirm({
      title,
      content: `确认将所选 ${selectedRows.length} 个用例退回未发布吗？旧版本仅保留历史记录，不会自动恢复发布。`,
      okText: '确认退回',
      async onBeforeOk() {
        if (version !== pageVersion || !pageActive.value) return false
        if (publicationActionCaseId.value !== null || batchPublicationAction.value !== null) {
          return false
        }
        batchPublicationAction.value = action
        const succeededIds = new Set<string>()
        const failedNames: string[] = []
        try {
          for (const row of selectedRows) {
            try {
              await revertApiCasePrepublication(Number(row.id))
              succeededIds.add(String(row.id))
            } catch {
              failedNames.push(`#${row.id} ${row.name}`)
            }
          }
          if (version !== pageVersion || !pageActive.value) return true
          selectedRowKeys.value = selectedRowKeys.value.filter(
            (id) => !succeededIds.has(String(id))
          )
          if (failedNames.length) {
            Message.warning(
              `${title}成功 ${succeededIds.size} 条，失败 ${failedNames.length} 条：${failedNames
                .slice(0, 5)
                .join('、')}。请刷新后检查状态或权限`
            )
          } else Message.success(`${title}成功，共 ${succeededIds.size} 条`)
          doRefresh(null, false, true)
          return true
        } finally {
          batchPublicationAction.value = null
        }
      },
    })
  }

  function batchPrepublicationWarning(rows: ApiCaseVersionListRow[]) {
    const reasons = new Set<string>()
    for (const row of rows) {
      if (!['unpublished', 'prepublished', 'published'].includes(row.publication_status))
        reasons.add('用例发布状态异常，请刷新后重试')
      else if (row.prepublished_revision_id || row.publication_status === 'prepublished')
        reasons.add('包含已有预发布候选的用例，请先处理旧候选')
      else if (!canSubmitCasePrepublication(row))
        reasons.add(!row.has_product_owner ? '部分产品未配置负责人，请先配置' : '包含已发布且无新修改的用例，无需重复提交')
      if (row.status !== 1) reasons.add('包含未执行通过的用例，请执行通过后再提交')
    }
    return [...reasons].join('；')
  }

  async function generateAndSubmitPrepublication(caseId: number, current: () => boolean) {
    const response = await createApiCaseRevision({
      case_id: caseId,
      summary: '从用例列表提交预发布时生成修订',
    })
    if (!current()) return false
    const revision = response?.data ?? response
    const revisionId = Number(revision?.id)
    if (!Number.isSafeInteger(revisionId) || revisionId <= 0) {
      Message.error('生成用例修订失败，请刷新后重试')
      throw Error('Invalid case revision')
    }
    await submitApiCasePrepublication(caseId, revisionId)
    return true
  }

  function batchSubmitPrepublication() {
    if (publicationActionCaseId.value !== null || batchPublicationAction.value !== null) return
    const selectedKeys = [...selectedRowKeys.value]
    const ids = new Set(selectedKeys.map(String))
    if (!ids.size) { Message.warning('请选择要提交预发布的用例'); return }
    const selected = (table.dataList as ApiCaseVersionListRow[]).filter(row => ids.has(String(row.id)))
    if (selected.length !== ids.size) { Message.warning('部分选中用例已不在当前列表，请重新选择'); return }
    const warning = batchPrepublicationWarning(selected)
    if (warning) { Message.warning(warning); return }
    const version = pageVersion
    let open = true
    const scope = () => JSON.stringify([getFormItems(conditionItems), sidebarModuleIds.value,
      activePublicationStatus.value, pagination.page, pagination.pageSize,
      userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment])
    const scopeKey = scope()
    const current = () => open && pageActive.value && version === pageVersion && scopeKey === scope()
    const fingerprint = (row: ApiCaseVersionListRow) => JSON.stringify([
      row.id, row.status, row.publication_status, row.prepublished_revision_id, row.update_time,
    ])
    const frozen = selected.map(row => ({ id: Number(row.id), fingerprint: fingerprint(row) }))
    if (frozen.some(row => !Number.isSafeInteger(row.id) || row.id <= 0)) {
      Message.warning('用例标识异常，请刷新后重新选择'); return
    }
    Modal.confirm({
      title: '批量预发布',
      content: `确认将所选 ${frozen.length} 个用例的当前编辑态生成修订并提交审核吗？提交后旧正式版本转为历史版本，用例暂停参与定时执行。`,
      okText: '提交预发布',
      onCancel() { open = false },
      onClose() { open = false },
      async onBeforeOk() {
        if (!current() || publicationActionCaseId.value !== null || batchPublicationAction.value !== null) return false
        const latest = (table.dataList as ApiCaseVersionListRow[]).filter(row => ids.has(String(row.id)))
        if (latest.length !== frozen.length || latest.some(row =>
          frozen.find(item => item.id === Number(row.id))?.fingerprint !== fingerprint(row))) {
          Message.warning('用例状态已变化，请重新选择后提交'); return false
        }
        const latestWarning = batchPrepublicationWarning(latest)
        if (latestWarning) { Message.warning(latestWarning); return false }
        batchPublicationAction.value = 'submit'
        const succeeded = new Set<string>()
        let failed = 0
        try {
          for (const row of frozen) {
            if (!current()) break
            try {
              if (!await generateAndSubmitPrepublication(row.id, current)) break
              succeeded.add(String(row.id))
            } catch { failed++ }
          }
          if (!current()) return true
          selectedRowKeys.value = selectedKeys.filter(id => !succeeded.has(String(id)))
          if (failed) Message.warning(`提交预发布成功 ${succeeded.size} 条，失败 ${failed} 条；失败项已保留勾选，请检查后重试`)
          else Message.success(`已提交预发布，共 ${succeeded.size} 条，待产品负责人审核`)
          await doRefresh(null, false, true)
          return true
        } finally { batchPublicationAction.value = null }
      },
    })
  }

  function submitCasePrepublication(record: ApiCaseVersionListRow) {
    const version = pageVersion
    if (publicationActionCaseId.value !== null || batchPublicationAction.value !== null) return
    Modal.confirm({
      title: '提交预发布',
      content: `确认根据用例「${record.name}」的当前编辑态生成修订并提交审核吗？提交后旧正式版本转为历史版本，用例暂停参与定时执行。`,
      okText: '提交预发布',
      async onBeforeOk() {
        if (version !== pageVersion || !pageActive.value) return false
        publicationActionCaseId.value = Number(record.id)
        try {
          if (!await generateAndSubmitPrepublication(Number(record.id),
            () => version === pageVersion && pageActive.value)) return true
          if (version !== pageVersion || !pageActive.value) return true
          Message.success('已生成修订并提交预发布')
          doRefresh(null, false, true)
          return true
        } catch {
          return false
        } finally {
          publicationActionCaseId.value = null
        }
      },
    })
  }

  function approveCasePrepublication(record: ApiCaseVersionListRow) {
    if (
      publicationActionCaseId.value !== null ||
      batchPublicationAction.value !== null ||
      !canApproveCasePrepublication(record)
    )
      return
    if (record.status !== 1) {
      Message.warning('用例尚未处于执行通过状态，请执行通过后再发布')
      return
    }
    void publicationReviewRef.value?.open('api', [Number(record.id)])
  }

  function revertCasePrepublication(record: ApiCaseVersionListRow) {
    const version = pageVersion
    if (
      publicationActionCaseId.value !== null ||
      batchPublicationAction.value !== null ||
      !canApproveCasePrepublication(record)
    )
      return
    Modal.confirm({
      title: '退回未发布',
      content: `确认将用例「${record.name}」退回未发布吗？不会自动恢复旧版本。`,
      okText: '确认退回',
      async onBeforeOk() {
        if (version !== pageVersion || !pageActive.value) return false
        publicationActionCaseId.value = Number(record.id)
        try {
          await revertApiCasePrepublication(Number(record.id))
          if (version !== pageVersion || !pageActive.value) return true
          Message.success('已退回未发布')
          doRefresh(null, false, true)
          return true
        } catch {
          return false
        } finally {
          publicationActionCaseId.value = null
        }
      },
    })
  }

  function unpublishCaseVersion(record: ApiCaseVersionListRow) {
    const version = pageVersion
    if (
      publicationActionCaseId.value !== null ||
      batchPublicationAction.value !== null ||
      !record.published_release_id
    )
      return
    Modal.confirm({
      title: '取消发布用例版本',
      content: `确认取消用例「${record.name}」的当前发布版本吗？取消后，定时任务将不再按已发布版本选中该 Case。`,
      okText: '确认取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (version !== pageVersion || !pageActive.value) return false
        publicationActionCaseId.value = Number(record.id)
        try {
          await unpublishApiCaseRelease(Number(record.id), Number(record.published_release_id))
          if (version !== pageVersion || !pageActive.value) return true
          Message.success('已取消发布')
          doRefresh(null, false, true)
          return true
        } catch {
          return false
        } finally {
          publicationActionCaseId.value = null
        }
      },
    })
  }

  const onCaseBatchRun = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要执行的用例')
      return
    }
    if (caseRunning.value) return

    const selectedIds = new Set(selectedRowKeys.value.map(String))
    const selectedRows = table.dataList.filter((row) =>
      selectedIds.has(String(row.id))
    ) as ApiCaseVersionListRow[]
    if (selectedRows.length !== selectedIds.size) {
      Message.warning('部分已选用例不在当前列表中，请刷新后重新选择')
      return
    }
    if (!validateSingleProject()) return
    pendingBatchRunCaseIds.value = selectedRows.map((item) => item.id)
    pendingBatchRows.value = selectedRows.map((row) => ({ ...row }))
    const version = pageVersion

    caseRunning.value = true
    try {
      const res = await getApiCaseExecutionOptions()
      if (version !== pageVersion || !pageActive.value) return
      apiPlatformLimit.value = Number(res.data?.api_platform_limit || 1)
      batchRunModalRef.value?.show({
        executionName: buildBatchExecutionName(),
        testEnv: Number(userStore.selected_environment),
        apiConcurrencyLimit: null,
        executionVersion: 'editing',
      })
    } catch (error: any) {
      Message.error(error?.msg || '获取平台并发配置失败')
    } finally {
      caseRunning.value = false
    }
  }

  function onCancelBatchRun() {
    if (caseRunning.value) return
    pendingBatchRunCaseIds.value = []
    pendingBatchRows.value = []
  }
  function buildBatchExecutionName() {
    const now = new Date()
    const pad = (value: number) => String(value).padStart(2, '0')
    return `API批量执行-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(
      now.getHours()
    )}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  }

  async function onConfirmCaseBatchRun(config: {
    executionName: string
    testEnv: number
    apiConcurrencyLimit: number | null
    executionVersion?: 'editing' | 'prepublished' | 'published'
  }) {
    if (caseRunning.value) return
    const version = pageVersion
    const caseIds = [...pendingBatchRunCaseIds.value]
    if (caseIds.length === 0) {
      Message.error('没有可执行的用例，请重新选择')
      batchRunModalRef.value?.setConfirmLoading(false)
      return
    }
    const executionVersion = config.executionVersion || 'editing'
    if (executionVersion === 'prepublished') {
      const selectedIds = new Set(caseIds.map(String))
      const missingRows = pendingBatchRows.value.filter(
        (row) => selectedIds.has(String(row.id)) && !row.prepublished_revision_id
      )
      if (missingRows.length) {
        Message.warning(
          `以下用例没有预发布修订：${missingRows
            .slice(0, 5)
            .map((row) => `${row.id}-${row.name}`)
            .join('、')}`
        )
        batchRunModalRef.value?.setConfirmLoading(false)
        return
      }
    }
    if (executionVersion === 'published') {
      const selectedIds = new Set(caseIds.map(String))
      const unpublishedRows = pendingBatchRows.value.filter(
        (row) => selectedIds.has(String(row.id)) && !hasPublishedCaseVersion(row)
      )
      if (unpublishedRows.length) {
        const names = unpublishedRows
          .slice(0, 5)
          .map((row) => `${row.id}-${row.name}`)
          .join('、')
        const suffix = unpublishedRows.length > 5 ? ` 等 ${unpublishedRows.length} 条` : ''
        Message.warning(`以下用例尚未发布，不能按已发布版本执行：${names}${suffix}`)
        batchRunModalRef.value?.setConfirmLoading(false)
        return
      }
    }
    caseRunning.value = true
    try {
      const res = await postApiCaseBatchRun(
        caseIds,
        config.testEnv,
        config.executionName,
        config.apiConcurrencyLimit,
        executionVersion
      )
      if (version !== pageVersion || !pageActive.value) return
      const reportId = res.data?.test_suite_id
      Message.success(reportId ? `${res.msg}，测试报告 ID：${reportId}` : res.msg)
      pendingBatchRunCaseIds.value = []
      batchRunModalRef.value?.close()
      doRefresh()
    } catch (error: any) {
      Message.error(error?.msg || '批量执行任务创建失败')
    } finally {
      caseRunning.value = false
      batchRunModalRef.value?.setConfirmLoading(false)
    }
  }

  function onStep(record: CaseListRow) {
    router.push({
      path: '/apitest/case/details',
      query: {
        id: record.id,
      },
    })
  }

  function openResultHistory(record: CaseListRow) {
    resultHistory.caseId = record.id
    resultHistory.title = `用例执行历史：${record.name || `Case #${record.id}`}`
    resultHistory.visible = true
  }

  async function showExecutionTrace(query: ApiCaseExecutionTraceQuery) {
    await traceDrawerRef.value?.open(query)
  }

  async function pageStepsCody(record: CaseListRow) {
    if (copyingIds.has(record.id)) return
    const version = pageVersion
    copyingIds.add(record.id)
    try {
      const response = await postApiCaseCody(record.id)
      if (version === pageVersion && pageActive.value) {
        Message.success(response.msg)
        await doRefresh(null, false, true)
      }
    } catch {
      /* 公共请求层提示错误，释放按钮供重试。 */
    } finally {
      copyingIds.delete(record.id)
    }
  }
  function closePanels() {
    pageVersion++
    pageActive.value = false
    userOptionsLoading.value = false
    panelSession.value++
    invalidateRequests()
    resetConfigurationSummaries()
    table.tableLoading.value = false
    metadataEditorRef.value?.close()
    taskBindingRef.value?.close()
    relatedTasksRef.value?.close()
    parametrizeRef.value?.close()
    configurationDrawerRef.value?.close()
    traceDrawerRef.value?.close()
    batchRunModalRef.value?.close()
    resultHistory.visible = false
    pendingBatchRunCaseIds.value = []
    pendingBatchRows.value = []
    clearPollingTimer()
    if (runNoticeTimer !== null) {
      clearTimeout(runNoticeTimer)
      runNoticeTimer = null
    }
  }
  watch(
    () => resultHistory.visible,
    (visible) => {
      if (!visible) historySession.value++
    }
  )
  onMounted(() => {
    const product = route.query.project_product
    setItemValue(conditionItems, 'project_product', typeof product === 'string' ? product : null)
    const status = route.query.publication_status
    activePublicationStatus.value =
      typeof status === 'string' && publicationTabs.some((tab) => tab.key === status)
        ? status
        : 'all'
    void getNickName()
    void doRefresh(null, false, true)
  })
  onDeactivated(closePanels)
  onActivated(() => {
    if (!pageActive.value) {
      pageActive.value = true
      void getNickName()
      void doRefresh(null, false, true)
    }
  })
  onUnmounted(closePanels)
</script>
