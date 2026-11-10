<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header>
      <TableHeader title="研发协同 / 测试用例">
        <template #header-extra>
          <a-space>
            <a-spin v-if="setupLoading" :loading="true" />
            <a-button v-if="setupError" size="small" :loading="setupLoading" @click="loadSetup"
              >重试选项</a-button
            >
            <a-spin v-if="viewSaving" :loading="true">正在保存视图…</a-spin>
            <a-button v-if="viewSaveError" size="small" :loading="viewSaving" @click="flushGridView"
              >重试保存视图</a-button
            >
            <input
              ref="importInput"
              class="mango-case-library__file"
              type="file"
              accept=".xlsx,.xls"
              @change="importCases"
            />
            <a-button
              size="small"
              :loading="importing"
              :disabled="batchSaving || deleting"
              @click="importInput?.click()"
            >
              导入
            </a-button>
            <a-button
              size="small"
              :loading="exporting"
              :disabled="batchSaving || deleting"
              @click="exportCases"
              >导出</a-button
            >
            <a-button size="small" :loading="loading || loadingMore" @click="refreshCases"
              >刷新</a-button
            >
            <a-button size="small" :disabled="draftBusy" @click="startBatchCreate"
              >批量新增</a-button
            >
            <a-button size="small" type="primary" @click="openEditor()">单个新增</a-button>
          </a-space>
        </template>
      </TableHeader>
      <div
        v-if="importProgress"
        class="mango-soft-panel mango-case-library__import-feedback"
        role="status"
      >
        <span>{{ importProgress }}</span>
        <a-button
          v-if="importRetryable"
          type="text"
          size="small"
          :loading="importing"
          @click="retryImport"
          >继续导入</a-button
        >
        <a-button v-if="!importing" type="text" size="small" @click="discardImport"
          >清除记录</a-button
        >
      </div>
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :sticky-horizontal-scroll="false"
        :show-search="false"
        show-modules
        :model-value="navigationProjectProduct"
        :module-value="navigationModule"
        @filter-change="onNavigationFilterChange"
      >
        <FunctionalCaseGrid
          class="mango-case-library__grid"
          ref="caseGrid"
          :rows="rows"
          :context-key="editorContextKey"
          :columns="columns"
          :loading="loading || inlineRecovering"
          :editable="editMode && !inlineRecovering && !importing && !batchSaving && !deleting"
          :show-hint="false"
          @cell-change="onGridCellChange"
          @selection-change="onGridSelectionChange"
          @view-change="saveGridView"
          @filter-change="handleGridFilterChange"
          @load-more="loadMoreCases"
          @insert-rows="insertDraftRows"
          @remove-rows="onGridRemoveRows"
          @sort-change="handleGridSortChange"
        >
          <template #summary>
            <span>已选择 {{ selectedRows.length }} 条</span>
            <a-tag v-if="editMode" size="small" :color="inlineSaveMeta.color">
              {{ inlineSaveMeta.text }}
            </a-tag>
            <span v-if="batchMode">批量新增草稿 {{ draftRows.length }} 行</span>
            <template v-if="loadError"></template>
            <span v-else-if="filterActive && loadingAllForFilter">
              正在加载完整数据并应用筛选（{{ persistedRowCount }} / {{ pageState.total }}）…
            </span>
            <span v-else-if="filterActive">已对全部 {{ pageState.total }} 条用例应用表格筛选</span>
            <span v-else-if="loadingMore">正在加载更多…</span>
            <span v-else-if="hasMore"
              >已加载 {{ persistedRowCount }} / {{ pageState.total }} 条，向下滚动继续加载</span
            >
            <span v-else>已加载全部 {{ pageState.total }} 条</span>
          </template>
          <template #toolbar>
            <template v-if="batchMode">
              <a-button
                size="small"
                :disabled="draftBusy"
                @click="insertDraftRows({ index: 0, count: 10 })"
              >
                新增 10 行
              </a-button>
              <a-button
                size="small"
                :disabled="draftBusy || !selectedDraftRows.length"
                @click="copyDraftRows"
              >
                复制所选行
              </a-button>
              <a-button
                size="small"
                :disabled="draftBusy || !selectedDraftRows.length"
                @click="removeSelectedDraftRows"
              >
                删除草稿行
              </a-button>
              <a-button
                size="small"
                :loading="batchSaving"
                :disabled="importing || deleting"
                @click="saveDraftRows"
              >
                保存全部
              </a-button>
              <a-button size="small" :disabled="draftBusy" @click="exitBatchCreate">
                退出批量新增
              </a-button>
            </template>
            <a-tooltip :content="editMode ? '可直接编辑表格单元格' : '开启后可直接编辑表格单元格'">
              <span class="mango-case-library__edit-toggle">
                编辑模式
                <a-switch
                  size="small"
                  :disabled="draftBusy"
                  :model-value="editMode"
                  @change="toggleEditMode"
                />
              </span>
            </a-tooltip>
            <a-button
              size="small"
              :disabled="selectedPersistedRows.length !== 1"
              @click="openEditor(selectedPersistedRows[0])"
            >
              编辑详情
            </a-button>
            <a-button
              size="small"
              :disabled="selectedPersistedRows.length !== 1"
              @click="openHistory(selectedPersistedRows[0])"
            >
              历史版本
            </a-button>
            <a-button
              size="small"
              :disabled="selectedPersistedRows.length !== 1"
              @click="openAutomationBinding(selectedPersistedRows[0])"
            >
              自动化绑定
            </a-button>
            <a-button size="small" @click="openCreatePlan">新建测试计划</a-button>
            <a-button size="small" :disabled="!selectedPersistedRows.length" @click="openAddPlan">
              加入测试计划
            </a-button>
            <a-button
              size="small"
              :disabled="!selectedPersistedRows.length"
              @click="createDefectFromCases"
              >创建缺陷</a-button
            >
          </template>
        </FunctionalCaseGrid>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <CaseEditor
    ref="editor"
    :users="userOptions"
    :context-key="editorContextKey"
    :defaults="editorDefaults"
    @saved="refreshCases()"
  />

  <CaseHistoryDrawer ref="history" :context-key="editorContextKey" />

  <CasePlanDialog
    ref="planDialog"
    :users="userOptions"
    :context-key="editorContextKey"
    :defaults="editorDefaults"
  />
  <CaseBindingDialog ref="bindingDialog" :context-key="editorContextKey" @saved="refreshCases()" />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
  import FunctionalCaseGrid from '@/components/table/FunctionalCaseGrid.vue'
  import type { FunctionalGridColumn } from '@/components/table/functional-case-grid'
  import type { FunctionalGridCellChange } from '@/components/table/functional-case-grid'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getUserName } from '@/api/user/user'
  import { getFunctionalGridView, saveFunctionalGridView } from '@/api/functional-test'
  import {
    CASE_LIBRARY_GRID_KEY,
    CASE_LIBRARY_GRID_LAYOUT_VERSION,
    createCaseLibraryColumns,
    mergeLibraryGridColumns,
  } from './config'
  import type { LibraryGridPreferences } from './config'
  import { useCaseLibraryList } from './composables/useCaseLibraryList'
  import { useCaseInlineSave } from './composables/useCaseInlineSave'
  import { useCaseSpreadsheet } from './composables/useCaseSpreadsheet'
  import { useCaseDrafts } from './composables/useCaseDrafts'
  import { isPersistedCaseRow, normalizeLibraryCaseRow } from './rows'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'

  import CaseEditor from './components/CaseEditor.vue'
  import CaseHistoryDrawer from './components/CaseHistoryDrawer.vue'
  import CaseBindingDialog from './components/CaseBindingDialog.vue'
  import CasePlanDialog from './components/CasePlanDialog.vue'
  import type {
    CaseEditorHandle,
    CaseBindingHandle,
    CaseBindingSubject,
    CasePlanHandle,
    CasePlanSubject,
    CaseHistoryHandle,
    CaseHistorySubject,
    LibraryCaseEditorRecord,
    CaseUserOption,
    LibraryCaseRow,
    LibraryGridHandle,
  } from './types'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const enumStore = useEnum()
  const userStore = useUserStore()
  const router = useRouter()
  const route = useRoute()
  const pagePath = route.path
  const editor = ref<CaseEditorHandle | null>(null)
  const history = ref<CaseHistoryHandle | null>(null)
  const bindingDialog = ref<CaseBindingHandle | null>(null)
  const planDialog = ref<CasePlanHandle | null>(null)
  const rows = ref<LibraryCaseRow[]>([])
  const caseGrid = ref<LibraryGridHandle | null>(null)
  const columns = ref<FunctionalGridColumn[]>(createCaseLibraryColumns(enumStore, []))
  const editMode = ref(false)
  const selectedRows = ref<LibraryCaseRow[]>([])
  const importInput = ref<HTMLInputElement>()
  const userOptions = ref<CaseUserOption[]>([])
  const setupLoading = ref(false),
    setupError = ref(false)
  const viewSaving = ref(false),
    viewSaveError = ref(false)
  let setupActive = true,
    setupRequest = 0,
    viewRevision = 0,
    navigationIntent = 0
  const navigationProjectProduct = ref<number>()
  const navigationModule = ref<number>()
  const sortState = reactive<{ field?: string; direction?: 'asc' | 'desc' }>({})
  let viewTimer: number | undefined
  let viewGeneration = 0
  let viewWrite: Promise<void> | null = null
  let pendingView: {
    identity: string
    columns: Array<Pick<FunctionalGridColumn, 'field' | 'visible' | 'width'>>
  } | null = null

  const selectedPersistedRows = computed(() => selectedRows.value.filter(isPersistedCaseRow))

  async function refreshCases() {
    const context = editorContextKey.value,
      generation = viewGeneration
    await flushInlineUpdates()
    if (
      !setupActive ||
      generation !== viewGeneration ||
      context !== editorContextKey.value ||
      route.path !== pagePath
    )
      return false
    return loadCases(true, false)
  }

  async function handleGridSortChange(payload: { field: string; direction: 'asc' | 'desc' }) {
    if (draftRows.value.length) {
      Message.warning('请先保存或退出批量新增，再对全部用例排序')
      return
    }
    const context = editorContextKey.value
    await flushInlineUpdates()
    if (context !== editorContextKey.value || route.path !== pagePath) return
    sortState.field = payload.field
    sortState.direction = payload.direction
  }

  async function onNavigationFilterChange(filter: {
    projectProduct: number | null
    module: number | null
  }) {
    const intent = ++navigationIntent,
      identity = pageIdentity.value
    await flushInlineUpdates()
    if (intent !== navigationIntent || identity !== pageIdentity.value || route.path !== pagePath)
      return
    navigationProjectProduct.value = filter.projectProduct ?? undefined
    navigationModule.value = filter.module ?? undefined
  }

  async function openHistory(row: CaseHistorySubject) {
    await history.value?.open(row)
  }

  function openAutomationBinding(row: CaseBindingSubject) {
    bindingDialog.value?.open(row)
  }

  const pageIdentity = computed(() =>
    JSON.stringify([
      userStore.userId,
      userStore.roleId,
      userStore.token,
      userStore.selected_environment,
    ])
  )
  const editorContextKey = computed(() =>
    JSON.stringify([
      route.path,
      userStore.userId,
      userStore.roleId,
      userStore.token,
      userStore.selected_environment,
      navigationProjectProduct.value,
      navigationModule.value,
    ])
  )
  const editorDefaults = computed(
    () =>
      navigationCreateRef.value?.getCreateDefaults() ?? {
        projectProduct: navigationProjectProduct.value ?? null,
        module: navigationModule.value ?? null,
      }
  )

  async function openEditor(row?: LibraryCaseEditorRecord) {
    await editor.value?.open(row)
  }

  const {
    pageState,
    loading,
    loadingMore,
    loadError,
    filterActive,
    loadingAllForFilter,
    persistedRowCount,
    hasMore,
    loadCases,
    loadMoreCases,
    retryCases,
    handleGridFilterChange,
  } = useCaseLibraryList({
    rows,
    context: () => JSON.stringify([editorContextKey.value, sortState.field, sortState.direction]),
    identity: () => pageIdentity.value,
    available: () => route.path === pagePath,
    query: () => ({
      project_product: navigationProjectProduct.value,
      module: navigationModule.value,
      include_descendants: navigationModule.value ? true : undefined,
      sort_field: sortState.field,
      sort_order: sortState.field ? sortState.direction ?? 'asc' : undefined,
    }),
    normalize: normalizeLibraryCaseRow,
    clearSelection: () => {
      selectedRows.value = []
    },
  })

  const { saveInline, flushInlineUpdates, inlineSaveMeta, inlineSavingCount, inlineRecovering } =
    useCaseInlineSave({
      context: () => editorContextKey.value,
      ownsRow: (row) => rows.value.some((item) => item === row),
      refreshCells: (id, fields) => caseGrid.value?.refreshRowCells?.(id, fields),
      reload: () => loadCases(false),
    })
  onBeforeRouteLeave(async () => {
    await Promise.all([flushInlineUpdates(), flushGridView()])
    return true
  })

  function onGridCellChange(event: FunctionalGridCellChange) {
    const row = rows.value.find((item) => item === event.row)
    if (!row || !editMode.value || importing.value || batchSaving.value || deleting.value) return
    saveInline({ ...event, row })
  }
  function onGridSelectionChange(selection: object[]) {
    selectedRows.value = rows.value.filter((row) => selection.includes(row))
  }
  function onGridRemoveRows(selection: object[]) {
    const owned = rows.value.filter((row) => selection.includes(row))
    if (selection.length && !owned.length) return
    removeGridRows(owned)
  }

  const {
    busy: draftBusy,
    batchMode,
    batchSaving,
    deleting,
    draftRows,
    selectedDraftRows,
    insertDraftRows,
    startBatchCreate,
    copyDraftRows,
    removeSelectedDraftRows,
    saveDraftRows,
    removeGridRows,
    exitBatchCreate,
  } = useCaseDrafts({
    rows,
    selection: selectedRows,
    context: () => editorContextKey.value,
    identity: () => pageIdentity.value,
    available: () => route.path === pagePath,
    blocked: () => importing.value || inlineRecovering.value,
    enableEditing: () => {
      editMode.value = true
    },
    defaults: () => {
      const defaults = editorDefaults.value
      const sample = rows.value.find(
        (row) =>
          !row.__draft &&
          String(row.project_product_id) === String(defaults.projectProduct) &&
          (defaults.module === null || String(row.module_id) === String(defaults.module))
      )
      return {
        productId: defaults.projectProduct,
        productPath: sample?.project_product_path ?? '',
        moduleId: defaults.module,
        modulePath: defaults.module === null ? '' : sample?.module_path ?? '',
        ownerId: userStore.userId || null,
        ownerName: userStore.nickName || userStore.userName || '-',
      }
    },
    flush: flushInlineUpdates,
    countChange: (delta) => {
      pageState.total = Math.max(0, pageState.total + delta)
      if (delta > 0) pageState.page = Math.max(pageState.page, 1)
    },
  })

  const {
    importing,
    exporting,
    importProgress,
    importRetryable,
    importCases,
    retryImport,
    discardImport,
    exportCases: writeCaseExport,
  } = useCaseSpreadsheet({
    context: () => editorContextKey.value,
    available: () => route.path === pagePath && !batchSaving.value && !deleting.value,
    exportQuery: () => ({
      page: 1,
      pageSize: 10000,
      id__in: selectedPersistedRows.value.length
        ? selectedPersistedRows.value.map((row) => row.id).join(',')
        : undefined,
      project_product: navigationProjectProduct.value,
      module: navigationModule.value,
      include_descendants: navigationModule.value ? true : undefined,
    }),
    flush: flushInlineUpdates,
    reload: () => loadCases(),
  })

  async function exportCases() {
    if (selectedDraftRows.value.length) {
      Message.warning('请先保存选中的草稿用例再导出')
      return
    }
    await writeCaseExport()
  }

  async function toggleEditMode(value: boolean | string | number) {
    const enabled = value === true
    if (!enabled && inlineSavingCount.value) await flushInlineUpdates()
    editMode.value = enabled
  }

  function selectedPlanCases(): CasePlanSubject[] {
    return selectedPersistedRows.value.map((row) => ({
      id: row.id,
      productId: row.project_product_id,
      ownerId: row.owner_id,
    }))
  }

  async function openAddPlan() {
    await planDialog.value?.openJoin(selectedPlanCases())
  }

  async function openCreatePlan() {
    await planDialog.value?.openCreate(selectedPlanCases())
  }

  function createDefectFromCases() {
    const productIds = [
      ...new Set(selectedPersistedRows.value.map((item) => item.project_product_id)),
    ]
    if (productIds.length !== 1) {
      Message.warning('请选择同一项目产品下的用例')
      return
    }
    router.push({
      path: '/functional-test/defect/index',
      query: {
        project_product: productIds[0],
        case_ids: selectedPersistedRows.value.map((item) => item.id).join(','),
      },
    })
  }

  function saveGridView(value: FunctionalGridColumn[]) {
    ++viewRevision
    columns.value = value
    persistGridView()
  }

  function persistGridView() {
    pendingView = {
      identity: pageIdentity.value,
      columns: columns.value.map(({ field, visible, width }) => ({ field, visible, width })),
    }
    viewSaveError.value = false
    window.clearTimeout(viewTimer)
    viewTimer = window.setTimeout(() => {
      viewTimer = undefined
      void flushGridView()
    }, 500)
  }

  async function flushGridView(): Promise<void> {
    window.clearTimeout(viewTimer)
    viewTimer = undefined
    if (!setupActive || route.path !== pagePath) return
    if (viewWrite) {
      await viewWrite
      if (pendingView && !viewSaveError.value) await flushGridView()
      return
    }
    const snapshot = pendingView
    if (!snapshot || snapshot.identity !== pageIdentity.value) return
    const generation = viewGeneration
    const current = () =>
      setupActive &&
      route.path === pagePath &&
      generation === viewGeneration &&
      snapshot.identity === pageIdentity.value
    pendingView = null
    viewSaving.value = true
    viewSaveError.value = false
    const task = Promise.resolve()
      .then(async () => {
        if (!current()) return
        await saveFunctionalGridView({
          grid_key: CASE_LIBRARY_GRID_KEY,
          name: '默认视图',
          config: {
            columns: snapshot.columns,
            layout_version: CASE_LIBRARY_GRID_LAYOUT_VERSION,
          },
          is_default: true,
        })
      })
      .catch(() => {
        if (current()) {
          if (!pendingView) pendingView = snapshot
          viewSaveError.value = true
        }
      })
    viewWrite = task
    try {
      await task
    } finally {
      if (viewWrite === task) viewWrite = null
      if (current()) viewSaving.value = false
    }
    if (current() && pendingView && !viewSaveError.value) await flushGridView()
  }

  async function loadSetup() {
    if (!setupActive || route.path !== pagePath) return
    const identity = pageIdentity.value,
      request = ++setupRequest,
      revision = viewRevision
    const current = () =>
      setupActive &&
      route.path === pagePath &&
      identity === pageIdentity.value &&
      request === setupRequest
    setupLoading.value = true
    setupError.value = false
    try {
      if (viewWrite) await viewWrite
      if (!current()) return
      if (pendingView?.identity === pageIdentity.value) {
        await flushGridView()
        if (viewSaveError.value || !current()) return
      }
      await enumStore.getEnum()
      if (!current()) return
      const [users, view] = await Promise.all([
        getUserName(),
        getFunctionalGridView(CASE_LIBRARY_GRID_KEY),
      ])
      if (!current()) return
      userOptions.value = users.data ?? []
      const defaults = createCaseLibraryColumns(enumStore, userOptions.value)
      if (revision !== viewRevision) {
        columns.value = columns.value.map((column) => ({
          ...defaults.find((item) => item.field === column.field),
          ...column,
          options: defaults.find((item) => item.field === column.field)?.options,
        }))
        return
      }
      const views: Array<{ is_default: boolean; config?: LibraryGridPreferences }> = view.data ?? []
      const merged = mergeLibraryGridColumns(
        defaults,
        views.find((item) => item.is_default)?.config ?? {}
      )
      columns.value = merged.columns
      if (merged.upgrade) persistGridView()
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), setupError.value = true)
    } finally {
      if (current()) setupLoading.value = false
    }
  }

  watch(
    pageIdentity,
    () => {
      ++setupRequest
      ++viewGeneration
      ++viewRevision
      window.clearTimeout(viewTimer)
      pendingView = null
      viewSaving.value = false
      viewSaveError.value = false
      userOptions.value = []
      columns.value = createCaseLibraryColumns(enumStore, [])
      setupLoading.value = false
      setupError.value = false
      void loadSetup()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    void loadSetup()
  })
  onDeactivated(() => {
    setupActive = false
    ++viewGeneration
    ++setupRequest
    ++navigationIntent
    setupLoading.value = false
    viewSaving.value = false
    window.clearTimeout(viewTimer)
  })
  onActivated(() => {
    if (!setupActive) {
      setupActive = true
      void loadSetup()
    }
  })
  onBeforeUnmount(() => {
    setupActive = false
    ++viewGeneration
    ++setupRequest
    ++navigationIntent
    window.clearTimeout(viewTimer)
  })
</script>

<style lang="less" scoped>
  .mango-case-library__import-feedback {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: var(--m-page-gap);
    white-space: normal;
    overflow-wrap: anywhere;
  }
  .mango-case-library__edit-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--m-text-2);
  }
  .mango-case-library__grid {
    height: 100%;
    min-height: 0;
    flex: 1;
  }
  .mango-case-library__file {
    display: none;
  }
</style>
