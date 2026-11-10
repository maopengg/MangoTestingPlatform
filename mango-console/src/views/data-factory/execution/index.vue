<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="数据工厂 / 执行记录" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        :model-value="getSearchItemValue('project_product')"
        :module-value="getSearchItemValue('module')"
        :reset-key="sidebarResetKey"
        show-modules
        @filter-change="onNavigationFilterChange"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearch"
                  @clear="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'stage'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_execution_stage"
                  :placeholder="item.placeholder"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_execution_status"
                  :placeholder="item.placeholder"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'cleanup_status'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_cleanup_status"
                  :placeholder="item.placeholder"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <span class="mango-execution-selection-summary"
              >已选 {{ selectedRowKeys.length }} 条</span
            >
            <a-button
              size="small"
              type="primary"
              status="danger"
              :disabled="selectedRowKeys.length === 0 || cleanupIds.size > 0"
              :loading="batchCleanupLoading"
              @click="batchCleanup"
            >
              批量清理
            </a-button>
          </a-space>
        </template>
        
        
        <a-table
          class="mango-native-scroll-table"
          :columns="visibleTableColumns"
          :data="rows"
          :loading="listLoading"
          :pagination="false"
          :row-key="'id'"
          :row-selection="rowSelection"
          :scroll="{ x: executionScrollX, y: '100%' }"
          @selection-change="onSelectionChange"
        >
          <template #columns>
            <a-table-column
              v-for="item of visibleTableColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :fixed="item.fixed"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
              :title="item.title"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'source_display'" #cell="{ record }">
                <div class="mango-execution-source-cell">
                  <a-tooltip :content="record.source_display || '-'" position="top" mini>
                    <span class="mango-execution-source-cell__title">{{
                      record.source_display || '-'
                    }}</span>
                  </a-tooltip>
                  <span class="mango-execution-source-cell__meta" :title="formatSourceMeta(record.source_info)">
                    {{ formatSourceMeta(record.source_info) }}
                  </span>
                </div>
              </template>
              <template v-else-if="item.key === 'stage'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.stage]" size="small">
                  {{ enumTitle(enumStore.data_factory_execution_stage, record.stage) }}</a-tag
                >
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-tag :color="enumStore.status_colors[record.status]" size="small">
                  {{ enumTitle(enumStore.data_factory_execution_status, record.status) }}</a-tag
                >
              </template>
              <template v-else-if="item.key === 'cleanup_status'" #cell="{ record }">
                <a-tag :color="cleanupStatusColor(record.cleanup_status)" size="small">{{
                  enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status)
                }}</a-tag>
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'module'" #cell="{ record }">
                {{ formatModulePath(record.module) }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions :actions="executionActions(record)" />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <ExecutionDetailDrawer ref="detailRef" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, ref, reactive, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    getDataFactoryExecution,
    postDataFactoryExecutionCleanup,
    postDataFactoryExecutionBatchCleanup,
  } from '@/api/data-factory'
  import { usePagination } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getFormItems } from '@/utils/datacleaning'
  import { formatProjectProductPath, formatModulePath, getOptionId } from '@/utils/business-format'
  import { DATA_FACTORY_CLEANUP_STATUS_COLORS, getStatusTagColor } from '@/utils/status-color'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ExecutionDetailDrawer from './components/ExecutionDetailDrawer.vue'
  import {
    createConditionItems,
    executionTableColumns,
    executionScrollX,
    enumFieldNames,
  } from './config'
  import { canCleanup, enumTitle, formatSourceMeta } from './display'
  import { useExecutionScope } from './composables/useExecutionScope'
  import type { ExecutionRecord, DetailHandle, CleanupResponse } from './types'
  const route = useRoute(),
    enumStore = useEnum(),
    executionConditionItems = createConditionItems()
  const sidebarResetKey = ref(0),
    headerConditionItems = computed(() =>
      executionConditionItems.filter(
        (item) => !['project_product', 'module'].includes(String(item.key))
      )
    ),
    visibleTableColumns = executionTableColumns
  const rows = ref<ExecutionRecord[]>([]),
    listLoading = ref(false),
    loadError = ref(false),
    enumsLoading = ref(false),
    enumsError = ref(false)
  const pagination = usePagination(doRefresh, listLoading),
    selectedRowKeys = ref<number[]>([]),
    cleanupIds = reactive(new Set<number>()),
    batchCleanupLoading = ref(false),
    detailRef = ref<DetailHandle | null>(null)
  const cleanupStatusColor = (value: number) =>
    getStatusTagColor(DATA_FACTORY_CLEANUP_STATUS_COLORS, value)
  const rowSelection = computed(() => ({
    selectedRowKeys: selectedRowKeys.value,
    showCheckedAll: true,
    getCheckboxProps: (record: ExecutionRecord) => ({
      disabled: listLoading.value || !canCleanup(record) || cleanupIds.has(record.id),
    }),
  }))
  let listRequest = 0,
    enumsRequest = 0,
    context = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useExecutionScope(reset, resume)
  function getSearchItem(key: string) {
    return executionConditionItems.find((item) => item.key === key)
  }
  function getSearchItemValue(key: string) {
    const value: unknown = getOptionId(getSearchItem(key)?.value)
    return typeof value === 'number' || (typeof value === 'string' && value !== '') ? value : null
  }
  function closeContext() {
    ++context
    confirmation?.close()
    confirmation = null
    detailRef.value?.close()
  }
  function reset() {
    ++listRequest
    ++enumsRequest
    closeContext()
    rows.value = []
    pagination.setTotalSize(0)
    selectedRowKeys.value = []
    listLoading.value = false
    loadError.value = false
    enumsLoading.value = false
    enumsError.value = false
  }
  function resume() {
    void doRefresh()
    void loadEnums()
  }
  async function loadEnums() {
    if (!scope.isActive()) return
    const request = ++enumsRequest,
      version = scope.snapshot()
    enumsLoading.value = true
    enumsError.value = false
    try {
      await enumStore.getEnum()
    } catch (loadFailure0) {
      if (request === enumsRequest && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), enumsError.value = true)
    } finally {
      if (request === enumsRequest) enumsLoading.value = false
    }
  }
  function onSelectionChange(keys: Array<number | string>) {
    if (listLoading.value) return
    selectedRowKeys.value = rows.value
      .filter(
        (record) =>
          keys.some((key) => String(key) === String(record.id)) &&
          canCleanup(record) &&
          !cleanupIds.has(record.id)
      )
      .map((record) => record.id)
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const request = ++listRequest,
      version = scope.snapshot(),
      query = getFormItems(executionConditionItems)
    query.project_product = getSearchItemValue('project_product')
    query.module = getSearchItemValue('module')
    Object.keys(query).forEach((key) => {
      if (query[key] === '' || query[key] === null || query[key] === undefined) delete query[key]
    })
    Object.assign(query, { page: pagination.page, pageSize: pagination.pageSize })
    selectedRowKeys.value = []
    listLoading.value = true
    loadError.value = false
    try {
      const response = await getDataFactoryExecution(query)
      if (request === listRequest && scope.current(version)) {
        rows.value = response.data || []
        pagination.setTotalSize(response.totalSize ?? 0)
      }
    } catch (loadFailure1) {
      if (request === listRequest && scope.current(version)) (reportLoadError(loadFailure1, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (request === listRequest) listLoading.value = false
    }
  }
  function onSearch() {
    closeContext()
    pagination.page = 1
    return doRefresh()
  }
  function onNavigationFilterChange({
    projectProduct,
    module,
  }: {
    projectProduct: string | number | null
    module: string | number | null
  }) {
    const product = getSearchItem('project_product'),
      item = getSearchItem('module')
    if (product) product.value = projectProduct ?? ''
    if (item) item.value = module ?? ''
    return onSearch()
  }
  function onResetSearch() {
    executionConditionItems.forEach((item) => {
      item.value = item.multiple ? [] : ''
    })
    sidebarResetKey.value++
    return onSearch()
  }
  function applyRoute() {
    const value = route.query.execution_no,
      item = getSearchItem('execution_no')
    if (item) item.value = typeof value === 'string' ? value : ''
  }
  watch(
    () => route.query.execution_no,
    () => {
      applyRoute()
      void onSearch()
    },
    { flush: 'sync' }
  )
  function openDetail(record: ExecutionRecord) {
    if (scope.isActive()) detailRef.value?.open(record)
  }
  function executionActions(record: ExecutionRecord) {
    const actions = [{ label: '详情', onClick: () => openDetail(record) }]
    return canCleanup(record)
      ? [
          ...actions,
          {
            label: Number(record.cleanup_status) === 2 ? '重试清理' : '清理',
            danger: true,
            loading: cleanupIds.has(record.id),
            disabled: batchCleanupLoading.value,
            onClick: () => cleanup(record),
          },
        ]
      : actions
  }
  function cleanup(record: ExecutionRecord) {
    if (
      !scope.isActive() ||
      confirmation ||
      batchCleanupLoading.value ||
      cleanupIds.has(record.id) ||
      !canCleanup(record)
    )
      return
    const id = record.id,
      no = record.execution_no,
      current = context,
      version = scope.snapshot()
    const dialog = Modal.confirm({
      title: Number(record.cleanup_status) === 2 ? '重试清理执行数据' : '清理执行数据',
      content: `确认按全部执行明细清理 ${no} 创建的数据？已不存在的数据会按成功处理。`,
      okText: '清理',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (
          current !== context ||
          !scope.current(version) ||
          cleanupIds.has(id) ||
          batchCleanupLoading.value
        )
          return false
        cleanupIds.add(id)
        try {
          const response = await postDataFactoryExecutionCleanup({ execution_id: id })
          if (current !== context || !scope.current(version)) return true
          const result: CleanupResponse = response.data || {}
          detailRef.value?.refreshFor(id)
          await doRefresh()
          if (current !== context || !scope.current(version)) return true
          if ((result.fail || 0) > 0) {
            Message.error(result.message || '清理失败，请检查执行明细')
            return false
          }
          Message.success(result.message || response.msg)
          return true
        } catch {
          return false
        } finally {
          cleanupIds.delete(id)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  function batchCleanup() {
    if (!scope.isActive() || confirmation || batchCleanupLoading.value || cleanupIds.size) return
    const ids = [...selectedRowKeys.value]
    if (!ids.length) {
      Message.warning('请先选择需要清理的执行记录')
      return
    }
    const current = context,
      version = scope.snapshot()
    const dialog = Modal.confirm({
      title: '批量清理执行数据',
      content: `确认清理已选择的 ${ids.length} 条执行记录？已不存在的数据会按成功处理。`,
      okText: '清理',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (
          current !== context ||
          !scope.current(version) ||
          batchCleanupLoading.value ||
          cleanupIds.size
        )
          return false
        batchCleanupLoading.value = true
        ids.forEach((id) => cleanupIds.add(id))
        try {
          const response = await postDataFactoryExecutionBatchCleanup({ execution_ids: ids })
          if (current !== context || !scope.current(version)) return true
          const result: CleanupResponse = response.data || {}
          ids.forEach((id) => detailRef.value?.refreshFor(id))
          await doRefresh()
          if (current !== context || !scope.current(version)) return true
          if ((result.fail || 0) > 0) {
            Message.warning(response.msg)
            return false
          }
          Message.success(response.msg)
          return true
        } catch {
          return false
        } finally {
          batchCleanupLoading.value = false
          ids.forEach((id) => cleanupIds.delete(id))
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  onMounted(() => {
    applyRoute()
    resume()
  })
</script>
<style scoped>
  .mango-execution-source-cell {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }
  .mango-execution-selection-summary {
    color: var(--m-muted);
    font-size: 12px;
    white-space: nowrap;
  }
  .mango-execution-source-cell__title,
  .mango-execution-source-cell__meta {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-execution-source-cell__meta {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
</style>
