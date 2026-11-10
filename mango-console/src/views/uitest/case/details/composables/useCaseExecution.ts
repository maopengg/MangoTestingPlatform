
import { reportLoadError } from '@/utils/load-error'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message, Notification } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getUiCaseRun } from '@/api/uitest/case'
import { getActiveExecutorTasks, getExecutorTask } from '@/api/system/executor-task'
import { clearExecutorTaskObservation, loadExecutorTaskObservation, saveExecutorTaskObservation } from '@/utils/executor-task-observer.mjs'
import { claimExecutorTaskNotification } from '@/utils/executor-task-notification'
import { uiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import { readCaseRuntimeResult } from '../runtime-results'
import { caseExecutionScope, readActiveCaseExecutionTasks, readCaseExecutionObservation, readCaseExecutionSubmission, readCaseExecutionTask, type CaseExecutionLaunch, type CaseExecutionTask, type CaseExecutionObservation } from '../case-execution'

interface Job {
  taskId: UiCaseAssetId; caseId: UiCaseAssetId; environment: UiCaseAssetId; owner: string; executionId: string; legacy: boolean
  active: boolean; reading: boolean; version: number; timer: number | null; handled: boolean
}
export function useCaseExecution(options: {
  caseId: () => UiCaseAssetId | null; name: () => string; busy: () => boolean
  started: (value: CaseExecutionLaunch & { executionId: string }) => void
  finished: (task: CaseExecutionTask, current: () => boolean) => void | Promise<unknown>
}) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const submitting = ref(false), recovering = ref(false), uncertain = ref(false), executionId = ref(''), error = ref(''), storageError = ref('')
  const selected = shallowRef<Job | null>(null), jobs = new Map<string, Job>()
  let active = true, disposed = false, version = 0, recoverySequence = 0, recoveryTimer: number | null = null
  let recoveringRead: { current: () => boolean; promise: Promise<boolean> } | null = null
  let write: Promise<boolean> | null = null
  const owner = () => JSON.stringify([user.userId, user.roleId, user.selected_environment])
  const identity = () => JSON.stringify([route.path, route.fullPath, options.caseId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  function capture() { const key = identity(), revision = version; return () => available() && key === identity() && revision === version }
  function key(job: Pick<Job, 'caseId' | 'owner' | 'taskId'>) { return `${caseExecutionScope(job.owner)}:${job.caseId}:${job.taskId}` }
  const visible = (job: Job) => available() && selected.value === job && job.active && job.owner === owner() && String(job.caseId) === String(options.caseId())
  function stop(job: Job) { job.active = false; job.version++; if (job.timer !== null) window.clearTimeout(job.timer); job.timer = null }
  function clearRecoveryTimer() { if (recoveryTimer !== null) window.clearTimeout(recoveryTimer); recoveryTimer = null }
  function pause(clear = false) {
    version++; recoverySequence++; recoveringRead = null; recovering.value = false; clearRecoveryTimer()
    for (const job of jobs.values()) stop(job)
    if (clear) { selected.value = null; executionId.value = ''; uncertain.value = false; error.value = ''; storageError.value = '' }
  }
  function persist(job: Job) {
    if (!job.executionId) return false
    try {
      if (!saveExecutorTaskObservation(caseExecutionScope(job.owner), job.caseId, { taskId: job.taskId, businessType: 'u_case', owner: job.owner, environment: job.environment, executionId: job.executionId })) throw Error('Observation not persisted')
      return true
    } catch { if (visible(job)) storageError.value = '任务已提交，观察记录保存失败；请保留当前页面查看结果'; return false }
  }
  function clearStored(job: Job) {
    try {
      clearExecutorTaskObservation(caseExecutionScope(job.owner), job.caseId, job.taskId)
      if (job.legacy) clearExecutorTaskObservation('ui-case-run', job.caseId, job.taskId)
    } catch { if (visible(job)) storageError.value = '任务已结束，观察记录清理失败，请重新核对' }
  }
  function schedule(job: Job, delay = 1000) {
    if (!visible(job) || job.reading || job.timer !== null || job.handled) return
    job.timer = window.setTimeout(() => { job.timer = null; void poll(job) }, delay)
  }
  function notify(job: Job, task: CaseExecutionTask) {
    if (!claimExecutorTaskNotification(job.taskId)) return
    const name = options.name() || `用例 ${job.caseId}`
    if (task.status === 'success') Notification.success({ title: 'Case 执行完成', content: `「${name}」已执行成功`, duration: 5000, closable: true })
    else if (task.status === 'cancelled') Notification.warning({ title: 'Case 执行已取消', content: `「${name}」已停止执行`, duration: 5000, closable: true })
    else Notification.error({ title: task.status === 'timeout' ? 'Case 执行超时' : 'Case 执行失败', content: task.error || `「${name}」执行未通过，请查看执行结果`, duration: 8000, closable: true })
  }
  async function poll(job: Job) {
    if (!visible(job) || job.reading || job.handled) return
    const valid = capture(), revision = job.version, current = () => visible(job) && revision === job.version && valid()
    job.reading = true; let retry = 1000
    try {
      const response: unknown = await getExecutorTask(job.taskId, true)
      if (!current()) return
      const task = readCaseExecutionTask(response, job.caseId, job.taskId)
      error.value = ''
      if (!task.terminal) { if (!job.executionId) error.value = '发现该用例的执行任务，正在核对执行环境；请勿重复执行'; return }
      let scoped = !!job.executionId
      if (task.result && uiCaseAssetObject(task.result).id != null) {
        const result = readCaseRuntimeResult(task.result)
        if (String(result.id) !== String(job.caseId)) throw Error('Unexpected case task result')
        scoped = String(result.testEnv) === String(job.environment) && (!job.executionId || job.executionId === result.executionId)
        if (scoped) { job.executionId = result.executionId; executionId.value = result.executionId }
      }
      if (!current()) return
      job.handled = true; clearStored(job); stop(job); selected.value = null
      if (!scoped) { executionId.value = ''; error.value = '恢复任务已结束，当前环境归属无法确认或不匹配；请查看执行历史'; return }
      notify(job, task)
      const completionCurrent = () => valid() && executionId.value === job.executionId && write === null
      try { await options.finished(task, completionCurrent) }
      catch (loadFailure0) { if (completionCurrent()) (reportLoadError(loadFailure0, "任务已结束，结果加载失败，请重试读取结果", false), error.value = '任务已结束，结果加载失败，请重试读取结果') }
    } catch (loadFailure1) { if (current()) { (reportLoadError(loadFailure1, "任务状态加载失败，正在重试；请勿重复执行", false), error.value = '任务状态加载失败，正在重试；请勿重复执行'); retry = 1500 } }
    finally { job.reading = false; if (visible(job)) schedule(job, revision === job.version ? retry : 0) }
  }
  function activate(job: Job) {
    if (!available() || job.owner !== owner() || String(job.caseId) !== String(options.caseId())) return
    selected.value = job; job.active = true; job.version++
    if (job.executionId) executionId.value = job.executionId
    if (!job.handled) void poll(job)
    else { clearStored(job); selected.value = null }
  }
  function remember(taskId: UiCaseAssetId, caseId: UiCaseAssetId, environment: UiCaseAssetId, jobOwner: string, execution = '', legacy = false): Job {
    const candidate: Job = { taskId, caseId, environment, owner: jobOwner, executionId: execution, legacy, active: false, reading: false, version: 0, timer: null, handled: false }
    const existing = jobs.get(key(candidate))
    if (existing) return existing
    jobs.set(key(candidate), candidate); return candidate
  }
  function retryRecovery() {
    clearRecoveryTimer(); const current = capture()
    recoveryTimer = window.setTimeout(() => { recoveryTimer = null; if (current()) void recover(false) }, 1500)
  }
  function recover(showLoading = true): Promise<boolean> {
    const caseId = options.caseId(), env = uiCaseAssetId(user.selected_environment)
    if (!available() || caseId === null || env === null) return Promise.resolve(false)
    if (selected.value && !selected.value.handled && selected.value.owner === owner() && String(selected.value.caseId) === String(caseId)) {
      const job = selected.value
      if (!job.active) activate(job)
      else if (showLoading && !job.reading) {
        if (job.timer !== null) window.clearTimeout(job.timer)
        job.timer = null; recovering.value = true; const current = capture()
        return poll(job).then(() => true).finally(() => { if (current()) recovering.value = false })
      }
      return Promise.resolve(true)
    }
    if (recoveringRead?.current()) { if (showLoading) recovering.value = true; return recoveringRead.promise }
    clearRecoveryTimer(); const valid = capture(), sequence = ++recoverySequence, jobOwner = owner(), current = () => valid() && sequence === recoverySequence
    recovering.value = showLoading; uncertain.value = true; error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        let observation: CaseExecutionObservation | null = null
        for (const legacy of [false, true]) {
          const scope = legacy ? 'ui-case-run' : caseExecutionScope(jobOwner)
          try { observation = readCaseExecutionObservation(loadExecutorTaskObservation(scope, caseId), caseId, env, jobOwner, legacy) }
          catch {
            try { clearExecutorTaskObservation(scope, caseId) } catch { /* 存储不可用时仍可从后端恢复。 */ }
            storageError.value = '本地任务观察记录异常，正在从服务器重新核对'
          }
          if (observation) break
        }
        if (observation) { const job = remember(observation.taskId, caseId, env, jobOwner, observation.executionId, observation.legacy); activate(job); uncertain.value = false; return true }
        const response: unknown = await getActiveExecutorTasks({ business_type: 'u_case', business_id: caseId }, true)
        if (!current()) return false
        const tasks = readActiveCaseExecutionTasks(response, caseId)
        if (tasks.length > 1) throw Error('Ambiguous case tasks')
        if (tasks[0]) activate(remember(tasks[0].taskId, caseId, env, jobOwner))
        uncertain.value = false; return true
      } catch { if (current()) { error.value = '执行任务恢复失败或存在多个待核对任务，正在重试；请勿重复执行'; retryRecovery() }; return false }
      finally { if (sequence === recoverySequence) { recovering.value = false; recoveringRead = null } }
    })
    recoveringRead = { current, promise }; return promise
  }
  function start(prepare: (current: () => boolean) => Promise<CaseExecutionLaunch | null>): Promise<boolean> {
    const caseId = options.caseId(), env = uiCaseAssetId(user.selected_environment)
    if (write) return Promise.resolve(false)
    if (!available() || caseId === null || env === null || options.busy()) return Promise.resolve(false)
    const valid = capture(), jobOwner = owner(); submitting.value = true; error.value = ''
    const promise = Promise.resolve().then(async () => {
      let accepted = false
      try {
        if (!await recover(false) || !valid() || selected.value || uncertain.value) return false
        const prepared = await prepare(valid)
        if (!prepared || !valid()) return false
        const launch: CaseExecutionLaunch = { actuatorUsername: prepared.actuatorUsername, withLive: prepared.withLive }
        const response: unknown = await getUiCaseRun(caseId, env, launch.actuatorUsername)
        uiCaseAssetResponse(response)
        accepted = true
        const submission = readCaseExecutionSubmission(response, caseId, env)
        const job = remember(submission.taskId, caseId, env, jobOwner, submission.executionId)
        const saved = persist(job)
        if (!valid()) return false
        if (!saved) storageError.value = '任务已提交，观察记录保存失败；请保留当前页面查看结果'
        executionId.value = submission.executionId
        options.started({ ...launch, executionId: submission.executionId })
        activate(job); Message.loading(submission.message); return true
      } catch {
        if (valid()) { error.value = accepted ? '操作已提交，但任务返回信息异常，正在重新核对；请勿重复执行' : '执行请求失败，正在核对是否已提交；请勿重复执行'; uncertain.value = true; retryRecovery() }
        return false
      } finally { submitting.value = false; write = null }
    })
    write = promise; return promise
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') pause(); else if (available()) void recover(false) }
  watch(identity, () => { pause(true); if (available()) void recover() }, { flush: 'sync' })
  onMounted(() => { document.addEventListener('visibilitychange', visibilityChanged); void recover() })
  onActivated(() => { active = true; if (available()) void recover(false) })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(true); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { submitting, recovering, executionId: computed(() => executionId.value), active: computed(() => selected.value !== null || uncertain.value), error: computed(() => error.value || storageError.value), start, recover }
}
