<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader :show-filter="true" title="操作日志" @search="onSearch" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="conditionItems" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <a-input v-if="item.type === 'input'" v-model="item.value" :placeholder="item.placeholder" @blur="onSearch" />
              <a-select v-else-if="item.type === 'select'" v-model="item.value" :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined" :field-names="fieldNames" :options="selectOptions(item.key)"
                :loading="item.key === 'user' ? userOptionsLoading : item.key === 'source_type' ? sourceOptionsLoading : false"
                :placeholder="item.placeholder" allow-clear allow-search @change="onSearch" />
            </a-form-item>
          </a-form>
          
          
        </template>
      </TableHeader>
    </template>
    <template #default>
      
      <a-table :scroll="{ x: tableScrollX }" :bordered="false" :data="rows" :loading="listLoading" :pagination="false" :row-key="rowKey">
        <template #columns>
          <a-table-column v-for="item of tableColumns" :key="item.key" :align="item.align" :data-index="item.key"
            :ellipsis="item.ellipsis" :fixed="item.fixed" :title="item.title" :tooltip="item.tooltip" :width="item.width">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'user'" #cell="{ record }">{{ record.user?.name || record.user?.username || '-' }}</template>
            <template v-else-if="item.key === 'source_type'" #cell="{ record }">
              <a-tag :color="sourceTypeColor(record.source_type)" size="small">{{ sourceTypeText(record.source_type) }}</a-tag>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { usePagination, useRowKey } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { createConditionItems, requestMethodOptions, tableColumns, tableScrollX } from './config'
  import { getUserName } from '@/api/user/user'
  import { getUserLogs } from '@/api/user/user-logs'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { getEnumTagColor } from '@/utils/business-format'
  import { parseLogOptions, parseUserLogOptions, parseUserLogs, userLogQuery } from './log-records'
  import type { LogOption, UserLogQuery, UserLogRecord } from './log-records'

  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path, enumStore = useEnum()
  const conditionItems = createConditionItems(), rows = ref<UserLogRecord[]>([]), listLoading = ref(true), listError = ref('')
  const userOptions = ref<LogOption[]>([]), sourceOptions = ref<LogOption[]>([])
  const userOptionsLoading = ref(false), sourceOptionsLoading = ref(false), userOptionsError = ref(''), sourceOptionsError = ref('')
  const pagination = usePagination(doRefresh, listLoading), rowKey = useRowKey('id')
  const listRequests = useLatestRequest(), userRequests = useLatestRequest(), sourceRequests = useLatestRequest()
  let mounted = false, active = true, disposed = false, contextVersion = 0
  let needsList = true, needsUsers = true, needsSources = true
  let pendingList: { key: string; promise: Promise<void> } | null = null
  let pendingUsers: Promise<void> | null = null, pendingSources: Promise<void> | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  function guard() {
    const version = contextVersion, key = identity()
    return () => available() && version === contextVersion && key === identity()
  }
  function selectOptions(key: string): LogOption[] {
    if (key === 'user') return userOptions.value
    if (key === 'source_type') return sourceOptions.value
    return key === 'method' ? requestMethodOptions : []
  }
  function sourceTypeText(source: string | null): string {
    if (source === 'MCP') return 'MCP'
    return sourceOptions.value.find(item => String(item.key) === String(source))?.title ?? (source || '-')
  }
  function sourceTypeColor(source: string | null): string {
    if (source === 'MCP') return 'purple'
    return getEnumTagColor(sourceOptions.value, source, enumStore.colors)
  }
  function buildQuery(): UserLogQuery { return userLogQuery(getFormItems(conditionItems)) }
  function doRefresh(): Promise<void> {
    if (!available()) { needsList = true; listLoading.value = false; return Promise.resolve() }
    let query: UserLogQuery
    try { query = { ...buildQuery(), page: pagination.page, pageSize: pagination.pageSize } }
    catch (loadFailure0) { listRequests.invalidateRequests(); pendingList = null; listLoading.value = false; (reportLoadError(loadFailure0, "加载失败，请重试", false), listError.value = '搜索条件格式异常，请检查后重试'); return Promise.resolve() }
    const signature = JSON.stringify([identity(), query])
    if (pendingList?.key === signature) return pendingList.promise
    const request = listRequests.beginRequest(), current = guard(), valid = () => current() && listRequests.isLatestRequest(request)
    needsList = false; listLoading.value = true; listError.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const response = await getUserLogs(query)
        if (!valid()) return
        const result = parseUserLogs(response)
        pagination.setTotalSize(result.total)
        const lastPage = Math.max(1, Math.ceil(result.total / pagination.pageSize))
        if (pagination.page > lastPage) { pagination.page = lastPage; await doRefresh(); return }
        rows.value = result.rows
      } catch (loadFailure1) { if (valid()) { (reportLoadError(loadFailure1, "操作日志加载失败，请重试", false), listError.value = '操作日志加载失败，请重试'); needsList = true } }
      finally { if (valid()) { listLoading.value = false; pendingList = null } }
    })
    pendingList = { key: signature, promise }; return promise
  }
  function onSearch() { pagination.page = 1; return doRefresh() }
  function resetConditions() { for (const item of conditionItems) { if (item.reset) item.reset(); else item.value = item.multiple ? [] : '' } }
  function onResetSearch() { resetConditions(); return onSearch() }
  function loadUserOptions(): Promise<void> {
    if (!available()) { needsUsers = true; return Promise.resolve() }
    if (pendingUsers) return pendingUsers
    const request = userRequests.beginRequest(), current = guard(), valid = () => current() && userRequests.isLatestRequest(request)
    needsUsers = false; userOptionsLoading.value = true; userOptionsError.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const response = await getUserName()
        if (valid()) userOptions.value = parseUserLogOptions(response)
      } catch (loadFailure2) { if (valid()) { (reportLoadError(loadFailure2, "用户选项加载失败，请重试", false), userOptionsError.value = '用户选项加载失败，请重试'); needsUsers = true } }
      finally { if (valid()) { userOptionsLoading.value = false; pendingUsers = null } }
    })
    pendingUsers = promise; return promise
  }
  function loadSourceOptions(): Promise<void> {
    if (!available()) { needsSources = true; return Promise.resolve() }
    if (pendingSources) return pendingSources
    const request = sourceRequests.beginRequest(), current = guard(), valid = () => current() && sourceRequests.isLatestRequest(request)
    needsSources = false; sourceOptionsLoading.value = true; sourceOptionsError.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        await enumStore.getEnum()
        if (valid()) sourceOptions.value = parseLogOptions(enumStore.cline_type)
      } catch (loadFailure3) { if (valid()) { (reportLoadError(loadFailure3, "来源选项加载失败，请重试", false), sourceOptionsError.value = '来源选项加载失败，请重试'); needsSources = true } }
      finally { if (valid()) { sourceOptionsLoading.value = false; pendingSources = null } }
    })
    pendingSources = promise; return promise
  }
  function pause() {
    contextVersion++; listRequests.invalidateRequests(); userRequests.invalidateRequests(); sourceRequests.invalidateRequests()
    pendingList = null; pendingUsers = null; pendingSources = null
    listLoading.value = false; userOptionsLoading.value = false; sourceOptionsLoading.value = false
    needsList = true; needsUsers = true; needsSources = true
  }
  function resume() {
    if (!available()) return
    if (needsList) void doRefresh()
    if (needsUsers) void loadUserOptions()
    if (needsSources) void loadSourceOptions()
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identity, () => {
    pause(); rows.value = []; userOptions.value = []; sourceOptions.value = []; resetConditions()
    pagination.page = 1; pagination.setTotalSize(0); listError.value = ''; userOptionsError.value = ''; sourceOptionsError.value = ''
    resume()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-user-logs-error { color: var(--m-danger); margin-top: var(--m-page-gap); }
</style>
