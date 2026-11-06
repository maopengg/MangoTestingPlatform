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
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="doRefresh"
                  @clear="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchProjectChange(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleSelect
                  v-model="item.value"
                  :project-product-id="getSearchItemValue('project_product')"
                  :placeholder="item.placeholder"
                  :auto-clear="false"
                  @change="doRefresh"
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
                  @change="doRefresh"
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
                  @change="doRefresh"
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
                  @change="doRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <span class="execution-selection-summary">已选 {{ selectedRowKeys.length }} 条</span>
            <a-button
              size="small"
              type="primary"
              status="danger"
              :disabled="selectedRowKeys.length === 0"
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
          :data="table.dataList"
          :loading="table.tableLoading.value"
          :pagination="false"
          :row-key="'id'"
          :row-selection="rowSelection"
          :scroll="{ x: 1590, y: '100%' }"
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
                <div class="execution-source-cell">
                  <a-tooltip :content="record.source_display || '-'" position="top" mini>
                    <span class="execution-source-cell__title">{{
                      record.source_display || '-'
                    }}</span>
                  </a-tooltip>
                  <span class="execution-source-cell__meta">
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

  <a-drawer v-model:visible="detailVisible" title="执行详情" width="860px">
    <a-tabs>
      <a-tab-pane
        key="source"
        title="来源"
        data-testid="qa-views-data-factory-execution-tab-pane-来源"
      >
        <div class="execution-source-detail">
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">来源类型</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.source_type_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">执行人</span>
            <span class="execution-source-detail__value">
              {{
                formatUserName(
                  detail.execution?.source_info?.executor_name,
                  detail.execution?.source_info?.executor_username
                )
              }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">用例责任人</span>
            <span class="execution-source-detail__value">
              {{
                formatUserName(
                  detail.execution?.source_info?.case_owner_name,
                  detail.execution?.source_info?.case_owner_username
                )
              }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">触发用例</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.case_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">所属模块名称</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.ui_module_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">接口</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.api_info_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item execution-source-detail__item--wide">
            <span class="execution-source-detail__label">接口地址</span>
            <span class="execution-source-detail__value">
              {{ formatApiInfo(detail.execution?.source_info) }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">接口场景</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.scenario_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">场景模板</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.template_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">来源ID</span>
            <span class="execution-source-detail__value">
              {{ formatSourceId(detail.execution?.source_info) }}
            </span>
          </div>
        </div>
      </a-tab-pane>
      <a-tab-pane
        key="context"
        title="上下文"
        data-testid="qa-views-data-factory-execution-tab-pane-上下文"
      >
        <JsonDisplay :data="detail.context || {}" />
      </a-tab-pane>
      <a-tab-pane
        key="items"
        title="创建明细"
        data-testid="qa-views-data-factory-execution-tab-pane-创建明细"
      >
        <a-table
          :columns="executionItemColumns"
          :data="detail.items || []"
          :loading="detailLoading"
          :pagination="false"
          :scroll="{ x: 1650 }"
        >
          <template #columns>
            <a-table-column
              v-for="item of executionItemColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
              :title="item.title"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'cleanup_status'" #cell="{ record }">
                {{ enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status) }}
              </template>
              <template v-else-if="item.key === 'storage_snapshot'" #cell="{ record }">
                {{ formatStorageSnapshot(record.storage_snapshot) }}
              </template>
              <template v-else-if="item.key === 'sql_executions'" #cell="{ record }">
                <div v-if="record.sql_executions?.length" class="execution-sql-audit-list">
                  <div
                    v-for="sqlRecord in record.sql_executions"
                    :key="sqlRecord.id"
                    class="execution-sql-audit-item"
                  >
                    <a-tag size="small" :color="sqlExecutionStatusColor(sqlRecord.status)">
                      {{ sqlExecutionStageName(sqlRecord.source_stage) }}
                    </a-tag>
                    <a-tooltip :content="sqlRecord.sql_text" position="top" mini>
                      <span class="execution-detail-cell-text">{{ sqlRecord.sql_text }}</span>
                    </a-tooltip>
                    <span class="execution-sql-audit-duration">
                      {{
                        sqlRecord.duration_ms === null
                          ? '历史记录'
                          : `${Number(sqlRecord.duration_ms || 0).toFixed(2)}ms`
                      }}
                    </span>
                    <a-tag v-if="sqlRecord.is_slow" size="small" color="orangered">慢执行</a-tag>
                    <a-tooltip content="复制执行内容" position="top" mini>
                      <a-button
                        class="execution-detail-copy-button"
                        type="text"
                        size="mini"
                        @click="copyCellValue(sqlRecord.sql_text, 'SQL')"
                      >
                        <template #icon><icon-copy /></template>
                      </a-button>
                    </a-tooltip>
                  </div>
                </div>
                <span v-else>-</span>
              </template>
              <template v-else-if="item.key === 'data'" #cell="{ record }">
                <div class="execution-detail-cell-line">
                  <a-tooltip :content="stringifyCellValue(record.data)" position="top" mini>
                    <span class="execution-detail-cell-text">
                      {{ stringifyCellValue(record.data) }}
                    </span>
                  </a-tooltip>
                  <a-tooltip content="复制创建数据" position="top" mini>
                    <a-button
                      class="execution-detail-copy-button"
                      type="text"
                      size="mini"
                      @click="copyCellValue(record.data, '创建数据')"
                    >
                      <template #icon>
                        <icon-copy />
                      </template>
                    </a-button>
                  </a-tooltip>
                </div>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane
        key="sql"
        title="数据源执行记录"
        data-testid="qa-views-data-factory-execution-tab-pane-SQL记录"
      >
        <a-table
          :data="detail.sql_executions || []"
          :loading="detailLoading"
          :pagination="false"
          :scroll="{ x: 1180 }"
        >
          <template #columns>
            <a-table-column title="阶段" :width="130">
              <template #cell="{ record }">
                {{ sqlExecutionStageName(record.source_stage) }}
              </template>
            </a-table-column>
            <a-table-column title="状态" :width="110">
              <template #cell="{ record }">
                <a-tag size="small" :color="sqlExecutionStatusColor(record.status)">
                  {{ sqlExecutionStatusName(record.status) }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="执行内容" :width="420">
              <template #cell="{ record }">
                <div class="execution-detail-cell-line">
                  <a-tooltip :content="record.sql_text" position="top" mini>
                    <span class="execution-detail-cell-text">{{ record.sql_text }}</span>
                  </a-tooltip>
                  <a-button
                    class="execution-detail-copy-button"
                    type="text"
                    size="mini"
                    @click="copyCellValue(record.sql_text, 'SQL')"
                  >
                    <template #icon><icon-copy /></template>
                  </a-button>
                </div>
              </template>
            </a-table-column>
            <a-table-column title="耗时" :width="110">
              <template #cell="{ record }">
                {{ Number(record.duration_ms || 0).toFixed(2) }}ms
                <a-tag v-if="record.is_slow" size="small" color="orangered">慢</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="影响行数" data-index="affected_rows" :width="100" />
            <a-table-column title="错误/结果" :width="310">
              <template #cell="{ record }">
                <a-tooltip
                  :content="record.error_message || record.result_preview || '-'"
                  position="top"
                  mini
                >
                  <span class="execution-detail-cell-text">
                    {{ record.error_message || record.result_preview || '-' }}
                  </span>
                </a-tooltip>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane
        key="error"
        title="错误"
        data-testid="qa-views-data-factory-execution-tab-pane-错误"
      >
        <a-alert v-if="detail.execution?.error_message" type="error">{{
          detail.execution.error_message
        }}</a-alert>
        <div v-else class="mango-empty-state execution-empty">暂无错误</div>
      </a-tab-pane>
      <a-tab-pane key="resources" title="关联资源清理">
        <a-table
          :columns="cleanupResourceColumns"
          row-key="key"
          :data="cleanupResourceRows"
          :loading="detailLoading"
          :pagination="false"
          :scroll="{ x: 1340 }"
        />
      </a-tab-pane>
    </a-tabs>
  </a-drawer>
</template>

<script lang="ts" setup>
  import {
    getDataFactoryExecution,
    getDataFactoryExecutionDetail,
    postDataFactoryExecutionBatchCleanup,
    postDataFactoryExecutionCleanup,
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getFormItems } from '@/utils/datacleaning'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { formatProjectProductPath, formatModulePath, getItemValue } from '@/utils/business-format'
  import { DATA_FACTORY_CLEANUP_STATUS_COLORS, getStatusTagColor } from '@/utils/status-color'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { executionConditionItems, executionItemColumns, executionTableColumns, cleanupResourceColumns } from './config'

  const table = useTable()
  const sidebarResetKey = ref(0)
  const headerConditionItems = computed(() =>
    executionConditionItems.filter((item) => !['project_product', 'module'].includes(item.key))
  )
  const visibleTableColumns = executionTableColumns
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const enumStore = useEnum()
  const cleanupStatusColor = (value: number) =>
    getStatusTagColor(DATA_FACTORY_CLEANUP_STATUS_COLORS, value)
  const enumFieldNames = { value: 'key', label: 'title' }
  const detailVisible = ref(false)
  const detail = ref<any>({})
  const cleanupResourceRows = computed(() => (detail.value.items || []).flatMap((item: any) => {
    const state = item.cleanup_resources || {}
    return (state.snapshots || []).map((snapshot: any, snapshotIndex: number) => {
      const result = (state.results || []).find((entry: any) => entry.snapshot_index != null ? entry.snapshot_index === snapshotIndex : entry.index === snapshot.index && entry.document_id === snapshot.document_id)
      return {
        key: `${item.id}:${snapshot.rule.datasource_alias_id}:${snapshot.index}:${snapshot.document_id}`,
        alias: item.alias,
        index: snapshot.index,
        document_id: snapshot.document_id,
        sql_status: state.sql_cleaned ? '已清理' : '未清理',
        status: !result ? '待检查' : result.success ? '已确认消失' : '失败',
        checked_at: result?.checked_at || '-',
        error: result?.error || (!result ? '数据库清理后将回查ES' : '-'),
      }
    })
  }))
  const detailLoading = ref(false)
  const actionLoading = ref('')
  const batchCleanupLoading = ref(false)
  const selectedRowKeys = ref<Array<number | string>>([])
  const route = useRoute()

  const CLEANABLE_STATUSES = new Set([0, 2, 4])
  const ACTIVE_EXECUTION_STATUSES = new Set([2, 3])
  type ExecutionAction = {
    label: string
    danger?: boolean
    loading?: boolean
    onClick: () => void
  }
  const canCleanup = (record: any) =>
    CLEANABLE_STATUSES.has(Number(record.cleanup_status)) &&
    !ACTIVE_EXECUTION_STATUSES.has(Number(record.status))
  const rowSelection = computed(() => ({
    selectedRowKeys: selectedRowKeys.value,
    showCheckedAll: true,
    getCheckboxProps: (record: any) => ({ disabled: !canCleanup(record) }),
  }))

  function onSelectionChange(keys: Array<number | string>) {
    selectedRowKeys.value = keys
  }

  function executionActions(record: any) {
    const actions: ExecutionAction[] = [
      {
        label: '详情',
        loading: actionLoading.value === `detail-${record.id}`,
        onClick: () => openDetail(record),
      },
    ]
    if (canCleanup(record)) {
      actions.push({

        label: record.cleanup_status === 2 ? '重试清理' : '清理',
        danger: true,
        loading: actionLoading.value === `cleanup-${record.id}`,
        onClick: () => cleanup(record),
      })
    }
    return actions
  }

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function getOptionId(value: any) {
    return value?.id ?? value
  }

  function stringifyCellValue(value: any) {
    if (typeof value === 'string') return value
    if (typeof value === 'undefined' || value === null) return '-'
    return JSON.stringify(value)
  }

  function formatSourceMeta(sourceInfo: any) {
    if (!sourceInfo) return '-'
    const parts = [
      sourceInfo.executor_name ? `执行人 ${sourceInfo.executor_name}` : '',
      !sourceInfo.executor_name && sourceInfo.case_owner_name
        ? `责任人 ${sourceInfo.case_owner_name}`
        : '',
      sourceInfo.case_id ? `用例ID ${sourceInfo.case_id}` : '',
      sourceInfo.scenario_id ? `场景ID ${sourceInfo.scenario_id}` : '',
      sourceInfo.template_id ? `模板ID ${sourceInfo.template_id}` : '',
    ].filter(Boolean)
    return parts.join(' / ') || formatSourceId(sourceInfo)
  }

  function formatSourceId(sourceInfo: any) {
    if (!sourceInfo) return '-'
    const parts = [
      sourceInfo.source_id ? `来源 ${sourceInfo.source_id}` : '',
      sourceInfo.template_id ? `模板 ${sourceInfo.template_id}` : '',
    ].filter(Boolean)
    return parts.join(' / ') || '-'
  }

  function formatUserName(name?: string, username?: string) {
    if (name && username) return `${name}（${username}）`
    return name || username || '-'
  }

  function formatApiInfo(sourceInfo: any) {
    if (!sourceInfo?.api_info_url) return '-'
    const method = sourceInfo.api_info_method_name ? `${sourceInfo.api_info_method_name} ` : ''
    return `${method}${sourceInfo.api_info_url}`
  }

  function formatStorageSnapshot(snapshot: any) {
    if (!snapshot) return '-'
    const database =
      snapshot.database_name || (snapshot.database_id ? `数据库 ${snapshot.database_id}` : '')
    const table = snapshot.table_name || ''
    const primaryKey = snapshot.primary_key ? `主键 ${snapshot.primary_key}` : ''
    return [database, table, primaryKey].filter(Boolean).join(' / ') || '-'
  }

  const sqlExecutionStageNames: Record<string, string> = {
    create: '创建',
    post_insert_update: '插入后回写',
    cleanup: '清理',
    residual_check: '残留校验',
  }

  function sqlExecutionStageName(stage: string) {
    return sqlExecutionStageNames[stage] || enumTitle(enumStore.datasource_audit_stage, stage) || stage || '-'
  }

  function sqlExecutionStatusColor(status: string) {
    if (status === 'success') return 'green'
    if (status === 'running') return 'blue'
    if (status === 'rolled_back') return 'orange'
    return 'red'
  }

  function sqlExecutionStatusName(status: string) {
    const names: Record<string, string> = {
      running: '执行中',
      success: '成功',
      fail: '失败',
      timeout: '超时',
      rolled_back: '已回滚',
    }
    return names[status] || status || '-'
  }

  function fallbackCopy(text: string) {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', 'readonly')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)
    textarea.select()
    textarea.setSelectionRange(0, textarea.value.length)
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }

  async function copyCellValue(value: any, label: string) {
    const text = stringifyCellValue(value)
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      } else if (!fallbackCopy(text)) {
        throw new Error('copy failed')
      }
      Message.success(`复制${label}成功`)
    } catch {
      Message.error(`复制${label}失败`)
    }
  }

  function getSearchItem(key: string) {
    return executionConditionItems.find((item) => item.key === key)
  }

  function getSearchItemValue(key: string) {
    return getItemValue(executionConditionItems, key)
  }

  function onSearchProjectChange(value: any) {
    const moduleItem = getSearchItem('module')
    if (moduleItem) {
      moduleItem.value = ''
    }
    doRefresh()
  }

  function onNavigationFilterChange({
    projectProduct,
    module,
  }: {
    projectProduct: any
    module: any
  }) {
    const projectItem = getSearchItem('project_product')
    const moduleItem = getSearchItem('module')
    if (projectItem) projectItem.value = projectProduct ?? ''
    if (moduleItem) moduleItem.value = module ?? ''
    pagination.page = 1
    doRefresh()
  }

  function doRefresh() {
    selectedRowKeys.value = []
    table.tableLoading.value = true
    const query = getFormItems(executionConditionItems)
    getDataFactoryExecution({
      ...query,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }).then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
  }

  function onResetSearch() {
    executionConditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    doRefresh()
  }

  function openDetail(record: any) {
    actionLoading.value = `detail-${record.id}`
    detailLoading.value = true
    getDataFactoryExecutionDetail({ execution_id: record.id })
      .then((res) => {
        detail.value = res.data || {}
        detailVisible.value = true
      })
      .finally(() => {
        actionLoading.value = ''
        detailLoading.value = false
      })
  }

  function cleanup(record: any) {
    Modal.confirm({
      title: record.cleanup_status === 2 ? '重试清理执行数据' : '清理执行数据',
      content: `确认按全部执行明细清理 ${record.execution_no} 创建的数据？已不存在的数据会按成功处理。`,
      onBeforeOk: () => {
        actionLoading.value = `cleanup-${record.id}`
        return postDataFactoryExecutionCleanup({ execution_id: record.id })
          .then((res) => {
            if (res.data?.fail > 0) {
              Message.error(res.data.message || '清理失败，请检查执行明细')
              doRefresh()
              return false
            }
            Message.success(res.data?.message || res.msg)
            doRefresh()
            return true
          })
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  function batchCleanup() {
    if (selectedRowKeys.value.length === 0) {
      Message.warning('请先选择需要清理的执行记录')
      return
    }
    const executionIds = [...selectedRowKeys.value]
    Modal.confirm({
      title: '批量清理执行数据',
      content: `确认清理已选择的 ${executionIds.length} 条执行记录？已不存在的数据会按成功处理。`,
      onBeforeOk: () => {
        batchCleanupLoading.value = true
        return postDataFactoryExecutionBatchCleanup({ execution_ids: executionIds })
          .then((res) => {
            const result = res.data || {}
            if (result.fail > 0) {
              Message.warning(res.msg)
            } else {
              Message.success(res.msg)
            }
            selectedRowKeys.value = []
            doRefresh()
          })
          .finally(() => {
            batchCleanupLoading.value = false
          })
      },
    })
  }

  onMounted(() => {
    const executionNo = route.query.execution_no
    if (executionNo) {
      const item = getSearchItem('execution_no')
      if (item) item.value = String(executionNo)
    }
    enumStore.getEnum()
    doRefresh()
  })
</script>
<style scoped>
  .execution-source-cell {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .execution-selection-summary {
    color: var(--m-muted);
    font-size: 12px;
    white-space: nowrap;
  }

  .execution-source-cell__title {
    overflow: hidden;
    color: var(--m-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-source-cell__meta {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-source-detail {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
  }

  .execution-source-detail__item {
    min-width: 0;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-bg);
  }

  .execution-source-detail__item--wide {
    grid-column: 1 / -1;
  }

  .execution-source-detail__label {
    display: block;
    margin-bottom: 4px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .execution-source-detail__value {
    display: block;
    min-height: 22px;
    overflow: hidden;
    color: var(--m-text);
    line-height: 22px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-empty {
    min-height: 120px;
  }

  .execution-detail-cell-line {
    display: flex;
    min-width: 0;
    align-items: flex-start;
    gap: 4px;
  }

  .execution-detail-cell-text {
    display: -webkit-box;
    flex: 1;
    min-width: 0;
    max-height: 40px;
    overflow: hidden;
    color: var(--m-text);
    font-size: 12px;
    line-height: 20px;
    word-break: break-all;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .execution-detail-copy-button {
    flex: none;
    width: 22px;
    height: 22px;
    padding: 0;
  }

  .execution-sql-audit-list {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }

  .execution-sql-audit-item {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
  }

  .execution-sql-audit-duration {
    flex: none;
    color: var(--m-muted);
    font-size: 12px;
    white-space: nowrap;
  }
</style>
