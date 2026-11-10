
import { reportLoadError } from '@/utils/load-error'
import { ref } from 'vue'
import { getScheduledTaskGroups } from '@/api/system/tasks'
import { readTaskGroupList, type TaskGroupListRecord, type TaskGroupQuery } from '../task-group-list-records'

interface Pagination { page: number; pageSize: number; setTotalSize: (total: number) => void }
export function useTaskGroupList(context: { available: () => boolean; capture: () => () => boolean; query: () => TaskGroupQuery; pagination: Pagination }) {
  const rows = ref<TaskGroupListRecord[]>([]), loading = ref(false), error = ref('')
  let version = 0
  let inFlight: { key: string; current: () => boolean; promise: Promise<boolean> } | null = null
  function invalidate(clear = false) {
    version++; inFlight = null; loading.value = false
    if (clear) { rows.value = []; error.value = ''; context.pagination.setTotalSize(0) }
  }
  function replace(record: TaskGroupListRecord) {
    invalidate()
    rows.value = rows.value.map(row => String(row.id) === String(record.id) ? { ...record, recent_results: row.recent_results } : row)
  }
  function load(): Promise<boolean> {
    if (!context.available()) { loading.value = false; return Promise.resolve(false) }
    const query = context.query(), key = JSON.stringify(query)
    if (inFlight?.key === key && inFlight.current()) return inFlight.promise
    const requestVersion = ++version, valid = context.capture()
    const current = () => context.available() && valid() && requestVersion === version && key === JSON.stringify(context.query())
    loading.value = true; error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const result = readTaskGroupList(await getScheduledTaskGroups(query))
        if (!current()) return false
        const last = Math.max(1, Math.ceil(result.total / query.pageSize))
        if (query.page > last) { context.pagination.page = last; return await load() }
        rows.value = result.rows; context.pagination.setTotalSize(result.total); return true
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "任务组加载失败，请重试", false), error.value = '任务组加载失败，请重试'); return false }
      finally { if (requestVersion === version) { loading.value = false; inFlight = null } }
    })
    inFlight = { key, current, promise }
    return promise
  }
  return { rows, loading, error, invalidate, replace, load }
}
