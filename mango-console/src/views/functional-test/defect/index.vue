<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header><TableHeader title="研发协同 / 缺陷管理" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        show-modules
        :sticky-horizontal-scroll="false"
        :model-value="navigationProjectProduct"
        :module-value="navigationModule"
        @filter-change="onNavigationFilterChange"
        @search="autoSearch.run"
        @reset-search="autoSearch.cancel(); reset(); autoSearch.sync()"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="autoSearch.run">
            <a-form-item label="关键词"
              ><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="filters.keyword" allow-clear placeholder="编号或标题"
            /></a-form-item>
            <a-form-item label="状态"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.status"
                :loading="enumsLoading"
                :options="statusOptions"
                :field-names="fieldNames"
                allow-clear
            /></a-form-item>
            <a-form-item label="严重程度"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.severity"
                :loading="enumsLoading"
                :options="severityOptions"
                :field-names="fieldNames"
                allow-clear
            /></a-form-item>
            <a-form-item label="优先级"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.priority"
                :loading="enumsLoading"
                :options="priorityOptions"
                :field-names="fieldNames"
                allow-clear
            /></a-form-item>
            <a-form-item label="缺陷类型"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.defect_type"
                :loading="enumsLoading"
                :options="typeOptions"
                :field-names="fieldNames"
                allow-clear
            /></a-form-item>
            <a-form-item label="缺陷来源"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.source_type"
                :loading="enumsLoading"
                :options="sourceOptions"
                :field-names="fieldNames"
                allow-clear
            /></a-form-item>
            <a-form-item label="经办人"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.assignee"
                :loading="usersLoading"
                :options="userOptions"
                :field-names="fieldNames"
                allow-search
                allow-clear
            /></a-form-item>
            <a-form-item label="报告人"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.reporter"
                :loading="usersLoading"
                :options="userOptions"
                :field-names="fieldNames"
                allow-search
                allow-clear
            /></a-form-item>
            <a-form-item label="来源计划"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.source_plan"
                :loading="searchPlansLoading"
                :options="searchPlanOptions"
                allow-search
                allow-clear
            /></a-form-item>
            <a-form-item label="创建日期"
              ><a-range-picker @change="autoSearch.schedule" v-model="filters.create_range" value-format="YYYY-MM-DD" allow-clear
            /></a-form-item>
            <a-form-item label="更新日期"
              ><a-range-picker @change="autoSearch.schedule" v-model="filters.update_range" value-format="YYYY-MM-DD" allow-clear
            /></a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-popover trigger="click" position="br">
              <a-button size="small">列设置</a-button>
              <template #content>
                <div class="mango-defect-page__column-settings">
                  <div
                    v-for="(column, index) in configuredColumns"
                    :key="columnKey(column)"
                    class="mango-defect-page__column-setting"
                  >
                    <a-checkbox
                      :model-value="column.visible !== false"
                      :disabled="fixedDefectColumn(column)"
                      @change="setColumnVisible(index, $event)"
                      >{{ column.title }}</a-checkbox
                    >
                    <a-space :size="2"
                      ><a-button
                        size="mini"
                        :disabled="fixedDefectColumn(column) || index === 0"
                        @click="moveColumn(index, -1)"
                        >上移</a-button
                      ><a-button
                        size="mini"
                        :disabled="
                          fixedDefectColumn(column) || index === configuredColumns.length - 1
                        "
                        @click="moveColumn(index, 1)"
                        >下移</a-button
                      ></a-space
                    >
                  </div>
                  <a-button size="mini" long @click="resetColumns">恢复默认</a-button>
                </div>
              </template>
            </a-popover>
            <a-button size="small" :loading="loading" @click="refreshAll">刷新</a-button>
            <a-button size="small" type="primary" @click="openEditor()">新建缺陷</a-button>
          </a-space>
        </template>
        <div class="mango-defect-page__feedback">
          
          
          
          
          
          <MangoRequestFeedback v-if="mutationError" :message="(mutationError)" />
          <a-alert v-if="columnStorageError" type="warning"
            >列设置暂未保存。<a-button size="mini" @click="saveColumns">重试保存</a-button></a-alert
          >
        </div>
        <MangoPanelSpin :loading="statsLoading">
          <div class="mango-defect-page__stats">
            <span
              >未关闭 <strong>{{ stats.open_count || 0 }}</strong></span
            >
            <span
              >我的待处理 <strong>{{ stats.my_pending_count || 0 }}</strong></span
            >
            <span
              >致命/严重 <strong>{{ stats.serious_count || 0 }}</strong></span
            >
            <span
              >已解决待验证 <strong>{{ stats.resolved_pending_count || 0 }}</strong></span
            >
          </div>
        </MangoPanelSpin>
        <div class="mango-defect-page__table">
          <a-table
            class="mango-native-scroll-table"
            :data="rows"
            :columns="visibleColumns"
            :loading="loading"
            :pagination="false"
            :scroll="{ x: tableWidth, y: '100%' }"
            row-key="id"
          >
            <template #defect_no="{ record }"
              ><a-link @click="openEditor(record)">{{ record.defect_no }}</a-link></template
            >
            <template #status="{ record }">
              <a-select
                :class="['mango-defect-page__quick-select', enumToneClass('status', record.status)]"
                :model-value="record.status"
                :options="statusQuickOptions(record)"
                :loading="rowBusy.get(record.id)?.kind === 'status'"
                :disabled="isRowBusy(record.id)"
                @change="quickStatus(record, $event)"
              />
            </template>
            <template #severity="{ record }"
              ><a-select
                :class="[
                  'mango-defect-page__quick-select',
                  enumToneClass('severity', record.severity),
                ]"
                :model-value="record.severity"
                :options="enumSelectOptions(severityOptions)"
                :loading="rowBusy.get(record.id)?.kind === 'severity'"
                :disabled="isRowBusy(record.id)"
                @change="quickUpdate(record, 'severity', $event)"
            /></template>
            <template #priority="{ record }"
              ><a-select
                :class="[
                  'mango-defect-page__quick-select',
                  enumToneClass('priority', record.priority),
                ]"
                :model-value="record.priority"
                :options="enumSelectOptions(priorityOptions)"
                :loading="rowBusy.get(record.id)?.kind === 'priority'"
                :disabled="isRowBusy(record.id)"
                @change="quickUpdate(record, 'priority', $event)"
            /></template>
            <template #defect_type="{ record }"
              ><a-tag :color="enumStore.colors[record.defect_type]">{{
                enumTitle(typeOptions, record.defect_type)
              }}</a-tag></template
            >
            <template #source_type="{ record }"
              ><a-tag :color="enumStore.colors[record.source_type]">{{
                enumTitle(sourceOptions, record.source_type)
              }}</a-tag></template
            >
            <template #assignee="{ record }"
              ><a-select
                class="mango-defect-page__quick-select"
                :model-value="record.assignee?.id"
                :options="userOptions"
                :field-names="fieldNames"
                allow-search
                allow-clear
                :loading="rowBusy.get(record.id)?.kind === 'assignee'"
                :disabled="isRowBusy(record.id)"
                @change="quickUpdate(record, 'assignee', $event)"
            /></template>
            <template #reporter="{ record }">{{ record.reporter?.name || '-' }}</template>
            <template #module="{ record }">{{ formatModulePath(record.module) }}</template>
            <template #project_product="{ record }">{{
              formatProjectProductPath(record.project_product)
            }}</template>
            <template #relations="{ record }">{{
              record.relation_count ?? record.relations?.length ?? 0
            }}</template>
            <template #actions="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '编辑',
                    disabled: isRowBusy(record.id),
                    onClick: () => openEditor(record),
                  },
                  {
                    label: '流转',
                    disabled: isRowBusy(record.id) || !nextStatuses(record).length,
                    onClick: () => openTransition(record),
                  },
                  {
                    label: '创建重测计划',
                    disabled:
                      isRowBusy(record.id) || !(record.relation_count ?? record.relations?.length),
                    onClick: () => openRetest(record),
                  },
                  {
                    label: '删除',
                    danger: true,
                    loading: rowBusy.get(record.id)?.kind === 'delete',
                    disabled: isRowBusy(record.id),
                    onClick: () => removeRow(record),
                  },
                ]"
              />
            </template>
          </a-table>
        </div>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <DefectEditorDrawer
    ref="editorDrawer"
    :users="userOptions"
    :users-loading="usersLoading"
    :users-error="usersError"
    :enums-loading="enumsLoading"
    :enums-error="enumsError"
    :context-key="windowContextKey"
    @retry-users="loadUsers"
    @retry-enums="loadEnums"
    @saved="onEditorSaved"
  />

  <DefectTransitionDialog
    ref="transitionDialog"
    :users="userOptions"
    :users-loading="usersLoading"
    :users-error="usersError"
    :enums-loading="enumsLoading"
    :enums-error="enumsError"
    :context-key="windowContextKey"
    @retry-users="loadUsers"
    @retry-enums="loadEnums"
    @saved="onTransitionSaved"
  />
  <DefectRetestDialog
    ref="retestDialog"
    :users="userOptions"
    :users-loading="usersLoading"
    :users-error="usersError"
    :enums-loading="enumsLoading"
    :enums-error="enumsError"
    :context-key="windowContextKey"
    @retry-users="loadUsers"
    @retry-enums="loadEnums"
  />
