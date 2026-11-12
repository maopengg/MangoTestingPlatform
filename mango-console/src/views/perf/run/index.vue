<template>
  <TableBody plain class="mango-detail-workbench-page mango-perf-page">
    <template #header>
      <TableHeader title="性能测试 / 运行历史" @search="autoSearch.run" @reset-search="autoSearch.cancel(); resetSearch(); autoSearch.sync()">
        <template #search-content>
          <a-form :model="filters" layout="inline" @submit.prevent="autoSearch.run">
            <a-form-item label="名称"><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="filters.name" placeholder="请输入运行名称" allow-clear @press-enter="autoSearch.run" /></a-form-item>
            <a-form-item label="状态"><a-select @change="autoSearch.schedule" v-model="filters.status" placeholder="请选择状态" multiple :max-tag-count="1" :options="statusOptions" allow-clear /></a-form-item>
            <a-form-item label="结论"><a-select @change="autoSearch.schedule" v-model="filters.verdict" placeholder="请选择结论" multiple :max-tag-count="1" :options="verdictOptions" allow-clear /></a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <a-table :columns="runColumns" :data="rows" :loading="loading" :pagination="false" :scroll="{ x: runScrollX }" row-key="id">
        <template #columns><a-table-column v-for="column in runColumns" :key="column.key" v-bind="column">
          <template v-if="column.key === 'index'" #cell="{ record }"><a-link @click="open(record)">{{ record.id }}</a-link></template>
          <template v-else-if="column.key === 'project_product'" #cell="{ record }"><span :title="record.project_product.name">{{ record.project_product.name || '-' }}</span></template>
          <template v-else-if="column.key === 'module'" #cell="{ record }"><span :title="record.module_full_path">{{ record.module_full_path || '-' }}</span></template>
          <template v-else-if="column.key === 'status'" #cell="{ record }"><a-tag :color="runStatusColor(record.status)" size="small">{{ runStatusTitle[record.status] || record.status }}</a-tag></template>
          <template v-else-if="column.key === 'verdict'" #cell="{ record }"><a-tag :color="runVerdictColor(record.verdict)" size="small">{{ verdictTitle[record.verdict] || record.verdict }}</a-tag></template>
          <template v-else-if="column.key === 'peak_target_users'" #cell="{ record }">{{ record.peak_target_users ?? '-' }}</template>
          <template v-else-if="column.key === 'nodes'" #cell="{ record }">{{ record.actual_node_count ?? '-' }}/{{ record.requested_node_count ?? '-' }}</template>
          <template v-else-if="column.key === 'actions'" #cell="{ record }"><MangoTableActions :actions="[{ label: '查看', onClick: () => open(record) }, { label: '停止', danger: true, hidden: !activeRunStatuses.has(record.status), loading: stoppingIds.has(record.id), onClick: () => stop(record) }]" /></template>
        </a-table-column></template>
        <template #empty><div class="mango-empty-state">暂无运行记录</div></template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>
</template>

