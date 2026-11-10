
import { reportLoadError } from '@/utils/load-error'
import { ref } from 'vue'
import { getSystemTasks, getSystemTaskRecentResults } from '@/api/system/tasks'
import { readTaskList, readTaskRecentResults, type TaskListQuery, type TaskListRecord, type TaskListRecentResult } from '../task-list-records'

interface Pagination { page: number; pageSize: number; setTotalSize: (total: number) => void }
export function useTaskList(context: { available: () => boolean; capture: () => () => boolean; query: () => TaskListQuery; pagination: Pagination }) {
  const rows = ref<TaskListRecord[]>([]), loading = ref(false), error = ref('')
  const recentResults = ref<Record<string, TaskListRecentResult[]>>({}), recentLoading = ref(false), recentError = ref('')
  let listVersion = 0, recentVersion = 0
  function invalidate(clear = false) {
    listVersion++; recentVersion++; loading.value = false; recentLoading.value = false
    if (clear) { rows.value = []; recentResults.value = {}; error.value = ''; recentError.value = ''; context.pagination.setTotalSize(0) }
  }
  async function loadRecentResults(): Promise<boolean> {
    if (!context.available()) return false
    const version = ++recentVersion, list = listVersion, valid = context.capture(), ids = rows.value.map(row => row.id)
    const queryKey = JSON.stringify(context.query())
    const current = () => context.available() && valid() && version === recentVersion && list === listVersion && queryKey === JSON.stringify(context.query())
    recentError.value = ''; recentLoading.value = ids.length > 0
    if (!ids.length) { recentResults.value = {}; return true }
    try {
      const results = readTaskRecentResults(await getSystemTaskRecentResults(ids), ids)
      if (!current()) return false
      recentResults.value = results
      return true
    } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "最近执行结果加载失败，请重试", false), recentError.value = '最近执行结果加载失败，请重试'); return false }
    finally { if (version === recentVersion) recentLoading.value = false }
  }
  async function load(): Promise<boolean> {
    if (!context.available()) { loading.value = false; return false }
    const version = ++listVersion, valid = context.capture(), query = context.query(), queryKey = JSON.stringify(query)
    const current = () => context.available() && valid() && version === listVersion && queryKey === JSON.stringify(context.query())
    recentVersion++; recentLoading.value = false; recentError.value = ''; loading.value = true; error.value = ''
    try {
      const result = readTaskList(await getSystemTasks(query))
      if (!current()) return false
      const lastPage = Math.max(1, Math.ceil(result.total / query.pageSize))
      if (query.page > lastPage) { context.pagination.page = lastPage; return await load() }
      rows.value = result.rows; context.pagination.setTotalSize(result.total); recentResults.value = {}
      void loadRecentResults()
      return true
    } catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, "定时任务加载失败，请重试", false), error.value = '定时任务加载失败，请重试'); return false }
    finally { if (version === listVersion) loading.value = false }
  }
  return { rows, loading, error, recentResults, recentLoading, recentError, load, loadRecentResults, invalidate }
}