</template>

<script lang="ts" setup>
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    nextTick,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { useRoute } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { usePagination } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    getFunctionalDefectStats,
    getFunctionalDefects,
    getFunctionalPlans,
  } from '@/api/functional-test'
  import useUserStore from '@/store/modules/user'
  import DefectEditorDrawer from './components/DefectEditorDrawer.vue'
  import DefectTransitionDialog from './components/DefectTransitionDialog.vue'
  import DefectRetestDialog from './components/DefectRetestDialog.vue'
  import { defectFields, defectId, defectPlanChoices, defectRouteSeed } from './form'
  import {
    DEFECT_COLUMN_STORAGE_KEY,
    defectColumnKey as columnKey,
    defectStatusTransitions,
    fixedDefectColumn,
    normalizeDefectColumns,
    restoreDefectColumns,
  } from './config'
  import type { DefectColumn } from './config'
  import {
    defectListRecord,
    defectQuery,
    defectUserOptions,
    emptyDefectFilters,
    emptyDefectStats,
    parseDefectStats,
    snapshotDefectFilters,
  } from './presentation'
  import { useDefectRowMutations } from './composables/useDefectRowMutations'
  import type {
    DefectActionSubject,
    DefectEditorHandle,
    DefectFilters,
    DefectListRecord,
    DefectMutationResult,
    DefectPlanChoice,
    DefectQuickField,
    DefectRetestHandle,
    DefectSelection,
    DefectTransitionHandle,
    DefectUserOption,
  } from './types'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const editorDrawer = ref<DefectEditorHandle | null>(null),
    transitionDialog = ref<DefectTransitionHandle | null>(null),
    retestDialog = ref<DefectRetestHandle | null>(null)
  const enumStore = useEnum(),
    windowUser = useUserStore(),
    route = useRoute()
  const windowContextKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      windowUser.userId,
      windowUser.roleId,
      windowUser.token,
      windowUser.selected_environment,
    ])
  )
  const identityKey = computed(() =>
    JSON.stringify([
      windowUser.userId,
      windowUser.roleId,
      windowUser.token,
      windowUser.selected_environment,
    ])
  )
  const rows = ref<DefectListRecord[]>([]),
    stats = ref(emptyDefectStats())
  const userOptions = ref<DefectUserOption[]>([]),
    searchPlanOptions = ref<DefectPlanChoice[]>([])
  const loading = ref(false),
    listError = ref(false),
    statsLoading = ref(false),
    statsError = ref(false)
  const usersLoading = ref(false),
    usersError = ref(false),
    enumsLoading = ref(false),
    enumsError = ref(false),
    searchPlansLoading = ref(false),
    searchPlansError = ref(false)
  const filters: DefectFilters = reactive(emptyDefectFilters())
  const appliedFilters = ref(snapshotDefectFilters(filters))
  const navigationProjectProduct = computed(() => defectId(appliedFilters.value.project_product)),
    navigationModule = computed(() => defectId(appliedFilters.value.module))
  const fieldNames = { value: 'key', label: 'title' }
  const sourceOptions = computed(() => enumStore.functional_test_defect_source ?? [])
  const typeOptions = computed(() => enumStore.functional_test_defect_type ?? [])
  const severityOptions = computed(() => enumStore.functional_test_defect_severity ?? [])
  const priorityOptions = computed(() => enumStore.functional_test_defect_priority ?? [])
  const statusOptions = computed(() => enumStore.functional_test_defect_status ?? [])
  const enumTitle = (options: Array<{ key: string | number; title: string }>, value: unknown) =>
    options.find((item) => item.key === value)?.title ?? '-'
  const enumSelectOptions = (options: Array<{ key: string | number; title: string }>) =>
    options.map((item) => ({ value: item.key, label: item.title }))
  const enumToneClass = (kind: string, value: number) => `is-${kind}-${value}`
  const configuredColumns = ref<DefectColumn[]>(restoreDefectColumns([])),
    columnStorageError = ref(false)
  const visibleColumns = computed(() =>
    configuredColumns.value.filter((item) => item.visible !== false)
  )
  const tableWidth = computed(() =>
    visibleColumns.value.reduce((total, item) => total + Number(item.width || 140), 0)
  )
  const pagination = usePagination(refreshAll, () => loading)
  const readContextKey = computed(() =>
    JSON.stringify([
      windowContextKey.value,
      defectQuery(appliedFilters.value),
      pagination.page,
      pagination.pageSize,
    ])
  )
  let active = true,
    mounted = false,
    generation = 0,
    listRequest = 0,
    statsRequest = 0,
    usersRequest = 0,
    enumsRequest = 0,
    plansRequest = 0
  let openedRoute: string | null = null
  let lastIdentity = identityKey.value
  const current = (version: number) => active && generation === version
  const scopeQuery = () =>
    Object.fromEntries(
      Object.entries({
        project_product: navigationProjectProduct.value,
        module: navigationModule.value,
      }).filter(([, value]) => value !== null)
    )
  const {
    busy: rowBusy,
    error: mutationError,
    write: writeRow,
    remove: removeMutation,
  } = useDefectRowMutations({
    context: () => readContextKey.value,
    available: (row) => !loading.value && !windowBusy(row.id),
    rows,
    saved: onTransitionSaved,
    deleted: (id) => {
      ++listRequest
      loading.value = false
      rows.value = rows.value.filter((row) => row.id !== id)
      pagination.setTotalSize(Math.max(0, pagination.pageCount - 1))
      pagination.page = Math.min(
        pagination.page,
        Math.max(1, Math.ceil(pagination.pageCount / pagination.pageSize))
      )
      void refreshAll()
    },
  })
  function windowBusy(id: number) {
    return !!(
      editorDrawer.value?.isSaving?.(id) ||
      transitionDialog.value?.isSaving?.(id) ||
      retestDialog.value?.isSaving?.(id)
    )
  }
  function isRowBusy(id: number) {
    return rowBusy.has(id) || windowBusy(id)
  }
  function invalidate() {
    ++generation
    ++listRequest
    ++statsRequest
    ++usersRequest
    ++enumsRequest
    ++plansRequest
    loading.value = false
    statsLoading.value = false
    usersLoading.value = false
    enumsLoading.value = false
    searchPlansLoading.value = false
    listError.value = false
    statsError.value = false
    usersError.value = false
    enumsError.value = false
    searchPlansError.value = false
  }
  async function loadRows() {
    if (!active) return
    const version = generation,
      request = ++listRequest,
      context = readContextKey.value
    const query = {
      ...defectQuery(appliedFilters.value),
      page: pagination.page,
      pageSize: pagination.pageSize,
    }
    const valid = () =>
      current(version) && request === listRequest && context === readContextKey.value
    loading.value = true
    listError.value = false
    try {
      const response = await getFunctionalDefects(query),
        data: unknown = response.data
      if (!valid()) return
      if (!Array.isArray(data)) throw Error('缺陷列表格式错误')
      const records = data.map(defectListRecord)
      rows.value = records
      pagination.setTotalSize(defectId(response.totalSize) ?? records.length)
    } catch (loadFailure0) {
      if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), listError.value = true)
    } finally {
      if (valid()) loading.value = false
    }
  }
  async function refreshStats() {
    if (!active) return
    const version = generation,
      request = ++statsRequest,
      query = scopeQuery(),
      scope = JSON.stringify(query)
    const valid = () =>
      current(version) && request === statsRequest && JSON.stringify(scopeQuery()) === scope
    statsLoading.value = true
    statsError.value = false
    try {
      const data: unknown = (await getFunctionalDefectStats(query)).data
      if (valid()) stats.value = parseDefectStats(data)
    } catch (loadFailure1) {
      if (valid()) (reportLoadError(loadFailure1, "加载失败，请重试", false), statsError.value = true)
    } finally {
      if (valid()) statsLoading.value = false
    }
  }
  async function refreshAll() {
    if (!active) {
      loading.value = false
      return
    }
    await Promise.all([loadRows(), refreshStats()])
  }
  async function loadUsers() {
    if (!active) return
    const version = generation,
      request = ++usersRequest
    usersLoading.value = true
    usersError.value = false
    try {
      const data: unknown = (await getUserName()).data
      if (current(version) && request === usersRequest) userOptions.value = defectUserOptions(data)
    } catch (loadFailure2) {
      if (current(version) && request === usersRequest) (reportLoadError(loadFailure2, "加载失败，请重试", false), usersError.value = true)
    } finally {
      if (current(version) && request === usersRequest) usersLoading.value = false
    }
  }
  async function loadEnums() {
    if (!active) return
    const version = generation,
      request = ++enumsRequest
    enumsLoading.value = true
    enumsError.value = false
    try {
      await enumStore.getEnum()
    } catch (loadFailure3) {
      if (current(version) && request === enumsRequest) (reportLoadError(loadFailure3, "加载失败，请重试", false), enumsError.value = true)
    } finally {
      if (current(version) && request === enumsRequest) enumsLoading.value = false
    }
  }
  async function loadSearchPlans() {
    if (!active) return
    const version = generation,
      request = ++plansRequest,
      product = navigationProjectProduct.value
    const valid = () =>
      current(version) && request === plansRequest && product === navigationProjectProduct.value
    searchPlansLoading.value = true
    searchPlansError.value = false
    try {
      const data: unknown = (
        await getFunctionalPlans({
          page: 1,
          pageSize: 500,
          ...(product === null ? {} : { project_product: product }),
        })
      ).data
      if (valid()) searchPlanOptions.value = defectPlanChoices(data)
    } catch (loadFailure4) {
      if (valid()) (reportLoadError(loadFailure4, "加载失败，请重试", false), searchPlansError.value = true)
    } finally {
      if (valid()) searchPlansLoading.value = false
    }
  }
  function search() {
    pagination.page = 1
    appliedFilters.value = snapshotDefectFilters(filters)
    return refreshAll()
  }
  function reset() {
    Object.assign(filters, emptyDefectFilters(), {
      project_product: navigationProjectProduct.value,
      module: navigationModule.value,
    })
    return search()
  }
  function onNavigationFilterChange(filter: {
    projectProduct: DefectSelection
    module: DefectSelection
  }) {
    filters.project_product = filter.projectProduct
    filters.module = filter.module
    filters.source_plan = null
    searchPlanOptions.value = []
    const refresh = search()
    void loadSearchPlans()
    return refresh
  }
  function restoreColumns() {
    try {
      const saved: unknown = JSON.parse(localStorage.getItem(DEFECT_COLUMN_STORAGE_KEY) || '[]')
      configuredColumns.value = restoreDefectColumns(saved)
      columnStorageError.value = false
    } catch {
      configuredColumns.value = restoreDefectColumns([])
      columnStorageError.value = true
    }
  }
  function saveColumns() {
    try {
      localStorage.setItem(
        DEFECT_COLUMN_STORAGE_KEY,
        JSON.stringify(
          configuredColumns.value.map((column) => ({
            key: columnKey(column),
            visible: column.visible !== false,
          }))
        )
      )
      columnStorageError.value = false
    } catch {
      columnStorageError.value = true
    }
  }
  function setColumnVisible(index: number, visible: unknown) {
    const column = configuredColumns.value[index]
    if (!column || fixedDefectColumn(column) || typeof visible !== 'boolean') return
    configuredColumns.value = configuredColumns.value.map((item, position) =>
      position === index ? { ...item, visible } : item
    )
  }
  function moveColumn(index: number, offset: number) {
    const column = configuredColumns.value[index],
      target = index + offset
    if (
      !column ||
      fixedDefectColumn(column) ||
      target < 0 ||
      target >= configuredColumns.value.length ||
      fixedDefectColumn(configuredColumns.value[target])
    )
      return
    const next = [...configuredColumns.value]
    ;[next[index], next[target]] = [next[target], next[index]]
    configuredColumns.value = normalizeDefectColumns(next)
  }
  function resetColumns() {
    configuredColumns.value = restoreDefectColumns([])
  }
  watch(configuredColumns, saveColumns)
  async function openEditor(record?: DefectListRecord) {
    if (!active || (record && (!rows.value.includes(record) || isRowBusy(record.id)))) return
    const defaults = record ? undefined : navigationCreateRef.value?.getCreateDefaults()
    await editorDrawer.value?.open(record, defaults)
  }
  async function openCurrentRoute() {
    const version = generation,
      context = windowContextKey.value
    await nextTick()
    if (!current(version) || context !== windowContextKey.value || openedRoute === context) return
    openedRoute = context
    const id = defectId(route.query.defect_id)
    if (id) {
      await editorDrawer.value?.openById(id)
      return
    }
    const seed = defectRouteSeed(route.query)
    if (seed) await editorDrawer.value?.openFromRoute(seed)
  }
  async function onEditorSaved(_result: { record: DefectMutationResult; created: boolean }) {
    if (!active) return
    await refreshAll()
  }
  function onTransitionSaved(saved: unknown) {
    if (!active) return
    const data = defectFields(saved),
      id = defectId(data.id)
    if (id === null) return
    const index = rows.value.findIndex((row) => row.id === id)
    ++listRequest
    loading.value = false
    if (index >= 0) {
      try {
        rows.value[index] = defectListRecord({ ...rows.value[index], ...data })
      } catch {
        void loadRows()
      }
    }
    void refreshStats()
  }
  const nextStatuses = (row: DefectActionSubject) => defectStatusTransitions[row.status] ?? []
  function statusQuickOptions(row: DefectListRecord) {
    const allowed = new Set([row.status, ...nextStatuses(row)])
    return enumSelectOptions(statusOptions.value).filter((item) => allowed.has(Number(item.value)))
  }
  function quickUpdate(row: DefectListRecord, field: DefectQuickField, value: unknown) {
    if (!loading.value) return writeRow(row, field, value)
  }
  function quickStatus(row: DefectListRecord, value: unknown) {
    const target = defectId(value)
    if (
      !active ||
      loading.value ||
      !rows.value.includes(row) ||
      isRowBusy(row.id) ||
      target === null ||
      !nextStatuses(row).includes(target)
    )
      return
    if ([2, 3, 4].includes(target)) transitionDialog.value?.open(row, target)
    else return writeRow(row, 'status', target)
  }
  function openTransition(row: DefectListRecord) {
    if (active && !loading.value && rows.value.includes(row) && !isRowBusy(row.id))
      transitionDialog.value?.open(row)
  }
  function openRetest(row: DefectListRecord) {
    if (active && !loading.value && rows.value.includes(row) && !isRowBusy(row.id))
      retestDialog.value?.open(row)
  }
  function removeRow(row: DefectListRecord) {
    if (!loading.value) removeMutation(row)
  }
  function startPage() {
    void loadUsers()
    void loadEnums()
    void loadSearchPlans()
    void refreshAll()
    void openCurrentRoute()
  }
  watch(
    windowContextKey,
    () => {
      invalidate()
      rows.value = []
      stats.value = emptyDefectStats()
      userOptions.value = []
      searchPlanOptions.value = []
      pagination.page = 1
      pagination.setTotalSize(0)
      openedRoute = null
      if (lastIdentity !== identityKey.value) {
        lastIdentity = identityKey.value
        Object.assign(filters, emptyDefectFilters())
        appliedFilters.value = snapshotDefectFilters(filters)
      }
      if (mounted && active) startPage()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    restoreColumns()
    startPage()
  })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    if (active) return
    active = true
    startPage()
  })
  onBeforeUnmount(() => {
    active = false
    mounted = false
    invalidate()
  })

  const autoSearch = useDebouncedSearch(search, () => filters)
