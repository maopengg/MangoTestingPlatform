<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader title="系统定时任务" @search="autoSearch.run" @reset-search="autoSearch.cancel(); onResetSearch(); autoSearch.sync()">
        <template #search-content>
          <a-form :model="conditionItems" layout="inline" @keyup.enter="autoSearch.run">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <a-input @blur="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-if="item.type === 'input'" v-model="item.value" :placeholder="item.placeholder" allow-clear @clear="autoSearch.schedule" />
              <a-select @change="autoSearch.schedule" v-else-if="item.type === 'select'" v-model="item.value" :placeholder="item.placeholder" :options="item.optionItems"
                :multiple="item.multiple" :max-tag-count="1" allow-search allow-clear @clear="autoSearch.schedule" />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>
    <template #default>
      
      <a-table :scroll="{ x: tableScrollX }" :bordered="false" :columns="tableColumns" :data="rows" :loading="listLoading" :pagination="false" :row-key="rowKey">
        <template #columns>
          <a-table-column v-for="item of tableColumns" :key="item.key" :align="item.align" :data-index="item.key" :fixed="item.fixed"
            :title="item.title" :width="item.width" :ellipsis="item.ellipsis" :tooltip="item.tooltip">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.key }}</template>
            <template v-else-if="item.key === 'source_type'" #cell="{ record }"><a-tag size="small">{{ record.source_type_name || '-' }}</a-tag></template>
            <template v-else-if="item.key === 'latest_status'" #cell="{ record }">
              <a-tag v-if="record.latest_fire" :color="statusColor(record.latest_fire.status)" size="small">{{ record.latest_fire.status_name || '-' }}</a-tag>
              <a-tag v-else color="gray" size="small">尚未触发</a-tag>
            </template>
            <template v-else-if="item.key === 'latest_planned_at'" #cell="{ record }">{{ record.latest_fire?.planned_at || '-' }}</template>
            <template v-else-if="item.key === 'latest_fired_at'" #cell="{ record }">{{ record.latest_fire?.fired_at || '-' }}</template>
            <template v-else-if="item.key === 'latest_error_message'" #cell="{ record }">{{ record.latest_fire?.error_message || '-' }}</template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions :actions="[{ label: '立即触发', loading: triggeringKeys.includes(record.key), disabled: triggeringKeys.includes(record.key), onClick: () => onTrigger(record) }]" />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>
</template>

