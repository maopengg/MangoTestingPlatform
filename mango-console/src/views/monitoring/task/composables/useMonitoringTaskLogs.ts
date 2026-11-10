
import { reportLoadError, runLoadRequest } from '@/utils/load-error'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { downloadMonitoringTaskLog, getMonitoringTaskLogs } from '@/api/monitoring/task'
import { monitoringLogInterval, monitoringLogLimit } from '../config'
import { readMonitoringLog } from '../task-records'
import type { TaskWorkspaceVersion } from '../types'
import { useMonitoringTaskScope } from './useMonitoringTaskScope'

interface Options {
  taskId: () => number | null
  snapshot: () => TaskWorkspaceVersion
  current: (version: TaskWorkspaceVersion) => boolean
  refreshState: () => Promise<boolean>
  pauseState: () => void
  scroll: () => void
}

export function useMonitoringTaskLogs(options: Options) {
  const visible = ref(false), text = ref(''), autoScroll = ref(true)
  const loading = ref(false), failed = ref(false), downloading = ref(false)
  let sequence = 0, pending = false, timer: ReturnType<typeof setInterval> | null = null
  const urls = new Map<string, ReturnType<typeof setTimeout>>()
  const scope = useMonitoringTaskScope(() => close(true))
  const available = () => scope.available() && visible.value && document.visibilityState === 'visible'
  function releaseUrls() {
    urls.forEach((handle, url) => { clearTimeout(handle); URL.revokeObjectURL(url) })
    urls.clear()
  }
  function pause() {
    ++sequence; pending = false; loading.value = false
    if (timer !== null) { clearInterval(timer); timer = null }
    options.pauseState()
  }
  function close(clear = false) {
    visible.value = false; pause(); releaseUrls()
    if (clear) { text.value = ''; failed.value = false }
  }
  function scrollIfCurrent(version: TaskWorkspaceVersion, request: number) {
    void nextTick(() => { if (available() && request === sequence && options.current(version) && autoScroll.value) options.scroll() })
  }
  async function refresh(silent = false) {
    const id = options.taskId()
    if (!available() || id === null || pending) return
    const request = ++sequence, version = options.snapshot(), context = scope.snapshot()
    const current = () => available() && request === sequence && options.current(version) && scope.current(context)
    pending = true
    if (!silent) loading.value = true
    try {
      const response = await runLoadRequest(silent, () => getMonitoringTaskLogs(id, monitoringLogLimit))
      if (!current()) return
      const log = readMonitoringLog(response)
      const changed = text.value !== log
      if (changed) text.value = log
      if (changed || !silent) scrollIfCurrent(version, request)
      failed.value = false
    } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", silent), failed.value = true) }
    finally { if (current()) { pending = false; loading.value = false } }
  }
  function sync() {
    if (!available() || options.taskId() === null) { pause(); return }
    if (timer === null) timer = setInterval(() => {
      if (!available()) { pause(); return }
      void refresh(true); void options.refreshState()
    }, monitoringLogInterval)
  }
  function open() {
    if (!scope.available() || options.taskId() === null) { Message.warning('请先选择任务'); return }
    if (visible.value) { void refresh(false); return }
    visible.value = true
  }
  watch(visible, shown => {
    pause()
    if (shown && available()) { void refresh(false); void options.refreshState(); sync() }
    else releaseUrls()
  }, { flush: 'sync' })
  function visibilityChanged() {
    if (!available()) pause()
    else { void refresh(true); void options.refreshState(); sync() }
  }
  async function download() {
    const id = options.taskId()
    if (!available() || id === null || downloading.value) return
    const version = options.snapshot(), context = scope.snapshot(), epoch = windowEpoch
    // 日志读取会推进 sequence；下载只绑定窗口、任务及身份，不被正常的日志刷新打断。
    const current = () => available() && options.current(version) && scope.current(context) && windowEpoch === epoch
    downloading.value = true
    try {
      const response = await downloadMonitoringTaskLog(id)
      if (!current()) return
      if (!(response.data instanceof Blob) || response.data.type.includes('json')) throw new Error('Invalid log download')
      const url = URL.createObjectURL(response.data), link = document.createElement('a')
      try {
        link.href = url; link.download = `任务日志_${id}_${new Date().getTime()}.log`
        document.body.appendChild(link); link.click()
      } catch (error) { URL.revokeObjectURL(url); throw error
      } finally { link.remove() }
      const handle = setTimeout(() => { URL.revokeObjectURL(url); urls.delete(url) }, 1000)
      urls.set(url, handle)
      Message.success('日志下载成功')
    } catch { if (current()) Message.error('下载失败') }
    finally { downloading.value = false }
  }
  let windowEpoch = 0
  watch(visible, () => { ++windowEpoch }, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onBeforeUnmount(() => { close(true); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { visible, text, autoScroll, loading, failed, downloading, open, close, refresh, download }
}