<script setup lang="ts">
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { reportLoadError, runLoadRequest } from '@/utils/load-error'

  import { Message } from '@arco-design/web-vue'
  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { usePagePolling, type PollingContext } from '@/hooks/use-page-polling'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { usePagination } from '@/hooks/table'
  import { getPerfRuns, stopPerfRun } from '@/api/perf'
  import { activeRunStatuses, runStatusColor, runStatusTitle, runVerdictColor, verdictTitle } from '../types'
  import { runColumns, runScrollX, statusOptions, verdictOptions } from './config'
  import { assertRunHistorySuccess, copyRunHistoryFilters, createRunHistoryFilters, readRunHistory, runHistoryQuery } from './records'
  import type { RunHistoryRecord } from './types'

  const route = useRoute(), router = useRouter(), user = useUserStore()
  const rows = ref<RunHistoryRecord[]>([])
  const loading = ref(false), failed = ref(false)
  const stoppingIds = reactive(new Set<number>())
  const filters = reactive(createRunHistoryFilters())
  const appliedFilters = ref(createRunHistoryFilters())
  const pagination = usePagination(() => load(), () => loading)
  let active = true, mounted = false, disposed = false, needsInitialLoad = true, readVersion = 0, viewVersion = 0
  let pending: { isCurrent: () => boolean; promise: Promise<boolean> } | null = null
  const available = () => !disposed && active && route.path === '/perf/run/index' && document.visibilityState === 'visible'
  const pagePolling = usePagePolling(context => load(true, context))

  function invalidateRead() { readVersion++; pending = null; loading.value = false }
  function load(silent = false, context?: PollingContext): Promise<boolean> {
    if (context && !context.isCurrent()) return Promise.resolve(false)
    if (!available()) { loading.value = false; return Promise.resolve(false) }
    if (pending?.isCurrent()) { if (!silent) loading.value = true; return pending.promise }
    const snapshot = readVersion
    const query = runHistoryQuery(appliedFilters.value, pagination.page, pagination.pageSize)
    const isCurrent = () => available() && snapshot === readVersion && (!context || context.isCurrent())
    const job = { isCurrent, promise: Promise.resolve(false) }
    pending = job
    if (!silent) { loading.value = true; pagePolling.start() }
    job.promise = Promise.resolve().then(async () => {
      try {
        if (!isCurrent()) return false
        const response = await runLoadRequest(silent, () => getPerfRuns(query))
        if (!isCurrent()) return false
        const result = readRunHistory(response)
        const lastPage = Math.max(1, Math.ceil(result.total / pagination.pageSize))
        if (pagination.page > lastPage) { pagination.page = lastPage; return load(silent, context) }
        rows.value = result.rows
        pagination.setTotalSize(result.total)
        failed.value = false
        if (result.rows.some(row => activeRunStatuses.has(row.status))) pagePolling.start()
        else pagePolling.stop()
        return true
      } catch (loadFailure0) {
        if (isCurrent()) (reportLoadError(loadFailure0, '运行历史加载失败，请重试', silent), failed.value = true)
        return false
      } finally {
        if (pending === job) { pending = null; loading.value = false }
      }
    })
    return job.promise
  }
  function search() {
    pagination.page = 1
    const next = copyRunHistoryFilters(filters)
    if (JSON.stringify(next) !== JSON.stringify(appliedFilters.value)) appliedFilters.value = next
    return load()
  }
  function resetSearch() { Object.assign(filters, createRunHistoryFilters()); return search() }
  function open(record: RunHistoryRecord) {
    if (available() && rows.value.some(row => row.id === record.id)) router.push({ path: '/perf/run/details', query: { id: record.id } })
  }
  async function stop(record: RunHistoryRecord) {
    if (!available() || stoppingIds.has(record.id) || !rows.value.some(row => row.id === record.id && activeRunStatuses.has(row.status))) return
    const id = record.id, view = viewVersion, query = readVersion
    const isCurrent = () => available() && view === viewVersion && query === readVersion
    stoppingIds.add(id)
    try {
      assertRunHistorySuccess(await stopPerfRun(id))
      if (!isCurrent()) return
      Message.success('停止请求已提交')
      pagePolling.start()
      await load(true)
    } catch {
      if (isCurrent()) Message.error('停止请求失败，请重试')
    } finally { stoppingIds.delete(id) }
  }
  function suspend(clear: boolean) {
    viewVersion++
    invalidateRead()
    pagePolling.pause(); pagePolling.stop()
    if (clear) { rows.value = []; pagination.setTotalSize(0); failed.value = false; needsInitialLoad = true }
  }
  function resume(silent: boolean) {
    if (!available()) return
    pagePolling.start(); pagePolling.resume()
    const quiet = silent && !needsInitialLoad
    needsInitialLoad = false
    void load(quiet)
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(true); else suspend(false) }
  watch(() => [pagination.page, pagination.pageSize, appliedFilters.value], invalidateRead, { flush: 'sync' })
  watch(() => [user.userId, user.roleId, user.token, user.selected_environment], () => {
    suspend(true)
    pagination.page = 1
    if (mounted) resume(false)
  }, { flush: 'sync' })
  watch(() => [route.path, route.fullPath], () => { suspend(true); if (mounted) resume(false) }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume(false) })
  onDeactivated(() => { active = false; suspend(false) })
  onActivated(() => { if (!active) { active = true; resume(true) } })
  onBeforeUnmount(() => { disposed = true; active = false; suspend(true); document.removeEventListener('visibilitychange', visibilityChanged) })

  const autoSearch = useDebouncedSearch(search, () => filters)
</script>
