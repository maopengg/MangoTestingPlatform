
import { reportLoadError } from '@/utils/load-error'
import { computed, reactive, ref } from 'vue'
import { postUiElementCheck, putUiElementDeepCheckApply } from '@/api/uitest/element'
import { getActiveExecutorTasks, getExecutorTask } from '@/api/system/executor-task'
import { createUiElementCheckSession } from '@/utils/ui-element-check-session.mjs'
import { clearExecutorTaskObservation, loadExecutorTaskObservation, saveExecutorTaskObservation } from '@/utils/executor-task-observer.mjs'
import { cloneLosslessJson } from '@/utils/lossless-json'
import { liveId, liveObject, liveError, readLiveElement, readLiveResult, type LiveId, type LiveResult, type LiveElement } from '@/components/business/ui-live-workbench'
function elementResponse(value: unknown): unknown { const row = liveObject(value); if (row.code != null && row.code !== 200) throw Error('请求未成功，请重试'); return row.data }
interface ElementScope { available: () => boolean; capture: () => () => boolean }

export interface ElementWorkbenchPort {
  checkElementInWorkspace: (record: LiveElement, mode: 'normal' | 'deep', variables?: Record<string, string>) => Promise<unknown>
  acceptElementCheckResult: (value: unknown) => boolean
}
export function useElementChecks(options: {
  scope: ElementScope; pageId: () => LiveId | null; environment: () => LiveId | null; owner: () => string
  pageUrl: () => string; rows: () => Array<{ id: LiveId; name?: string }>; liveVisible: () => boolean; workbench: () => ElementWorkbenchPort | null
  variables: (record: unknown) => Promise<Record<string, string> | null>
  applyRuntime: (result: LiveResult) => void; refresh: () => Promise<unknown>
}) {
  const pending = reactive({ loadingKey: '', element: null as { id: LiveId; name: string } | null, taskId: '', checkId: '', kind: '' as '' | 'direct' | 'workspace' | 'scan', rowKey: '' })
  const result = reactive({ visible: false, title: '元素检测结果', data: null as LiveResult | null })
  const submitting = ref(false), recovering = ref(false), uncertain = ref(false), error = ref(''), applying = ref(false), applied = ref(false)
  const busy = computed(() => submitting.value || recovering.value || uncertain.value || Boolean(pending.loadingKey))
  let version = 0, recoverySequence = 0, pollTimer: number | null = null, timeout: number | null = null, recoveryTimer: number | null = null
  const session = createUiElementCheckSession()
  const observationScope = () => `ui-element-check:${options.owner()}`
  function clearTimers() { if (pollTimer !== null) window.clearTimeout(pollTimer); if (timeout !== null) window.clearTimeout(timeout); pollTimer = timeout = null }
  function finish() { version++; clearTimers(); session.cancel(); Object.assign(pending, { loadingKey: '', element: null, taskId: '', checkId: '', kind: '', rowKey: '' }) }
  function invalidate() { recoverySequence++; finish(); if (recoveryTimer !== null) window.clearTimeout(recoveryTimer); recoveryTimer = null; result.visible = false; result.data = null; recovering.value = uncertain.value = false; error.value = ''; applied.value = false }
  function schedule(delay = 1000) { if (!options.scope.available() || !pending.taskId) return; if (pollTimer !== null) window.clearTimeout(pollTimer); pollTimer = window.setTimeout(() => void poll(), delay) }
  function show(value: LiveResult) {
    result.data = cloneLosslessJson(value); result.title = `${value.check_mode === 'deep' ? '元素深度检测结果' : '元素检测结果'} / ${value.element_name || pending.element?.name || '页面元素'}`; result.visible = true; applied.value = false
    options.applyRuntime(value); finish(); void options.refresh()
  }
  function accept(value: unknown, source: 'direct' | 'workspace' = 'direct') {
    if (!options.scope.available() || !pending.loadingKey) return false
    const data = readLiveResult(value)
    if (pending.kind === 'scan') { if (!pending.rowKey || data.scan_row_key !== pending.rowKey) return false }
    else if (liveId(data.element_id) === null || String(data.element_id) !== String(pending.element?.id)) return false
    if (pending.kind === 'direct' && (source !== 'direct' || !session.accept(data))) return false
    if (pending.kind === 'workspace' && source !== 'workspace') return false
    if (pending.checkId && data.check_id !== pending.checkId) return false
    const taskId = pending.taskId, elementId = pending.element?.id
    if (taskId && elementId != null) clearExecutorTaskObservation(observationScope(), elementId, taskId)
    show(data); return true
  }
  async function poll() {
    const current = options.scope.capture(), request = version, taskId = pending.taskId, elementId = pending.element?.id
    if (!current() || !taskId || elementId == null) return
    try {
      const response: unknown = await getExecutorTask(taskId, true)
      if (!current() || request !== version || taskId !== pending.taskId) return
      const task = liveObject(elementResponse(response))
      if (String(task.task_id) !== taskId || String(task.business_id) !== String(elementId) || task.business_type !== 'u_element_check' || !['element_check', 'element_deep_check'].includes(String(task.task_type))) throw Error('检测任务归属不匹配')
      if (!task.terminal) { schedule(); return }
      const payload = readLiveResult(task.result)
      const data: LiveResult = liveId(payload.element_id) !== null ? payload : { element_id: elementId, element_name: pending.element?.name, check_id: pending.checkId, check_mode: task.task_type === 'element_deep_check' ? 'deep' : 'normal', status: 0, check_status: 'invalid', error_message: String(task.error_message || '执行器任务未返回检测结果') }
      if (!accept({ ...data, executor_task_id: taskId })) {
        clearExecutorTaskObservation(observationScope(), elementId, taskId)
        error.value = '检测结果与当前任务不匹配，请检查执行器后重试'; finish()
      }
    } catch (reason) { if (current() && request === version) { (reportLoadError(reason, "检测状态获取失败，正在重试", false), error.value = liveError(reason, '检测状态获取失败，正在重试')); schedule(1500) } }
  }
  async function start(record: unknown, mode: 'normal' | 'deep' = 'deep') {
    const snapshot = readLiveElement(record), current = options.scope.capture(), elementId = liveId(snapshot.id), environment = options.environment()
    if (environment === null) { error.value = '请先选择测试环境'; return false }
    if (!current() || busy.value || elementId === null) return false
    let requestVersion = version
    const owner = options.owner(), pageId = options.pageId()
    let shouldRecover = false
    submitting.value = true; error.value = ''
    try {
      const variables = mode === 'deep' ? await options.variables({ ...snapshot, page_url: options.pageUrl() }) : {}
      if (!current() || variables === null) return false
      if (options.liveVisible()) {
        const workbench = options.workbench()
        if (!workbench) throw Error('实时工作区正在加载，请稍后重试')
        return Boolean(await workbench.checkElementInWorkspace(snapshot, mode, variables))
      }
      finish(); pending.element = { id: elementId, name: snapshot.name || `元素 ${elementId}` }; pending.loadingKey = String(elementId); pending.kind = 'direct'
      const request = version, token = session.start(elementId)
      requestVersion = request
      timeout = window.setTimeout(() => { if (current() && request === version) { error.value = '检测等待回传超时，请确认执行器在线后重试'; finish() } }, mode === 'deep' ? 180000 : 60000)
      const response: unknown = await postUiElementCheck({ element_id: elementId, test_env: environment, check_mode: mode, runtime_variables: cloneLosslessJson(variables) })
      const data = liveObject(elementResponse(response)), taskId = liveId(data.task_id), checkId = String(data.check_id ?? '')
      if (taskId === null) { shouldRecover = true; throw Error('检测任务未返回任务ID，请核对执行器状态') }
      saveExecutorTaskObservation(`ui-element-check:${owner}`, elementId, { taskId, businessType: 'u_element_check', owner, environment, meta: { pageId, checkId, checkMode: mode } })
      shouldRecover = true
      if (!current() || request !== version || !session.isActive(token)) return false
      pending.checkId = checkId; session.bindCheckId(token, pending.checkId)
      pending.taskId = String(taskId)
      shouldRecover = false
      schedule(0); return true
    } catch (reason) { shouldRecover = true; if (current() && requestVersion === version) { error.value = liveError(reason, '检测触发失败，请重试'); finish() }; return false }
    finally {
      submitting.value = false
      if (shouldRecover && options.scope.available() && owner === options.owner() && String(pageId) === String(options.pageId()) && String(environment) === String(options.environment())) void recover()
    }
  }
  function workbenchStarted(value: unknown) {
    if (!options.scope.available()) return
    const row = liveObject(value), id = liveId(row.element_id), scanKey = typeof row.scan_row_key === 'string' ? row.scan_row_key : ''
    if (id === null && !scanKey) return
    finish(); pending.element = { id: id ?? 0, name: String(row.element_name || options.rows().find(item => String(item.id) === String(id))?.name || `元素 ${id}`) }; pending.loadingKey = scanKey || String(id); pending.rowKey = scanKey; pending.kind = scanKey ? 'scan' : 'workspace'
  }
  function workbenchResult(value: unknown) { return accept(value, 'workspace') }
  function workbenchFinished() { if (pending.kind === 'workspace' || pending.kind === 'scan') finish() }
  async function apply() {
    const current = options.scope.capture(), data = result.data, elementId = liveId(data?.element_id), taskId = liveId(data?.executor_task_id)
    if (!current() || !result.visible || elementId === null || taskId === null || applying.value || applied.value || !data?.selected_result?.locator_engine?.locator_updates?.some(row => row.same_target && row.slot && row.loc)) return false
    applying.value = true; error.value = ''
    try { const response: unknown = await putUiElementDeepCheckApply({ element_id: elementId, task_id: taskId }); elementResponse(response); if (!current() || result.data !== data || !result.visible) return false; applied.value = true; await options.refresh(); return true }
    catch (reason) { if (current() && result.data === data) error.value = liveError(reason, '写入定位组失败，请重试'); return false }
    finally { applying.value = false }
  }
  async function recover() {
    const current = options.scope.capture(), request = ++recoverySequence, owner = options.owner(), environment = options.environment(), pageId = options.pageId()
    if (!current() || pending.loadingKey || submitting.value || environment === null || pageId === null) return
    recovering.value = true
    const wasUncertain = uncertain.value
    try {
      const known = options.rows().map(row => ({ row, observation: liveObject(loadExecutorTaskObservation(observationScope(), row.id)) })).filter(({ observation }) => liveId(observation.taskId) !== null && observation.businessType === 'u_element_check' && observation.owner === owner && String(observation.environment) === String(environment) && String(liveObject(observation.meta).pageId) === String(pageId))
      if (known.length === 1) {
        if (!current() || request !== recoverySequence) return
        const { row, observation } = known[0], meta = liveObject(observation.meta)
        finish(); pending.element = { id: row.id, name: row.name || `元素 ${row.id}` }; pending.loadingKey = String(row.id); pending.taskId = String(observation.taskId); pending.checkId = String(meta.checkId ?? ''); pending.kind = 'direct'
        const token = session.start(row.id); session.bindCheckId(token, pending.checkId); uncertain.value = false; error.value = ''; schedule(0); return
      }
      const response: unknown = await getActiveExecutorTasks({ business_type: 'u_element_check' }, true)
      if (!current() || request !== recoverySequence) return
      const data = elementResponse(response)
      if (!Array.isArray(data)) throw Error('活跃检测任务格式不正确')
      const active = data.map(liveObject).filter(task => task.business_type === 'u_element_check' && task.terminal !== true && (task.workspace_id == null || task.workspace_id === '') && options.rows().some(row => String(row.id) === String(task.business_id)))
      uncertain.value = active.length > 0
      if (uncertain.value) error.value = '存在未完成检测，缺少可核对的环境记录；正在等待任务结束，避免重复提交'
      else if (wasUncertain) error.value = ''
    } catch (reason) { if (current() && request === recoverySequence) { uncertain.value = true; error.value = liveError(reason, '检测任务恢复失败，正在重试') } }
    finally {
      if (current() && request === recoverySequence) {
        recovering.value = false
        if (uncertain.value) { if (recoveryTimer !== null) window.clearTimeout(recoveryTimer); recoveryTimer = window.setTimeout(() => void recover(), 1500) }
      }
    }
  }
  return { pending, result, busy, submitting, error, applying, applied, start, poll, recover, invalidate, workbenchStarted, workbenchResult, workbenchFinished, apply }
}
