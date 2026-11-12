
import { reportLoadError } from '@/utils/load-error'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getExecutorTask } from '@/api/system/executor-task'
import { postUiAuthConfigAutoStart, postUiAuthConfigAutoCapture } from '@/api/uitest/auth-config'
import { loadExecutorTaskObservation, saveExecutorTaskObservation, clearExecutorTaskObservation } from '@/utils/executor-task-observer.mjs'
import { requiredUiAuthId, uiAuthResponse, type UiAuthId } from '../auth-editor-records'
import { authTaskBusiness, authTaskScope, authTaskTimeout, readAuthSubmission, readAuthTask, readAuthObservation, type UiAuthTaskAction } from '../auth-task-records'

interface AuthTarget { id: UiAuthId; auth_type: number }
interface Observation {
  id: UiAuthId; action: UiAuthTaskAction; taskId: UiAuthId; owner: string; key: string; legacy: boolean
  active: boolean; reading: boolean; version: number; deadline: number; timer: number | null
}
interface Context {
  available: () => boolean
  capture: () => () => boolean
  owner: () => string
  busy: (id: UiAuthId) => boolean
  onCaptured: () => void | Promise<unknown>
}
export function useAuthTaskObserver(context: Context) {
  const error = ref(''), loading = reactive(new Set<string>()), submitting = reactive(new Set<string>())
  function notifyError(message: string, cause?: unknown) {
    if (error.value !== message) reportLoadError(cause, message)
    error.value = message
  }
  const jobs = new Map<string, Observation>()
  const keyFor = (id: UiAuthId, action: UiAuthTaskAction, owner = context.owner()) => `${authTaskScope(action, owner)}:${id}`
  const isLoading = (id: UiAuthId, action: UiAuthTaskAction) => loading.has(keyFor(id, action)) || submitting.has(keyFor(id, action))
  const isSubmitting = (id: UiAuthId) => (['start', 'capture'] as const).some(action => submitting.has(keyFor(id, action)))
  function stop(job: Observation) {
    job.active = false; job.version++
    if (job.timer !== null) window.clearTimeout(job.timer)
    job.timer = null; loading.delete(job.key)
  }
  function pause() { for (const job of jobs.values()) stop(job); error.value = '' }
  const visible = (job: Observation) => context.available() && job.active && job.owner === context.owner() && jobs.get(job.key) === job
  function persist(job: Observation) {
    try {
      if (!saveExecutorTaskObservation(authTaskScope(job.action, job.owner), job.id, { taskId: job.taskId, businessType: authTaskBusiness(job.action), owner: job.owner })) throw Error('Observation not persisted')
      return true
    } catch { if (context.available() && job.owner === context.owner()) notifyError('任务已提交，观察记录暂未保存；请保留当前页面查看结果'); return false }
  }
  function clear(job: Observation) {
    try {
      clearExecutorTaskObservation(authTaskScope(job.action, job.owner), job.id, job.taskId)
      if (job.legacy) clearExecutorTaskObservation(`ui-auth-${job.action}`, job.id, job.taskId)
    } catch { if (visible(job)) notifyError('任务已结束，观察记录清理失败，请重新加载核对') }
  }
  function schedule(job: Observation, delay = 1000) {
    if (!visible(job) || job.timer !== null || job.reading) return
    job.timer = window.setTimeout(() => { job.timer = null; void poll(job) }, delay)
  }
  async function poll(job: Observation) {
    if (!visible(job) || job.reading) return
    if (Date.now() >= job.deadline) { notifyError('等待执行器任务结果超时，可重新点击原操作继续查看任务状态'); stop(job); return }
    const version = job.version, valid = context.capture()
    const current = () => visible(job) && version === job.version && valid()
    job.reading = true
    try {
      const response: unknown = await getExecutorTask(job.taskId, true)
      if (!current()) return
      const task = readAuthTask(response, job.taskId, job.id, job.action)
      error.value = ''
      if (job.legacy && persist(job)) {
        // 旧记录没有身份归属；后端按创建人鉴权且任务/业务信息核对通过后才转入当前身份。
        try { clearExecutorTaskObservation(`ui-auth-${job.action}`, job.id, job.taskId); job.legacy = false }
        catch { notifyError('任务状态已恢复，旧观察记录清理失败，请重新加载核对') }
      }
      if (task.terminal) {
        clear(job); stop(job); jobs.delete(job.key)
        if (task.status === 'success') {
          Message.success(job.action === 'start' ? '自动授权浏览器已打开，请完成登录后点击“完成登录”' : '授权缓存已提取并保存')
          if (job.action === 'capture') {
            try { await context.onCaptured() }
            catch (loadFailure0) { if (valid() && job.owner === context.owner()) notifyError('授权缓存已保存，列表加载失败，请重新加载列表', loadFailure0) }
          }
        } else notifyError('自动授权任务未完成，请查看任务通知，可重新发起操作')
      }
    } catch (loadFailure1) { if (current()) notifyError('任务状态加载失败，正在重试；请勿重复提交授权操作', loadFailure1) }
    finally {
      job.reading = false
      if (visible(job)) schedule(job, version === job.version ? 1000 : 0)
    }
  }
  function activate(job: Observation) {
    if (!context.available() || job.owner !== context.owner() || job.active) return
    job.active = true; job.version++; job.deadline = Date.now() + authTaskTimeout(job.action); loading.add(job.key)
    void poll(job)
  }
  function storedObservation(scope: string, id: UiAuthId): unknown {
    try { return loadExecutorTaskObservation(scope, id) }
    catch { notifyError('任务恢复记录暂不可用，请保留当前页面查看结果'); return null }
  }
  function restore(id: UiAuthId, action: UiAuthTaskAction): Observation | null | false {
    const owner = context.owner(), key = keyFor(id, action, owner), existing = jobs.get(key)
    if (existing) return existing
    try {
      const stored = storedObservation(authTaskScope(action, owner), id)
      const observation = readAuthObservation(stored, id, action, owner, false) ?? readAuthObservation(storedObservation(`ui-auth-${action}`, id), id, action, owner, true)
      if (!observation) return null
      const job: Observation = { id, action, taskId: observation.taskId, owner, key, legacy: observation.legacy, active: false, reading: false, version: 0, deadline: 0, timer: null }
      jobs.set(key, job); return job
    } catch { notifyError('授权任务观察记录异常，请重新加载核对'); return false }
  }
  function resume(rows: AuthTarget[]) {
    if (!context.available()) return
    for (const job of jobs.values()) if (job.owner === context.owner()) activate(job)
    for (const row of rows) {
      if (row.auth_type !== 1) continue
      for (const action of ['start', 'capture'] as const) {
        const id = requiredUiAuthId(row.id)
        if (submitting.has(keyFor(id, action))) continue
        const job = restore(id, action)
        if (job) activate(job)
      }
    }
  }
  async function start(record: AuthTarget, action: UiAuthTaskAction): Promise<boolean> {
    if (!context.available() || record.auth_type !== 1 || context.busy(record.id)) return false
    const id = requiredUiAuthId(record.id), owner = context.owner(), key = keyFor(id, action, owner)
    if (submitting.has(key) || loading.has(key)) return false
    const existing = restore(id, action)
    if (existing === false) return false
    if (existing) { activate(existing); return true }
    submitting.add(key); error.value = ''
    const valid = context.capture()
    let accepted = false
    try {
      const response: unknown = await (action === 'start' ? postUiAuthConfigAutoStart(id) : postUiAuthConfigAutoCapture(id))
      uiAuthResponse(response); accepted = true
      const taskId = readAuthSubmission(response)
      const job: Observation = { id, action, taskId, owner, key, legacy: false, active: false, reading: false, version: 0, deadline: 0, timer: null }
      jobs.set(key, job); persist(job); activate(job)
      return true
    } catch (cause) { if (valid()) notifyError(accepted ? '操作已提交，但返回的任务信息异常，请重新加载核对' : '自动授权操作提交失败，请重试', cause); return false }
    finally { submitting.delete(key) }
  }
  return { error, start, pause, resume, isLoading, isSubmitting }
}
