import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useUserStoreContext } from '@/store/modules/user'
import {
  postSystemTestSuiteDetailsApiExport,
  getSystemTestSuiteDetailsApiExportStatus,
  downloadSystemTestSuiteDetailsApiExport,
} from '@/api/system/test_sute_details'
import { reportIdentifier } from '../report-overview'
import { parseReportExportTask, reportExportBlob, saveReportExport, type ReportExportTask } from '../report-export'

interface ExportOptions {
  reportId(): string
  status(): number | 'all'
  available(): boolean
}

export function useReportApiExport(options: ExportOptions) {
  const route = useRoute(), userStore = useUserStoreContext()
  const phase = ref<'idle' | 'creating' | 'polling' | 'downloading' | 'error'>('idle')
  const creating = ref(false), checking = ref(false), error = ref('')
  const loading = computed(() => creating.value || checking.value || ['creating', 'polling', 'downloading'].includes(phase.value))
  let active = true, disposed = false, contextVersion = 0, activityVersion = 0
  let task: (ReportExportTask & { reportId: string }) | null = null
  let createPending: Promise<void> | null = null, cyclePending: Promise<void> | null = null
  let timer: ReturnType<typeof setTimeout> | undefined, resumeRequested = false
  const canRestart = computed(() => phase.value === 'error' && task !== null)
  const available = () => !disposed && active && document.visibilityState === 'visible' && options.available()
  function clearTimer() { if (timer !== undefined) clearTimeout(timer); timer = undefined }
  function schedule(delay = 1500) {
    clearTimer()
    if (available() && task && phase.value !== 'error') timer = setTimeout(() => { timer = undefined; void poll() }, delay)
  }
  function invalidate() {
    contextVersion += 1
    activityVersion += 1
    clearTimer()
    task = null
    resumeRequested = false
    phase.value = 'idle'
    error.value = ''
  }
  function pause() {
    activityVersion += 1
    clearTimer()
    resumeRequested = false
  }
  function resume() {
    if (!available() || !task || phase.value === 'error') return
    if (cyclePending) resumeRequested = true
    else void poll()
  }
  function poll(): Promise<void> {
    if (!available() || !task || phase.value === 'error') return Promise.resolve()
    if (cyclePending) return cyclePending
    clearTimer()
    const snapshot = { ...task }, version = contextVersion, activity = activityVersion
    const current = () => available() && version === contextVersion && activity === activityVersion && task?.id === snapshot.id
    checking.value = true
    phase.value = 'polling'
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const result = parseReportExportTask(await getSystemTestSuiteDetailsApiExportStatus(snapshot.id), snapshot.id)
        if (!current()) return
        task = { ...result, reportId: snapshot.reportId }
        if (result.status === 'fail') {
          task = null
          phase.value = 'error'
          error.value = 'API 报告导出失败，请重新导出'
          return
        }
        if (result.status !== 'success') return
        phase.value = 'downloading'
        const response: unknown = await downloadSystemTestSuiteDetailsApiExport(snapshot.id)
        if (!current()) return
        const blob = reportExportBlob(response)
        saveReportExport(blob, result.fileName || `API测试报告_${snapshot.reportId}_${Date.now()}.xlsx`)
        if (!current()) return
        task = null
        phase.value = 'idle'
        Message.success('API报告导出完成')
      } catch {
        if (current()) {
          phase.value = 'error'
          error.value = '查询或下载导出报告失败，请重试'
        }
      } finally {
        checking.value = false
        cyclePending = null
        const resume = resumeRequested
        resumeRequested = false
        if (available() && task && phase.value !== 'error') schedule(resume ? 0 : 1500)
      }
    })
    cyclePending = promise
    return promise
  }
  function start(): Promise<void> {
    if (!available()) return Promise.resolve()
    if (createPending) return createPending
    if (cyclePending) return cyclePending
    if (task) {
      error.value = ''
      phase.value = 'polling'
      return poll()
    }
    const id = reportIdentifier(options.reportId()), status = options.status()
    if (id === null || (status !== 'all' && (!Number.isInteger(status) || status < 0))) return Promise.resolve()
    const version = contextVersion
    const current = () => !disposed && version === contextVersion && options.reportId() === id
    creating.value = true
    phase.value = 'creating'
    error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const result = parseReportExportTask(await postSystemTestSuiteDetailsApiExport({ test_suite_id: id, status }))
        if (!current()) return
        task = { ...result, reportId: id }
        phase.value = 'polling'
        if (available()) {
          Message.success('导出任务已创建，完成后将自动下载')
          await poll()
        }
      } catch {
        if (current()) { phase.value = 'error'; error.value = '导出任务创建失败，请重试' }
      } finally {
        creating.value = false
        createPending = null
      }
    })
    createPending = promise
    return promise
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  function restart(): Promise<void> {
    if (!available()) return Promise.resolve()
    if (createPending) return createPending
    if (cyclePending) return cyclePending
    if (phase.value !== 'error') return Promise.resolve()
    invalidate()
    return start()
  }
  watch(() => [options.reportId(), route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], invalidate, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(() => { active = false; pause() })
  onActivated(() => { const wasInactive = !active; active = true; if (wasInactive) resume() })
  onBeforeUnmount(() => { disposed = true; active = false; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { loading, error, canRestart, start, restart }
}