<script lang="ts">
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { reportLoadError } from '@/utils/load-error'

  import { defineComponent, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination, useRowKey } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getSystemTaskSystemJobs, postSystemTaskSystemJobTrigger } from '@/api/system/tasks'
  import { getFormItems } from '@/utils/datacleaning'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { createConditionItems, tableColumns, tableScrollX } from './config'
  import { copySystemJob, parseSystemJobs, parseSystemJobTrigger, systemJobQuery } from './job-records'
  import type { SystemJobQuery, SystemJobRecord } from './job-records'

  export default defineComponent({
    name: 'TimingSystemJobs',
    setup() {
      const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
      const conditionItems = createConditionItems(), rows = ref<SystemJobRecord[]>([]), listLoading = ref(true), listError = ref('')
      const pagination = usePagination(doRefresh, listLoading), rowKey = useRowKey('key'), triggeringKeys = ref<string[]>([])
      const listRequests = useLatestRequest()
      let mounted = false, active = true, disposed = false, contextVersion = 0, confirmationVersion = 0, needsList = true
      let pendingList: { key: string; promise: Promise<void> } | null = null
      let confirmation: ReturnType<typeof Modal.confirm> | null = null
      const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
      const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
      function guard() {
        const version = contextVersion, key = identity()
        return () => available() && version === contextVersion && key === identity()
      }
      function buildQuery(): SystemJobQuery { return systemJobQuery(getFormItems(conditionItems)) }
      function onSearch() { pagination.page = 1; return doRefresh() }
      function resetConditions() { for (const item of conditionItems) { if (item.reset) item.reset(); else item.value = item.multiple ? [] : '' } }
      function onResetSearch() { resetConditions(); return onSearch() }
      function doRefresh(): Promise<void> {
        if (!available()) { needsList = true; listLoading.value = false; return Promise.resolve() }
        let query: SystemJobQuery
        try { query = { ...buildQuery(), page: pagination.page, pageSize: pagination.pageSize } }
        catch (loadFailure0) { listRequests.invalidateRequests(); pendingList = null; listLoading.value = false; (reportLoadError(loadFailure0, "加载失败，请重试", false), listError.value = '搜索条件格式异常，请检查后重试'); return Promise.resolve() }
        const signature = JSON.stringify([identity(), query])
        if (pendingList?.key === signature) return pendingList.promise
        const request = listRequests.beginRequest(), current = guard(), valid = () => current() && listRequests.isLatestRequest(request)
        needsList = false; listLoading.value = true; listError.value = ''
        const promise = Promise.resolve().then(async () => {
          try {
            if (!valid()) return
            const response = await getSystemTaskSystemJobs(query)
            if (!valid()) return
            const result = parseSystemJobs(response)
            pagination.setTotalSize(result.total)
            const lastPage = Math.max(1, Math.ceil(result.total / pagination.pageSize))
            if (pagination.page > lastPage) { pagination.page = lastPage; await doRefresh(); return }
            rows.value = result.rows
          } catch (loadFailure1) { if (valid()) { (reportLoadError(loadFailure1, "系统定时任务加载失败，请重试", false), listError.value = '系统定时任务加载失败，请重试'); needsList = true } }
          finally { if (valid()) { listLoading.value = false; pendingList = null } }
        })
        pendingList = { key: signature, promise }; return promise
      }
      function statusColor(status: number | null) {
        if (status === 3) return 'green'
        if (status === 4) return 'red'
        if (status === 1 || status === 2) return 'blue'
        if (status === 5 || status === 6) return 'gray'
        return 'orange'
      }
      function closeConfirmation() { confirmationVersion++; confirmation?.close(); confirmation = null }
      function onTrigger(record: SystemJobRecord) {
        if (!available() || triggeringKeys.value.includes(record.key)) return
        const target = copySystemJob(record), current = guard(), key = identity()
        closeConfirmation()
        const version = confirmationVersion, valid = () => current() && version === confirmationVersion
        confirmation = Modal.confirm({
          title: '确认触发系统定时任务', content: `确认立即触发系统定时任务「${target.name || target.key}」吗？该操作会立即执行一次并写入触发记录。`,
          okText: '确认触发', cancelText: '取消',
          onCancel: () => { if (version === confirmationVersion) closeConfirmation() },
          onBeforeOk: async () => {
            if (!valid() || triggeringKeys.value.includes(target.key)) return false
            triggeringKeys.value = [...triggeringKeys.value, target.key]
            let refreshAttempted = false
            try {
              const response = await postSystemTaskSystemJobTrigger(target.key), result = parseSystemJobTrigger(response)
              if (key === identity()) needsList = true
              if (!valid()) return false
              closeConfirmation(); Message.success(result.message)
              refreshAttempted = true; await doRefresh(); return true
            } catch { if (valid()) Message.error('触发失败，请重试'); return false }
            finally {
              triggeringKeys.value = triggeringKeys.value.filter(item => item !== target.key)
              if (!refreshAttempted || !current()) resume()
            }
          },
        })
      }
      function pause() {
        contextVersion++; listRequests.invalidateRequests(); pendingList = null
        listLoading.value = false; needsList = true; closeConfirmation()
      }
      function resume() { if (available() && needsList) void doRefresh() }
      function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
      watch(identity, () => {
        pause(); rows.value = []; resetConditions(); pagination.page = 1; pagination.setTotalSize(0); listError.value = ''; resume()
      }, { flush: 'sync' })
      onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
      onActivated(() => { active = true; resume() })
      onDeactivated(() => { active = false; pause() })
      onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
      const autoSearch = useDebouncedSearch(onSearch, () => conditionItems.map(item => [item.key, item.value]))
      return { autoSearch, tableColumns, tableScrollX, conditionItems, rows, listLoading, listError, pagination, rowKey, triggeringKeys,
        buildQuery, onSearch, onResetSearch, doRefresh, statusColor, onTrigger }
    },
  })
</script>
