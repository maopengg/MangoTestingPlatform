
import { reportLoadError } from '@/utils/load-error'
import { computed, onMounted, reactive, ref } from 'vue'
import { getMonitoringTask } from '@/api/monitoring/task'
import { monitoringTaskQuery, readMonitoringTaskPage } from '../task-records'
import { monitoringTaskPageSize } from '../config'
import type { MonitoringTaskSnapshot, TaskSearchItem } from '../types'
import { useMonitoringTaskScope } from './useMonitoringTaskScope'

export function useMonitoringTaskList(items: TaskSearchItem[]) {
  const rows = ref<MonitoringTaskSnapshot[]>([]), loading = ref(false), loadingMore = ref(false), failed = ref(false)
  const lastChange = ref<'replace' | 'append' | 'patch'>('replace')
  const paging = reactive({ page: 1, pageSize: monitoringTaskPageSize, total: 0 })
  const hasMore = computed(() => rows.value.length < paging.total)
  let sequence = 0, pending: Promise<void> | null = null, pendingKey: string | null = null, failedAppend = false
  const scope = useMonitoringTaskScope(reset, () => { void load() })
  function invalidateRead() {
    ++sequence; pending = null; pendingKey = null; loading.value = false; loadingMore.value = false
  }
  function reset() {
    invalidateRead(); lastChange.value = 'replace'; rows.value = []; paging.page = 1; paging.total = 0; failed.value = false
  }
  function load(append = false, force = false): Promise<void> {
    if (!scope.available() || (append && (loading.value || loadingMore.value || !hasMore.value))) return Promise.resolve()
    const page = append ? paging.page + 1 : 1
    const query = monitoringTaskQuery(items, page, paging.pageSize), key = JSON.stringify(query)
    if (!force && pending && pendingKey === key) return pending
    const request = ++sequence, version = scope.snapshot()
    const current = () => request === sequence && scope.current(version)
    loading.value = !append; loadingMore.value = append; failed.value = false; pendingKey = key
    pending = (async () => {
      try {
        const response = await getMonitoringTask(query)
        if (!current()) return
        const result = readMonitoringTaskPage(response)
        const unique = new Map((append ? rows.value : []).map(task => [task.id, task]))
        result.rows.forEach(task => unique.set(task.id, task))
        lastChange.value = append ? 'append' : 'replace'
        rows.value = result.total === 0 ? [] : [...unique.values()]
        paging.page = page; paging.total = result.total
      } catch (loadFailure0) { if (current()) { (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true); failedAppend = append } }
      finally { if (current()) { loading.value = false; loadingMore.value = false; pendingKey = null; pending = null } }
    })()
    return pending
  }
  function updateTask(task: MonitoringTaskSnapshot, invalidate = false) {
    if (invalidate) invalidateRead()
    lastChange.value = 'patch'
    rows.value = rows.value.map(row => row.id === task.id ? task : row)
  }
  onMounted(() => { void load() })
  return { rows, loading, loadingMore, failed, paging, hasMore, lastChange, load, retry: () => load(failedAppend), reset, updateTask, invalidateRead }
}
