
import { reportLoadError } from '@/utils/load-error'
import { computed, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getMonitoringTaskDetail, postMonitoringTaskStart, postMonitoringTaskStop, putMonitoringTask } from '@/api/monitoring/task'
import { monitoringCanStop, monitoringProcessActive, readMonitoringTask, readMonitoringTaskResponse, readMonitoringRuntime } from '../task-records'
import type { MonitoringTaskSnapshot } from '../types'
import { useMonitoringTaskScope } from './useMonitoringTaskScope'
import { usePagePolling } from '@/hooks/use-page-polling'
import type { PollingContext } from '@/hooks/use-page-polling'

interface Options {
  blocked: () => boolean
  changed: (task: MonitoringTaskSnapshot, write: boolean) => void
  reset: () => void
  started: () => void
  stopped: () => void
}

export function useMonitoringTaskWorkspace(options: Options) {
  const task = ref<MonitoringTaskSnapshot | null>(null), codeText = ref(''), originalCode = ref('')
  const loading = ref(false), loadFailed = ref(false), ready = ref(false), saving = ref(false), actionLoading = ref(false)
  const stateLoading = ref(false), stateFailed = ref(false)
  const saveFailed = ref(false)
  const taskId = computed(() => task.value?.id ?? null), dirty = computed(() => codeText.value !== originalCode.value)
  const processActive = computed(() => monitoringProcessActive(task.value)), canStop = computed(() => monitoringCanStop(task.value))
  let selection = 0, choosing = 0, stateSequence = 0
  let ownerIdentity: string | null = null
  let cachedDraft: { identity: string; task: MonitoringTaskSnapshot; code: string; original: string } | null = null
  let saveJob: { promise: Promise<boolean>; selection: number; version: number } | null = null
  const scope = useMonitoringTaskScope(clear)
  const current = (selected: number, version: number) => scope.current(version) && selected === selection
  const polling = usePagePolling(context => refreshState(context), pauseStateRequests)
  watch(() => [ready.value, task.value?.status, task.value?.pid], () => {
    if (ready.value && task.value && ([0, 1, 5].includes(task.value.status) || Boolean(task.value.pid))) polling.start()
    else polling.stop()
  }, { flush: 'sync' })

  function pauseStateRequests() { ++stateSequence; stateLoading.value = false }
  function clear(preserveDraft = true) {
    if (!preserveDraft || ownerIdentity !== scope.identity()) cachedDraft = null
    else if (task.value && dirty.value) cachedDraft = { identity: ownerIdentity, task: task.value, code: codeText.value, original: originalCode.value }
    ++selection; ++choosing; pauseStateRequests()
    task.value = null; codeText.value = ''; originalCode.value = ''
    loading.value = false; loadFailed.value = false; stateFailed.value = false; saveFailed.value = false; ready.value = false
    options.reset()
  }
  async function load(record: MonitoringTaskSnapshot) {
    if (!scope.available()) return
    const selected = ++selection, version = scope.snapshot()
    pauseStateRequests(); options.reset()
    ownerIdentity = scope.identity()
    const draft = cachedDraft?.identity === ownerIdentity && cachedDraft.task.id === record.id ? cachedDraft : null
    task.value = readMonitoringTask(record); codeText.value = draft?.code ?? ''; originalCode.value = draft?.original ?? ''
    ready.value = false; loading.value = true; loadFailed.value = false; stateFailed.value = false; saveFailed.value = false
    try {
      const response = await getMonitoringTaskDetail(record.id)
      if (!current(selected, version)) return
      const result = readMonitoringTaskResponse(response, record.id)
      task.value = result; codeText.value = draft?.code ?? result.script_content; originalCode.value = result.script_content; ready.value = true
      if (cachedDraft === draft) cachedDraft = null
    } catch (loadFailure0) { if (current(selected, version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true) }
    finally { if (current(selected, version)) loading.value = false }
  }
  async function retryLoad() { if (task.value && !saving.value && !actionLoading.value) await load(task.value) }

  async function saveCode(showSuccess = true, duringStart = false): Promise<boolean> {
    const selected = selection, version = scope.snapshot()
    if (!scope.available() || !ready.value || !task.value || options.blocked() || (actionLoading.value && !duringStart)) return false
    const id = task.value.id
    while (current(selected, version)) {
      if (saveJob) {
        if (saveJob.selection !== selected || saveJob.version !== version) return false
        if (!await saveJob.promise) return false
        continue
      }
      if (!codeText.value.trim()) { Message.warning('脚本内容不能为空'); return false }
      if (!dirty.value) return true
      const code = codeText.value
      saving.value = true; saveFailed.value = false
      pauseStateRequests()
      const job = { selection: selected, version, promise: Promise.resolve(false) }
      saveJob = job
      job.promise = (async () => {
        try {
          const response = await putMonitoringTask({ id, script_content: code })
          if (!current(selected, version)) return false
          if (response.code !== 200) throw new Error('Code save failed')
          originalCode.value = code
          if (task.value) {
            task.value = { ...task.value, script_content: code }
            options.changed(task.value, true)
          }
          if (showSuccess) Message.success(response.msg || '代码保存成功')
          return true
        } catch { if (current(selected, version)) { saveFailed.value = true; Message.error('代码自动保存失败') }; return false }
        finally { if (saveJob === job) { saveJob = null; saving.value = false } }
      })()
      if (!await job.promise) return false
    }
    return false
  }
  async function select(record: MonitoringTaskSnapshot) {
    if (!scope.available() || record.id === taskId.value || actionLoading.value || options.blocked()) return
    const choice = ++choosing, version = scope.snapshot()
    if (dirty.value || saveJob) { if (!await saveCode(false)) return }
    if (choice !== choosing || !scope.current(version) || actionLoading.value || options.blocked()) return
    await load(record)
  }
  function reconcile(rows: MonitoringTaskSnapshot[], replace = true) {
    if (!scope.available()) return
    if (!task.value && cachedDraft?.identity === scope.identity()) { void load(cachedDraft.task); return }
    const found = rows.find(row => row.id === taskId.value)
    if (found && task.value) {
      task.value = { ...task.value, ...found }
      if (ready.value && !dirty.value && !saving.value && !actionLoading.value) {
        codeText.value = found.script_content
        originalCode.value = found.script_content
      }
    }
    else if ((!task.value || replace) && !dirty.value && !saving.value && !actionLoading.value) {
      if (rows.length) void load(rows[0]); else clear()
    }
  }
  async function refreshState(context?: PollingContext) {
    if (!scope.available() || taskId.value === null || stateLoading.value || !ready.value || actionLoading.value || saving.value || options.blocked()) return false
    const id = taskId.value, selected = selection, version = scope.snapshot(), request = ++stateSequence
    const valid = () => current(selected, version) && request === stateSequence && (!context || context.isCurrent())
    stateLoading.value = true; stateFailed.value = false
    try {
      const response = await getMonitoringTaskDetail(id)
      if (!valid()) return false
      task.value = readMonitoringTaskResponse(response, id)
      options.changed(task.value, false)
      return true
    } catch (loadFailure0) { if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), stateFailed.value = true); return false }
    finally { if (valid()) stateLoading.value = false }
  }
  async function control(kind: 'start' | 'stop') {
    if (!scope.available() || !ready.value || taskId.value === null || actionLoading.value || options.blocked()) return false
    if (kind === 'start' && processActive.value) { Message.warning('任务仍在运行或停止中，请等待进程完全停止后再运行'); return false }
    if (kind === 'stop' && !canStop.value) return false
    if (kind === 'stop' && saving.value) return false
    const id = taskId.value, selected = selection, version = scope.snapshot()
    let applied = false
    actionLoading.value = true
    try {
      if (kind === 'start') {
        do { if (!await saveCode(false, true)) return false } while (current(selected, version) && dirty.value)
      }
      if (!current(selected, version) || !task.value || (kind === 'start' && processActive.value)) return false
      pauseStateRequests()
      const response = kind === 'start' ? await postMonitoringTaskStart(id) : await postMonitoringTaskStop(id)
      if (!current(selected, version) || !task.value) return false
      const patch = readMonitoringRuntime(response, id)
      task.value = { ...task.value, ...patch }
      options.changed(task.value, true)
      applied = true
      Message.success(response.msg || (kind === 'start' ? '任务已提交运行' : '已提交停止请求'))
      if (kind === 'start') options.started(); else options.stopped()
      return true
    } catch { if (current(selected, version)) Message.error(kind === 'start' ? '任务运行失败，请重试' : '任务停止失败，请重试'); return false }
    finally {
      actionLoading.value = false
      if (applied && current(selected, version)) void refreshState()
    }
  }
  return {
    task, taskId, codeText, originalCode, dirty, loading, loadFailed, ready, saving, actionLoading,
    stateLoading, stateFailed, saveFailed, processActive, canStop,
    load, retryLoad, clear, select, reconcile, saveCode, refreshState, pauseStateRequests,
    run: () => control('start'), stop: () => control('stop'),
    snapshot: () => ({ selection, version: scope.snapshot() }),
    current: (snapshot: { selection: number; version: number }) => current(snapshot.selection, snapshot.version),
  }
}