</script>

<style lang="less" scoped>
  .mango-defect-page__feedback {
    display: flex;
    flex: none;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .mango-defect-page__table {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }
  .mango-defect-page__stats {
    display: flex;
    flex: none;
    align-items: center;
    gap: 24px;
    min-height: 36px;
    padding: 0 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    color: var(--m-muted);
  }
  .mango-defect-page__stats strong {
    margin-left: 4px;
    color: var(--m-text);
    font-weight: 600;
  }
  .mango-defect-page__quick-select {
    width: 100%;
  }
  .mango-defect-page__quick-select :deep(.arco-select-view) {
    border-color: transparent;
    border-radius: var(--m-radius-md);
  }
  .mango-defect-page__quick-select.is-status-3 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-status-4 :deep(.arco-select-view) {
    background: color-mix(in srgb, var(--m-success) 12%, var(--m-surface));
  }
  .mango-defect-page__quick-select.is-status-2 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-severity-1 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-priority-1 :deep(.arco-select-view) {
    background: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface));
  }
  .mango-defect-page__quick-select.is-status-5 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-severity-0 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-priority-0 :deep(.arco-select-view) {
    background: color-mix(in srgb, var(--m-danger) 12%, var(--m-surface));
  }
  .mango-defect-page__quick-select.is-status-0 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-priority-2 :deep(.arco-select-view) {
    background: var(--m-primary-soft);
  }
  .mango-defect-page__column-settings {
    display: flex;
    width: 280px;
    max-height: 420px;
    flex-direction: column;
    gap: 6px;
    overflow: auto;
  }
  .mango-defect-page__column-setting {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
</style>
