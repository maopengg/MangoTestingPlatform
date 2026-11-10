<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="测试用例" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="getConditionValue('project_product')"
        :module-value="getConditionValue('module')"
        :reset-key="sidebarResetKey"
        show-modules
        @filter-change="onNavigationFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="list.users.value"
                  :loading="list.usersLoading.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="list.users.value"
                  :loading="list.usersLoading.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :loading="enumsLoading"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'level'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :loading="enumsLoading"
                  :options="enumStore.case_level"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :loading="enumsLoading"
                  :options="enumStore.api_case_scenario_layer"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :loading="enumsLoading"
                  :options="enumStore.api_case_scenario_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :loading="enumsLoading"
                  :options="enumStore.api_case_scenario_tag"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  multiple
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #tabs>
          <TableTabs :active-key="activePublicationStatus" @tab-click="switchPublicationTab">
            <a-tab-pane v-for="tab in publicationTabs" :key="tab.key" :title="tab.title" />
            <template #extra>
          <a-space>
            <div>
              <a-button
                size="small"
                status="success"
                :loading="actions.pending.value?.kind === 'batch-run'"
                :disabled="!!actions.pending.value"
                @click="actions.batchRun(selectedRowKeys)" data-testid="qa-views-uitest-case-button-批量执行"
                >批量执行
              </a-button>
            </div>
            <a-button size="small" status="warning" :disabled="!!actions.pending.value" @click="openTaskBinding" data-testid="qa-views-uitest-case-button-设为定时任务">设为定时任务</a-button>
            <div>
              <a-button  size="small" type="primary" @click="onAdd" data-testid="qa-views-uitest-case-button-新增">新增</a-button>
            </div>
            <div>
              <a-button  size="small" status="danger" :disabled="!!actions.pending.value" @click="actions.remove(selectedRowKeys)" :loading="actions.pending.value?.kind === 'delete'" data-testid="qa-views-uitest-case-button-批量删除">批量删除</a-button>
            </div>
          </a-space>
            </template>
          </TableTabs>
        </template>

      
      
      
      <a-alert v-if="actions.error.value" type="error">{{ actions.error.value }}</a-alert>
      <a-table
        class="mango-native-scroll-table"
        :bordered="false"
        :columns="visibleTableColumns"
        :data="batchSelectableDataList"
        :loading="list.loading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        row-key="id"
        :scroll="{ x: 2000, y: '100%' }"
        @selection-change="onUiCaseSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of visibleTableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :fixed="item.fixed"
            :title="item.title"
            :tooltip="item.tooltip"
            :width="item.width"
          >
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
            <template v-else-if="item.key === 'level'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record?.level]" size="small"
                >{{ record.level !== null ? enumStore.case_level[record.level]?.title || '-' : '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'publication_status'" #cell="{ record }">
              <a-tag :color="record.publication_status === 'published' ? 'green' : record.publication_status === 'prepublished' ? 'orange' : 'gray'" size="small">
                {{ publicationTabs.find((tab) => tab.key === record.publication_status)?.title || '未发布' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record.module) }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="caseActions(record)"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <CasePublicationReviewModal ref="publicationReviewRef" @published="saved()" />
  <UiCaseMetadataEditor ref="metadataEditorRef" :user-options="list.users.value" :users-loading="list.usersLoading.value" :users-error="list.usersError.value" :enums-loading="enumsLoading" :enums-error="enumsError" @retry-users="list.loadUsers()" @retry-enums="loadEnums()" @saved="saved()" />
  <UiCaseSuiteEditor ref="suiteEditorRef" @saved="saved()" />
  <UiCaseTaskBindingModal ref="taskBindingRef" @saved="saved()" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { usePagination } from '@/hooks/table'
  import { usePagePolling, isPendingExecution } from '@/hooks/use-page-polling'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { usePageData } from '@/store/page-data'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { getItemValue, setItemValue, formatProjectProductPath, formatModulePath } from '@/utils/business-format'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import CasePublicationReviewModal from '@/components/business/CasePublicationReviewModal.vue'
  import UiCaseMetadataEditor from './components/UiCaseMetadataEditor.vue'
  import UiCaseSuiteEditor from './components/UiCaseSuiteEditor.vue'
  import UiCaseTaskBindingModal from './components/UiCaseTaskBindingModal.vue'
  import { createSearchItems, tableColumns, publicationTabs } from './config'
  import { caseListQuery, caseOptionId, type CaseId, type UiCaseRow } from './case-list-records'
  import { useUiCaseList } from './composables/useUiCaseList'
  import { useUiCaseActions } from './composables/useUiCaseActions'
  import { useCaseListScope } from './composables/useCaseListScope'

  const route = useRoute(), router = useRouter(), userStore = useUserStore(), enumStore = useEnum()
  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const metadataEditorRef = ref<InstanceType<typeof UiCaseMetadataEditor> | null>(null)
  const suiteEditorRef = ref<InstanceType<typeof UiCaseSuiteEditor> | null>(null)
  const taskBindingRef = ref<InstanceType<typeof UiCaseTaskBindingModal> | null>(null)
  const publicationReviewRef = ref<InstanceType<typeof CasePublicationReviewModal> | null>(null)
  const conditionItems = createSearchItems(), visibleTableColumns = tableColumns
  const headerConditionItems = computed(() => conditionItems.filter(item => !['project_product', 'module'].includes(String(item.key))))
  const activePublicationStatus = ref('all'), sidebarResetKey = ref(0), sidebarModuleIds = ref<CaseId[]>([])
  const selectedRowKeys = ref<CaseId[]>([]), showCheckedAll = true, enumsLoading = ref(false), enumsError = ref('')
  let enumSequence = 0, routeKey = ''
  const pagination = usePagination(() => { selectedRowKeys.value = []; actions.closeConfirmation(); return list.load(true) }, () => list.loading)
  function closeWindows() { metadataEditorRef.value?.close(); suiteEditorRef.value?.close(); taskBindingRef.value?.close(); publicationReviewRef.value?.invalidate() }
  const scope = useCaseListScope({
    invalidate(clear) { enumSequence++; enumsLoading.value = false; closeWindows(); actions.invalidate(); list.invalidate(clear); selectedRowKeys.value = [] },
    resume() { applyRouteFilters(); void list.load(false); void list.loadUsers(); if (enumsError.value) void loadEnums() },
  })
  const query = () => caseListQuery(getFormItems(conditionItems), activePublicationStatus.value, sidebarModuleIds.value, pagination.page, pagination.pageSize)
  const list = useUiCaseList({ available: scope.available, capture: scope.capture, query, total: pagination.setTotalSize, page: value => { pagination.page = value }, loaded() {
    const ids = new Set(list.rows.value.map(row => String(row.id)))
    selectedRowKeys.value = selectedRowKeys.value.filter(id => ids.has(String(id)))
    if (list.rows.value.some(isPendingExecution)) pagePolling.start(); else pagePolling.stop()
  } })
  const actions = useUiCaseActions({ available: scope.available, capture: scope.capture, environment: () => userStore.selected_environment, rows: () => list.rows.value, filterKey: () => JSON.stringify(query()),
    beforeWrite: () => list.invalidateRows(), committed: async (kind, ids, target) => {
      selectedRowKeys.value = []; list.invalidateRows()
      const selected = new Set(ids.map(String))
      if (kind === 'delete') { list.rows.value = list.rows.value.filter(row => !selected.has(String(row.id))); pagination.setTotalSize(Math.max(0, pagination.pageCount - selected.size)) }
      if (kind === 'publication' && target) list.rows.value = list.rows.value.map(row => selected.has(String(row.id)) ? { ...row, publication_status: target } : row)
      if (kind === 'run' || kind === 'batch-run') { list.rows.value = list.rows.value.map(row => selected.has(String(row.id)) ? { ...row, status: 2 } : row); pagePolling.start() }
      await list.load(false)
    },
  })
  const pagePolling = usePagePolling(context => list.load(false, context.isCurrent), () => list.invalidateRows())
  const selectedRows = computed(() => list.rows.value.filter(row => selectedRowKeys.value.some(id => String(id) === String(row.id))))
  const batchSelectableDataList = computed(() => {
    const project = selectedRows.value[0]?.project_product?.project?.id
    return list.rows.value.map(row => ({ ...row, disabled: project != null && row.project_product?.project?.id != null && String(project) !== String(row.project_product.project.id) }))
  })
  function onUiCaseSelectionChange(keys: CaseId[]) {
    const wanted = new Set(keys.map(String)), rows = list.rows.value.filter(row => wanted.has(String(row.id)))
    const project = selectedRows.value[0]?.project_product?.project?.id ?? rows[0]?.project_product?.project?.id
    selectedRowKeys.value = rows.filter(row => project == null || String(row.project_product?.project?.id) === String(project)).map(row => row.id)
    if (selectedRowKeys.value.length !== keys.length) Message.warning('一次批量执行只能选择同一项目下的用例')
  }
  function getConditionValue(key: string) { return getItemValue(conditionItems, key) }
  function doRefresh() { return list.load(true) }
  function saved() { if (!scope.available()) return; list.invalidateRows(); void list.load(false) }
  function onSearchRefresh() { pagination.page = 1; selectedRowKeys.value = []; actions.closeConfirmation(); publicationReviewRef.value?.invalidate(); return list.load(true) }
  function switchPublicationTab(key: string | number) { activePublicationStatus.value = String(key); return onSearchRefresh() }
  function onNavigationFilterChange(value: { projectProduct: unknown; module: unknown; moduleIds?: CaseId[] }) {
    setItemValue(conditionItems, 'project_product', caseOptionId(value.projectProduct))
    setItemValue(conditionItems, 'module', value.module === '__all__' ? null : caseOptionId(value.module))
    sidebarModuleIds.value = [...(value.moduleIds ?? [])]; return onSearchRefresh()
  }
  function onResetSearch() {
    for (const item of conditionItems) { if (['project_product', 'module'].includes(String(item.key))) item.value = null; else if (item.reset) item.reset(); else item.value = item.multiple ? [] : '' }
    sidebarModuleIds.value = []; sidebarResetKey.value++; return onSearchRefresh()
  }
  function getEnumTitle(options: unknown, value: unknown): string {
    if (!Array.isArray(options)) return '-'
    const row = options.find(item => item && typeof item === 'object' && String(item.key) === String(value))
    return typeof row?.title === 'string' ? row.title : '-'
  }
  async function loadEnums() {
    if (!scope.available()) return
    const valid = scope.capture(), request = ++enumSequence, current = () => valid() && request === enumSequence
    enumsLoading.value = true; enumsError.value = ''
    try {
      await enumStore.getEnum()
      if (current() && !(['task_status', 'case_level', 'api_case_scenario_layer', 'api_case_scenario_type'] as const).every(key => enumStore[key]?.length)) (reportLoadError(undefined, "枚举选项加载失败，请重试", false), (reportLoadError(undefined, "枚举选项加载失败，请重试", false), enumsError.value = '枚举选项加载失败，请重试'))
    }
    catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "枚举选项加载失败，请重试", false), enumsError.value = '枚举选项加载失败，请重试') }
    finally { if (request === enumSequence) enumsLoading.value = false }
  }
  function applyRouteFilters() {
    if (routeKey === route.fullPath) return
    routeKey = route.fullPath
    const status = route.query.publication_status
    activePublicationStatus.value = typeof status === 'string' && publicationTabs.some(tab => tab.key === status) ? status : 'all'
    try { setItemValue(conditionItems, 'project_product', caseOptionId(route.query.project_product)) } catch { setItemValue(conditionItems, 'project_product', null) }
    setItemValue(conditionItems, 'module', null); sidebarModuleIds.value = []; pagination.page = 1
  }
  function onAdd() {
    const defaults = navigationCreateRef.value?.getCreateDefaults()
    metadataEditorRef.value?.open(null, { projectProduct: defaults?.projectProduct ?? null, module: defaults?.module === '__all__' ? null : defaults?.module ?? null })
  }
  function onUpdate(row: UiCaseRow) { metadataEditorRef.value?.open(row) }
  function clickSuite(row: UiCaseRow) { suiteEditorRef.value?.open(row) }
  function openTaskBinding() { if (!selectedRowKeys.value.length) { Message.warning('请选择要添加定时任务的用例'); return }; taskBindingRef.value?.open([...selectedRowKeys.value]) }
  function onClick(row: UiCaseRow) { usePageData().setRecord(row); return router.push({ path: '/uitest/case/details', query: { id: String(row.id) } }) }
  function review(row: UiCaseRow) {
    // 公共发布审核仍为安全整数协议；不将长字符串ID静默截断后审核另一条资产。
    const id = Number(row.id)
    if (!Number.isSafeInteger(id) || id <= 0) { Message.error('当前用例标识无法用于发布审核，请检查数据'); return }
    void publicationReviewRef.value?.open('ui', [id])
  }
  function caseActions(row: UiCaseRow) {
    const pending = actions.pending.value, busy = pending !== null, matching = pending?.ids.some(id => String(id) === String(row.id))
    return [
      { label: '执行', loading: matching && pending?.kind === 'run', disabled: busy, onClick: () => actions.run(row.id) },
      { label: '步骤', onClick: () => onClick(row) }, { label: '套件', onClick: () => clickSuite(row) }, { label: '编辑', onClick: () => onUpdate(row) },
      { label: '复制', loading: matching && pending?.kind === 'copy', disabled: busy, onClick: () => actions.copy(row.id) },
      { label: '提交预发布', hidden: row.publication_status !== 'unpublished', loading: matching && pending?.kind === 'publication', disabled: busy, onClick: () => actions.publication(row.id, 'prepublished') },
      { label: '通过发布', hidden: row.publication_status !== 'prepublished', disabled: busy, onClick: () => review(row) },
      { label: '退回未发布', hidden: row.publication_status === 'unpublished', danger: true, loading: matching && pending?.kind === 'publication', disabled: busy, onClick: () => actions.publication(row.id, 'unpublished') },
      { label: '删除', danger: true, loading: matching && pending?.kind === 'delete', disabled: busy, onClick: () => actions.remove([row.id]) },
    ]
  }
  onMounted(() => { applyRouteFilters(); void list.loadUsers(); void loadEnums(); void list.load(true) })
</script>
