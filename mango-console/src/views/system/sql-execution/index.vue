<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="数据源执行记录"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #header-extra>
          <a-button size="small" @click="contentSearch?.open()">执行内容检索</a-button>
        </template>
        <template #search-content>
          <a-form :model="conditionItems" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item in conditionItems" :key="item.key" :label="item.label">
              <a-input
                v-if="item.type === 'input'"
                v-model="item.value"
                :placeholder="item.placeholder"
                @blur="onSearch"
              />
              <a-select
                v-else-if="item.type === 'select'"
                v-model="item.value"
                :field-names="fieldNames"
                :options="selectOptions(String(item.key))"
                :loading="optionsLoading"
                :multiple="item.multiple"
                :max-tag-count="1"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                value-key="key"
                @change="onSearch"
              />
              <a-range-picker
                v-else-if="item.type === 'range'"
                v-model="item.value"
                show-time
                value-format="YYYY-MM-DD HH:mm:ss"
                @change="onSearch"
              />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      
      
      <a-table
        :scroll="{ x: tableScrollX }"
        :bordered="false"
        :columns="tableColumns"
        :data="rows"
        :loading="listLoading"
        :pagination="false"
        :row-key="rowKey"
      >
        <template #columns>
          <a-table-column
            v-for="item in tableColumns"
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
            <template v-else-if="item.key === 'datasource_type_name'" #cell="{ record }">
              <a-tag :color="record.datasource_type === null ? 'gray' : optionTagColor('datasource_type', record.datasource_type)" size="small">{{ record.datasource_type_name }}</a-tag>
            </template>
            <template v-else-if="item.key === 'project_product_name' || item.key === 'datasource_alias_name'" #cell="{ record }">
              {{ record[item.key] || '不适用' }}
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag :color="optionTagColor('test_env', record.test_env)" size="small">
                {{ record.test_env_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'source_type'" #cell="{ record }">
              <a-tag :color="optionTagColor('source_type', record.source_type)" size="small">
                {{ optionTitle('source_type', record.source_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'source_stage'" #cell="{ record }">
              <a-tag :color="optionTagColor('source_stage', record.source_stage)" size="small">{{ optionTitle('source_stage', record.source_stage) }}</a-tag>
            </template>
            <template v-else-if="item.key === 'case_id' || item.key === 'operation'" #cell="{ record }">
              {{ auditSourceValue(record, String(item.key)) }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColor(record.status)" size="small">
                {{ statusText(record.status) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'duration_ms'" #cell="{ record }">
              {{ formatDuration(record.duration_ms) }}
            </template>
            <template v-else-if="item.key === 'is_slow'" #cell="{ record }">
              <a-tag :color="record.is_slow ? 'orange' : 'green'" size="small">
                {{ record.is_slow ? '慢执行' : '正常' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'operations'" #cell="{ record }">
              <MangoTableActions
                :actions="[{ key: 'detail', label: '详情', onClick: () => openDetail(record) }]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <BaseSidePanel v-model:visible="detailVisible" title="数据源执行详情" width="720px" @cancel="closeDetail">
    <a-descriptions v-if="selectedRecord" :column="2" bordered size="small">
      <a-descriptions-item label="记录ID">{{ selectedRecord.id }}</a-descriptions-item>
      <a-descriptions-item label="请求ID">{{ selectedRecord.request_id }}</a-descriptions-item>
      <a-descriptions-item label="Case ID">{{ auditSourceValue(selectedRecord, 'case_id') }}</a-descriptions-item>
      <a-descriptions-item label="操作类型">{{ auditSourceValue(selectedRecord, 'operation') }}</a-descriptions-item>
      <a-descriptions-item label="数据源类型">{{ selectedRecord.datasource_type_name }}</a-descriptions-item>
      <a-descriptions-item label="来源">
        {{ optionTitle('source_type', selectedRecord.source_type) }} #{{ selectedRecord.source_id ?? '-' }}
      </a-descriptions-item>
      <a-descriptions-item label="阶段">{{ optionTitle('source_stage', selectedRecord.source_stage) }}</a-descriptions-item>
      <a-descriptions-item label="项目产品">
        {{ selectedRecord.project_product_name || '不适用' }}
      </a-descriptions-item>
      <a-descriptions-item label="被测环境">{{ selectedRecord.test_env_name }}</a-descriptions-item>
      <a-descriptions-item label="逻辑数据源">
        {{ selectedRecord.datasource_alias_name || '不适用' }}
      </a-descriptions-item>
      <a-descriptions-item label="实际数据库">
        {{ selectedRecord.database_name || '-' }}
      </a-descriptions-item>
      <a-descriptions-item label="状态">{{ statusText(selectedRecord.status) }}</a-descriptions-item>
      <a-descriptions-item label="耗时">
        {{ formatDuration(selectedRecord.duration_ms) }}
      </a-descriptions-item>
    </a-descriptions>

    <div v-if="selectedRecord" class="mango-sql-execution-detail">
      <section>
        <h4>来源说明</h4>
        <JsonDisplay :data="selectedRecord.source_detail ?? {}" :default-expanded="false" />
      </section>
      <section>
        <h4>执行内容</h4>
        <pre class="mango-code-panel">{{ selectedRecord.sql_text || '-' }}</pre>
      </section>
      <section>
        <h4>执行参数</h4>
        <JsonDisplay :data="selectedRecord.sql_parameters ?? {}" :default-expanded="false" />
      </section>
      <section>
        <h4>结果预览</h4>
        <pre class="mango-code-panel">{{ selectedRecord.result_preview || '-' }}</pre>
        <div v-if="selectedRecord.result_truncated" class="mango-sql-execution-tip">
          内容已截断，仅保留前 1000 个字符。
        </div>
      </section>
      <section v-if="selectedRecord.error_message">
        <h4>错误信息</h4>
        <pre class="mango-code-panel">{{ selectedRecord.error_message }}</pre>
      </section>
    </div>
  </BaseSidePanel>
  <ExecutionContentSearchDrawer ref="contentSearch" kind="datasource" :on-open="openSearchHit" />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { onMounted, onActivated, onDeactivated, onBeforeUnmount, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { usePagination, useRowKey } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getFormItems } from '@/utils/datacleaning'
  import { getSqlExecutionList, getSqlExecutionOptions } from '@/api/system/sql_execution'
  import type { SqlExecutionQuery } from '@/api/system/sql_execution'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ExecutionContentSearchDrawer from '@/components/reports/ExecutionContentSearchDrawer.vue'
  import type { ContentSearchHit } from '@/api/system/execution_content_search'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { getEnumTagColor } from '@/utils/business-format'
  import { createConditionItems, tableColumns, tableScrollX, SQL_EXECUTION_OPTION_KEYS, SQL_STATUS_TITLES, SQL_STATUS_COLORS } from './config'
  import { auditSourceValue, emptyAuditOptions, parseAuditOptions, parseExecutionList, copyExecutionRecord, executionQuery } from './execution-records'
  import type { AuditOptions, SqlExecutionRecord } from './execution-records'

  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const enumStore = useEnum()
  const conditionItems = createConditionItems()
  const rows = ref<SqlExecutionRecord[]>([])
  const listLoading = ref(true), optionsLoading = ref(false)
  const listError = ref(''), optionsError = ref('')
  const options = ref<AuditOptions>(emptyAuditOptions())
  const detailVisible = ref(false), selectedRecord = ref<SqlExecutionRecord | null>(null)
  const contentSearch = ref<InstanceType<typeof ExecutionContentSearchDrawer> | null>(null)
  async function openSearchHit(hit: ContentSearchHit) {
    const context = identity()
    const response = await getSqlExecutionList({ id: hit.record_id, page: 1, pageSize: 1 })
    if (context !== identity()) return
    const parsed = parseExecutionList(response)
    const record = parsed.rows.find(row => String(row.id) === String(hit.record_id))
    if (record) openDetail(record)
    else Message.warning('执行记录已删除或不可访问')
  }
  const rowKey = useRowKey('id')
  const pagination = usePagination(doRefresh, listLoading)
  const listRequests = useLatestRequest(), optionRequests = useLatestRequest()
  let active = true, mounted = false, disposed = false, contextVersion = 0
  let needsList = true, needsOptions = true
  let pendingList: { key: string; promise: Promise<void> } | null = null
  let pendingOptions: Promise<void> | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const currentContext = () => {
    const version = contextVersion, key = identity()
    return () => available() && version === contextVersion && key === identity()
  }

  function selectOptions(key: string) {
    const optionKey = SQL_EXECUTION_OPTION_KEYS[key as keyof typeof SQL_EXECUTION_OPTION_KEYS]
    return optionKey ? options.value[optionKey] : []
  }
  function optionTitle(key: string, value: string | number | null) {
    return selectOptions(key).find(item => String(item.key) === String(value))?.title ?? value ?? '-'
  }
  function optionTagColor(key: string, value: string | number | null) {
    return getEnumTagColor(selectOptions(key).map(item => ({ key: String(item.key), title: item.title })), value, enumStore.colors)
  }
  const buildQuery = () => executionQuery(getFormItems(conditionItems))

  function doRefresh(): Promise<void> {
    if (!available()) { needsList = true; listLoading.value = false; return Promise.resolve() }
    let query: SqlExecutionQuery
    try { query = { ...buildQuery(), page: pagination.page, pageSize: pagination.pageSize } }
    catch (loadFailure0) {
      listRequests.invalidateRequests(); pendingList = null
      void (reportLoadError(loadFailure0, "加载失败，请重试", false), listError.value = '搜索条件格式异常，请检查后重试'); listLoading.value = false
      return Promise.resolve()
    }
    const signature = JSON.stringify([identity(), query])
    if (pendingList?.key === signature) return pendingList.promise
    const request = listRequests.beginRequest(), current = currentContext()
    const valid = () => current() && listRequests.isLatestRequest(request)
    listLoading.value = true; listError.value = ''; needsList = false
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const response = await getSqlExecutionList(query)
        if (!valid()) return
        const result = parseExecutionList(response)
        pagination.setTotalSize(result.total)
        const lastPage = Math.max(1, Math.ceil(result.total / pagination.pageSize))
        if (pagination.page > lastPage) {
          pagination.page = lastPage
          await doRefresh()
          return
        }
        rows.value = result.rows
      } catch (loadFailure1) {
        if (valid()) { (reportLoadError(loadFailure1, "执行记录加载失败，请重试", false), listError.value = '执行记录加载失败，请重试'); needsList = true }
      } finally {
        if (valid()) { listLoading.value = false; pendingList = null }
      }
    })
    pendingList = { key: signature, promise }
    return promise
  }
  function onSearch() { pagination.page = 1; return doRefresh() }
  function resetConditions() {
    for (const item of conditionItems) {
      if (item.reset) item.reset()
      else item.value = item.type === 'range' || item.multiple ? [] : ''
    }
  }
  function onResetSearch() { resetConditions(); return onSearch() }

  function loadOptions(): Promise<void> {
    if (!available()) { needsOptions = true; return Promise.resolve() }
    if (pendingOptions) return pendingOptions
    const request = optionRequests.beginRequest(), current = currentContext()
    const valid = () => current() && optionRequests.isLatestRequest(request)
    optionsLoading.value = true; optionsError.value = ''; needsOptions = false
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const [lookup, enums] = await Promise.allSettled([getSqlExecutionOptions(), enumStore.getEnum()])
        if (!valid()) return
        if (lookup.status === 'rejected') throw lookup.reason
        options.value = parseAuditOptions(lookup.value)
        if (enums.status === 'rejected') { (reportLoadError(undefined, "枚举信息加载失败，可重试选项", false), optionsError.value = '枚举信息加载失败，可重试选项'); needsOptions = true }
      } catch (loadFailure2) {
        if (valid()) { (reportLoadError(loadFailure2, "筛选选项加载失败，请重试", false), optionsError.value = '筛选选项加载失败，请重试'); needsOptions = true }
      } finally {
        if (valid()) { optionsLoading.value = false; pendingOptions = null }
      }
    })
    pendingOptions = promise
    return promise
  }
  function openDetail(record: SqlExecutionRecord) {
    if (!available()) return
    try { selectedRecord.value = copyExecutionRecord(record); detailVisible.value = true }
    catch { Message.error('执行记录格式异常，请重新加载列表') }
  }
  function closeDetail() { detailVisible.value = false; selectedRecord.value = null }
  watch(detailVisible, visible => { if (!visible) selectedRecord.value = null })
  function statusText(status: string) { return SQL_STATUS_TITLES[status] || status || '-' }
  function statusColor(status: string) { return SQL_STATUS_COLORS[status] || 'gray' }
  function formatDuration(value: number | string | null) {
    return value === null ? '-' : `${Number(value).toFixed(2)} ms`
  }

  function pause() {
    contextVersion++; listRequests.invalidateRequests(); optionRequests.invalidateRequests()
    pendingList = null; pendingOptions = null
    listLoading.value = false; optionsLoading.value = false
    needsList = true; needsOptions = true; closeDetail()
  }
  function resume() {
    if (!available()) return
    if (needsList) void doRefresh()
    if (needsOptions) void loadOptions()
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identity, () => {
    pause(); rows.value = []; options.value = emptyAuditOptions(); resetConditions()
    pagination.page = 1; pagination.setTotalSize(0); listError.value = ''; optionsError.value = ''
    resume()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-sql-execution-detail {
    display: grid;
    gap: var(--m-page-gap);
    margin-top: var(--m-page-gap);
  }

  .mango-sql-execution-detail section h4 {
    margin: 0 0 6px;
    color: var(--m-text-2);
    font-size: 14px;
    font-weight: 600;
  }

  .mango-sql-execution-error {
    margin-bottom: var(--m-page-gap);
    color: var(--m-danger);
  }

  .mango-sql-execution-detail .mango-code-panel {
    max-height: 260px;
    margin: 0;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-sql-execution-tip {
    margin-top: 4px;
    color: var(--m-warning);
  }
</style>
