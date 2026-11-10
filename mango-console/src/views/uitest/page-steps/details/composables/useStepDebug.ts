
import { reportLoadError } from '@/utils/load-error'
import { ref } from 'vue'
import { getUiStepsTest } from '@/api/uitest/page-steps'
import { getExecutorTask, getActiveExecutorTasks } from '@/api/system/executor-task'
import { getExecutionResultLatestResolved } from '@/api/system/execution_result'
import { clearExecutorTaskObservation, loadExecutorTaskObservation, saveExecutorTaskObservation } from '@/utils/executor-task-observer.mjs'
import { cloneLosslessJson } from '@/utils/lossless-json'
import { liveObject, liveId } from '@/components/business/ui-live-workbench'
import { readStepResult, requiredStepId, stepResponse, stepArray, type StepId, type StepResult, type StepExecution } from '@/components/business/ui-page-step'
import type { UiStepControl } from '@/types/components'

export function useStepDebug(options: {
  capture: () => () => boolean; id: () => StepId | null; environment: () => StepId | null; owner: () => string
  control: () => UiStepControl; ready: () => Promise<boolean>; count: () => number
  workspace: () => boolean; startWorkspace: (id?: StepId) => Promise<boolean>
  result: (value: StepResult) => void; status: (status: number) => void; refresh: () => Promise<unknown>
}) {
  const running = ref(false), submitting = ref(false), singleSubmitting = ref(false), completed = ref(false)
  const error = ref(''), resultLoading = ref(false), resultError = ref(''), taskId = ref(''), slotId = ref(''), uncertain = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null, completedTimer: ReturnType<typeof setTimeout> | null = null, generation = 0, readSequence = 0, requesting = false, failures = 0
  const observationScope = () => `ui-page-step-debug:${options.owner()}`
  function stop() { generation++; running.value = false; taskId.value = slotId.value = ''; uncertain.value = false; error.value = ''; completed.value = false; requesting = false; if (timer !== null) clearTimeout(timer); if (completedTimer !== null) clearTimeout(completedTimer); timer = completedTimer = null }
  function invalidate() { stop(); readSequence++; resultLoading.value = false; resultError.value = '' }
  function schedule(delay = 2000) { const valid = options.capture(), version = generation; if (timer !== null) clearTimeout(timer); if (running.value && valid()) timer = setTimeout(() => { timer = null; if (valid() && version === generation) void poll() }, delay) }
  async function latest(showLoading = false): Promise<StepExecution | null> {
    const current = options.capture(), id = options.id(), environment = options.environment(), sequence = ++readSequence
    if (!current() || id === null || environment === null) return null
    if (showLoading) resultLoading.value = true
    resultError.value = ''
    try {
      const response: unknown = await getExecutionResultLatestResolved({ source_type: 'page', target_type: 'ui_page_step', target_id: id, test_env: environment, page: 1, pageSize: 1 }, !showLoading)
      if (!current() || sequence !== readSequence) return null
      const data = stepResponse(response)
      if (data == null) { options.result(readStepResult(null)); return null }
      const row = liveObject(data), result = readStepResult(row.result_data)
      const execution = { id: requiredStepId(row.id), create_time: String(row.create_time ?? ''), result_data: result }
      options.result(result); return execution
    } catch (loadFailure0) { if (current() && sequence === readSequence) (reportLoadError(loadFailure0, "最近结果加载失败，请重试", false), resultError.value = '最近结果加载失败，请重试'); return null }
    finally { if (current() && sequence === readSequence) resultLoading.value = false }
  }
  async function finish(result: StepResult) {
    const current = options.capture(), version = generation
    if (!running.value) return
    options.result(result); options.status(Number(result.status ?? 0))
    if (timer !== null) clearTimeout(timer); timer = null
    if (taskId.value && options.id() !== null) clearExecutorTaskObservation(observationScope(), options.id(), taskId.value)
    taskId.value = ''; slotId.value = ''; uncertain.value = false
    try { await options.refresh() }
    finally { if (current() && version === generation) running.value = false }
    if (!current() || version !== generation) return
    completed.value = true; completedTimer = setTimeout(() => { if (current() && version === generation) completed.value = false }, 1800)
  }
  async function poll() {
    const current = options.capture(), version = generation, id = options.id(), task = taskId.value
    if (!current() || !running.value || id === null || requesting) return
    requesting = true
    try {
      if (uncertain.value) { await recover(); return }
      if (!task) {
        // 工作区负责派发；未拿到可核对任务前不以旧结果判定本次完成。
        await recover(); return
      }
      const response: unknown = await getExecutorTask(task, true)
      if (!current() || version !== generation || task !== taskId.value) return
      const value = liveObject(stepResponse(response))
      if (String(value.task_id) !== task || String(value.business_id) !== String(id) || value.business_type !== 'u_page_step') throw Error('任务归属不匹配')
      failures = 0; error.value = ''
      if (value.terminal) {
        const result = readStepResult(value.result)
        if (!Array.isArray(result.element_result_list)) throw Error('执行任务未返回步骤结果')
        await finish(result)
      } else options.status(3)
    } catch { if (current() && version === generation) { failures++; error.value = '结果刷新异常，正在重试' } }
    finally { if (current() && version === generation) { requesting = false; if (running.value) schedule(error.value ? Math.min(1000 * 2 ** Math.max(0, failures - 1), 10000) : 2000) } }
  }
  async function recover() {
    const current = options.capture(), version = generation, id = options.id(), environment = options.environment(), owner = options.owner()
    if (!current() || id === null || environment === null || submitting.value || singleSubmitting.value) return
    try {
      const observation = liveObject(loadExecutorTaskObservation(observationScope(), id))
      if (liveId(observation.taskId) !== null && observation.owner === owner && String(observation.environment) === String(environment) && observation.businessType === 'u_page_step') {
        taskId.value = String(observation.taskId); slotId.value = String(observation.slotId ?? ''); uncertain.value = false; running.value = true; schedule(0); return
      }
      const response: unknown = await getActiveExecutorTasks({ business_type: 'u_page_step', business_id: id }, true)
      if (!current() || version !== generation) return
      const tasks = stepArray(stepResponse(response)).map(liveObject).filter(row => row.terminal !== true && row.business_type === 'u_page_step' && String(row.business_id) === String(id))
      uncertain.value = tasks.length > 0; running.value = uncertain.value
      error.value = uncertain.value ? '存在未完成任务，缺少可核对的环境记录；正在等待结束，避免重复调试' : ''
      if (running.value) schedule()
    } catch { if (current() && version === generation) { uncertain.value = running.value = true; error.value = '任务恢复失败，正在重试'; schedule() } }
  }
  async function run(detailId?: StepId) {
    const current = options.capture(), id = options.id(), environment = options.environment(), owner = options.owner(), control = cloneLosslessJson(options.control())
    if (!current() || id === null || environment === null || submitting.value || singleSubmitting.value || running.value) return false
    const loading = detailId === undefined ? submitting : singleSubmitting
    let needsRecovery = false
    loading.value = true; error.value = ''
    try {
      if (!(await options.ready()) || !current()) return false
      stop(); running.value = true; const version = generation
      if (options.workspace()) {
        if (!(await options.startWorkspace(detailId)) || !current() || version !== generation) { if (current() && version === generation) stop(); return false }
        // 工作区回传用slot关联；无关联时由恢复接口观察实际任务。
        schedule(); return true
      }
      const response: unknown = await getUiStepsTest(id, environment, undefined, control, detailId)
      const data = liveObject(stepResponse(response)), acceptedTask = requiredStepId(data.task_id)
      saveExecutorTaskObservation(`ui-page-step-debug:${owner}`, id, { taskId: acceptedTask, businessType: 'u_page_step', owner, environment, slotId: data.slot_id ?? '', meta: { detailId } })
      if (!current() || version !== generation) return false
      taskId.value = String(acceptedTask); slotId.value = String(data.slot_id ?? ''); options.status(2); schedule(0); return true
    } catch { if (current()) { stop(); error.value = '调试触发失败，请检查执行器状态后重试'; needsRecovery = true }; return false }
    finally { loading.value = false; if (needsRecovery || (!current() && options.capture()() && owner === options.owner() && String(id) === String(options.id()) && String(environment) === String(options.environment()))) void recover() }
  }
  function message(event: Event) {
    if (!options.capture()() || !running.value || !slotId.value) return
    const message = liveObject((event as CustomEvent<unknown>).detail), data = liveObject(message.data), result = readStepResult(data.func_args)
    if (data.func_name !== 'u_page_steps' || result.case_step_details_id != null || String(result.id) !== String(options.id()) || String(result.slot_id) !== slotId.value) return
    options.result(result)
    if (result.is_final) void finish(result)
  }
  function acceptWorkspace(value: unknown) {
    const row = liveObject(value), id = options.id(), environment = options.environment(), task = liveId(row.task_id)
    if (!options.capture()() || !running.value || task === null || id === null || String(row.page_step_id) !== String(id) || String(row.test_env) !== String(environment)) return
    taskId.value = String(task); slotId.value = String(row.slot_id ?? '')
    const owner = options.owner()
    saveExecutorTaskObservation(observationScope(), id, { taskId: task, slotId: slotId.value, owner, environment, businessType: 'u_page_step' })
  }
  return { running, submitting, singleSubmitting, completed, error, resultLoading, resultError, taskId, slotId, uncertain, run, latest, recover, poll, stop, invalidate, message, acceptWorkspace }
}
