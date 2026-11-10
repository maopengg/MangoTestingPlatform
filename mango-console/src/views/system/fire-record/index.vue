<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="触发记录"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearch"
                  @clear="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  @change="onSearch"
                />
              </template>
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
        :rowKey="rowKey"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'time_task'" #cell="{ record }">
              {{ record.time_task_label || record.time_task?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'source_type'" #cell="{ record }">
              <a-tag :color="sourceTypeColor(record.source_type)" size="small">
                {{ record.source_type_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColor(record.status)" size="small">
                {{ record.status_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '报告', disabled: record.test_suite === null || reportOpening,
                    loading: reportOpening && openingReportId === record.test_suite, onClick: () => openReport(record) },
]"
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
</template>

<script lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { defineComponent, onMounted, onBeforeUnmount, onActivated, onDeactivated, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { usePagination, useRowKey } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { useRoute, useRouter } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { getSystemTaskFireRecord } from '@/api/system/tasks'
  import { createConditionItems, fireSourceTypeOptions, tableColumns, tableScrollX } from './config'
  import { buildFireRecordQuery, resetFireRecordConditions, parseFireRecords, fireReportId } from './fire-record'
  import type { FireRecordId, FireRecordRow } from './fire-record'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'

  export default defineComponent({
    name: 'TimingFireRecord',
    setup() {
      const route = useRoute(), router = useRouter(), pagePath = route.path
      const user = useUserStore(), permission = usePermissionStore(), enumStore = useEnum()
      const conditionItems = createConditionItems(), rows = ref<FireRecordRow[]>([])
      const listLoading = ref(false), listError = ref(''), enumLoading = ref(false), enumError = ref('')
      const rowKey = useRowKey('id'), pagination = usePagination(doRefresh, listLoading)
      const listRequests = useLatestRequest(), enumRequests = useLatestRequest()
      const reportOpening = ref(false), openingReportId = ref<FireRecordId | null>(null)
      let mounted = false, active = true, disposed = false, needsLoad = true, epoch = 0
      let pending: { key: string; promise: Promise<void> } | null = null
      const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
      const identity = () => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
      const context = () => JSON.stringify([identity(), epoch])
      function buildQuery() { return buildFireRecordQuery(conditionItems) }
      function listContext() { return JSON.stringify([context(), buildQuery(), pagination.page, pagination.pageSize]) }
      function doRefresh(): Promise<void> {
        if (!available()) { needsLoad = true; listLoading.value = false; return Promise.resolve() }
        const key = listContext()
        if (pending?.key === key) return pending.promise
        const request = listRequests.beginRequest(), query = { ...buildQuery(), page: pagination.page, pageSize: pagination.pageSize }
        const current = () => available() && listRequests.isLatestRequest(request) && key === listContext()
        listLoading.value = true; listError.value = ''; needsLoad = false
        const promise = Promise.resolve().then(async () => {
          try {
            if (!current()) return
            const result = parseFireRecords(await getSystemTaskFireRecord(query))
            if (current()) { rows.value = result.rows; pagination.setTotalSize(result.total) }
          } catch (loadFailure0) { if (current()) { rows.value = []; pagination.setTotalSize(0); (reportLoadError(loadFailure0, "触发记录加载失败，请重试", false), listError.value = '触发记录加载失败，请重试') } }
          finally { if (listRequests.isLatestRequest(request)) { listLoading.value = false; pending = null } }
        })
        pending = { key, promise }
        return promise
      }
      function onSearch() { pagination.page = 1; return doRefresh() }
      function onResetSearch() { resetFireRecordConditions(conditionItems); return onSearch() }
      async function loadEnums() {
        if (!available() || enumLoading.value) return
        const request = enumRequests.beginRequest(), key = context()
        const current = () => available() && enumRequests.isLatestRequest(request) && key === context()
        enumLoading.value = true; enumError.value = ''
        try { await enumStore.getEnum() }
        catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, "触发类型颜色加载失败，请重试", false), enumError.value = '触发类型颜色加载失败，请重试') }
        finally { if (enumRequests.isLatestRequest(request)) enumLoading.value = false }
      }
      function statusColor(status: number | null) {
        if (status === 3) return 'green'
        if (status === 4) return 'red'
        if (status === 1 || status === 2) return 'blue'
        if (status === 5 || status === 6) return 'gray'
        return 'orange'
      }
      function sourceTypeColor(sourceType: number | null) {
        return getEnumTagColor(fireSourceTypeOptions.map(item => ({ key: item.value, title: item.label })), sourceType, enumStore.colors)
      }
      async function openReport(record: FireRecordRow) {
        if (!available() || reportOpening.value) return
        const id = fireReportId(record.test_suite)
        if (id === null) return
        const key = context()
        reportOpening.value = true; openingReportId.value = id
        try {
          const failure = await router.push({ path: '/report/system/details', query: { id } })
          if (failure && available() && key === context()) Message.error('报告打开失败，请重试')
        }
        catch { if (available() && key === context()) Message.error('报告打开失败，请重试') }
        finally { reportOpening.value = false; openingReportId.value = null }
      }
      function pause() {
        epoch++; needsLoad = true; pending = null
        listRequests.invalidateRequests(); enumRequests.invalidateRequests()
        listLoading.value = false; enumLoading.value = false
      }
      function resume() {
        if (!available() || !needsLoad) return
        needsLoad = false; void doRefresh(); void loadEnums()
      }
      function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
      watch(identity, () => { pause(); rows.value = []; pagination.setTotalSize(0); pagination.page = 1; resume() }, { flush: 'sync' })
      onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
      onActivated(() => { active = true; resume() })
      onDeactivated(() => { active = false; pause() })
      onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
      return { conditionItems, tableColumns, tableScrollX, rows, listLoading, listError, enumLoading, enumError,
        pagination, rowKey, doRefresh, onSearch, onResetSearch, loadEnums, statusColor, sourceTypeColor,
        reportOpening, openingReportId, openReport, buildQuery }
    },
  })
</script>

<style scoped>
  .mango-fire-record-feedback {
    padding: var(--m-page-gap);
    color: var(--m-muted);
  }
  .mango-fire-record-feedback--error {
    color: var(--m-danger);
  }
</style>
