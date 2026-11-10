
import { reportLoadError } from '@/utils/load-error'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getExecutionResultLatestResolved } from '@/api/system/execution_result'
import { uiCaseAssetId, uiCaseAssetObject, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import { UI_CASE_RESULT_SOCKET_EVENTS } from '../config'
import { mergeCaseNodeProgress, mergeCaseRuntimeStep, readCaseNodeProgress, readCaseRuntimeResult, readCaseRuntimeStep, readLatestCaseRuntime, type CaseRuntimeResult } from '../runtime-results'

export function useCaseRuntimeResults(options: {
  caseId: () => UiCaseAssetId | null; executionId: () => string; stepIds: () => UiCaseAssetId[]
  updated: (result: CaseRuntimeResult, final: boolean) => void; refresh: () => unknown; finished: (executionId: string) => void
}) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const result = shallowRef<CaseRuntimeResult | null>(null), pending = ref(false), loading = ref(false), error = ref('')
  const socketEvents = new Set<string>(UI_CASE_RESULT_SOCKET_EVENTS)
  let active = true, disposed = false, version = 0, sequence = 0
  let timer: ReturnType<typeof window.setTimeout> | null = null
  let reading: { current: () => boolean; promise: Promise<boolean> } | null = null
  const identity = () => JSON.stringify([route.path, route.fullPath, options.caseId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const environment = () => uiCaseAssetId(user.selected_environment)
  function capture() { const key = identity(), revision = version; return () => available() && key === identity() && revision === version }
  function clearTimer() { if (timer !== null) window.clearTimeout(timer); timer = null }
  function invalidateRead() { sequence++; reading = null; loading.value = false }
  function invalidate(clear = false) { version++; invalidateRead(); clearTimer(); error.value = ''; if (clear) { result.value = null; pending.value = false } }
  function requireLatest() { pending.value = true }
  function reset(keepExecutionId = '') { invalidateRead(); if (!keepExecutionId || result.value?.executionId !== keepExecutionId) result.value = null; error.value = ''; pending.value = true }
  function matchesExecution(executionId: string) { return !options.executionId() || executionId === options.executionId() }
  function load(enforceCurrentExecution = true, showLoading = true): Promise<boolean> {
    const id = options.caseId()
    if (!available() || id === null) return Promise.resolve(false)
    if (reading?.current()) { if (showLoading) loading.value = true; return reading.promise }
    const valid = capture(), request = ++sequence, current = () => valid() && request === sequence, env = environment()
    const expectedExecution = enforceCurrentExecution ? options.executionId() || (!result.value?.final ? result.value?.executionId : '') : ''
    loading.value = showLoading; error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const next = readLatestCaseRuntime(await getExecutionResultLatestResolved({ source_type: 'page', target_type: 'ui_case', target_id: id, test_env: env, page: 1, pageSize: 1 }), id, env)
        if (!current() || (expectedExecution && (!next || next.executionId !== expectedExecution))) return false
        result.value = next; pending.value = false; return true
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "执行结果加载失败，请重试", false), error.value = '执行结果加载失败，请重试'); return false }
      finally { if (request === sequence) { loading.value = false; reading = null } }
    })
    reading = { current, promise }; return promise
  }
  function publish(next: CaseRuntimeResult, final: boolean) {
    if (next === result.value) return false
    invalidateRead(); error.value = ''; result.value = next
    if (final) pending.value = false
    options.updated(next, final)
    return true
  }
  function acceptFinal(value: unknown): boolean {
    if (!available() || options.caseId() === null) return false
    try {
      const next = readCaseRuntimeResult(value)
      if (String(next.id) !== String(options.caseId()) || String(next.testEnv) !== String(environment()) || !matchesExecution(next.executionId)) return false
      return publish(next, true)
    } catch { return false }
  }
  function acceptStep(value: unknown): boolean {
    const caseId = options.caseId()
    if (!available() || caseId === null) return false
    try {
      const step = readCaseRuntimeStep(value)
      if (step.detailId === null || !options.stepIds().some(id => String(id) === String(step.detailId)) || String(step.testEnv) !== String(environment()) || !matchesExecution(step.executionId)) return false
      return publish(mergeCaseRuntimeStep(result.value, step, caseId), false)
    } catch { return false }
  }
  function acceptNode(value: unknown): boolean {
    const caseId = options.caseId()
    if (!available() || caseId === null) return false
    try {
      const progress = readCaseNodeProgress(value)
      if (!progress.executionId || !matchesExecution(progress.executionId) || !options.stepIds().some(id => String(id) === String(progress.detailId))) return false
      let previous = result.value
      if (!previous && options.executionId() === progress.executionId) previous = { id: caseId, executionId: progress.executionId, testEnv: environment(), status: 3, final: false, cache: undefined, factoryCache: undefined, steps: [], evidence: Object.freeze({}) }
      const next = mergeCaseNodeProgress(previous, progress, caseId, environment())
      return next ? publish(next, false) : false
    } catch { return false }
  }
  function receive(event: Event) {
    if (!available()) return
    try {
      const message = uiCaseAssetObject((event as CustomEvent<unknown>).detail), data = uiCaseAssetObject(message.data)
      if (typeof data.func_name !== 'string' || !socketEvents.has(data.func_name)) return
      let accepted = false
      if (data.func_name === 'u_page_steps') accepted = acceptStep(data.func_args)
      else if (data.func_name === 'u_page_step_node_progress') accepted = acceptNode(data.func_args)
      else if (data.func_name === 'u_test_case') { accepted = acceptFinal(data.func_args); if (accepted) options.finished(result.value?.executionId ?? '') }
      else { const packet = uiCaseAssetObject(data.func_args); accepted = options.caseId() !== null && String(uiCaseAssetId(packet.id)) === String(options.caseId()) }
      if (!accepted) return
      clearTimer(); const current = capture()
      timer = window.setTimeout(() => { timer = null; if (current()) void options.refresh() }, 500)
    } catch { /* 非本页或不完整的Socket消息不改变当前结果。 */ }
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate(); else if (available()) void load(true, false) }
  watch(identity, () => { invalidate(true); if (available()) void load() }, { flush: 'sync' })
  watch(options.executionId, executionId => { reset(executionId); clearTimer() }, { flush: 'sync' })
  onMounted(() => { window.addEventListener('mango:websocket-message', receive); document.addEventListener('visibilitychange', visibilityChanged); void load() })
  onActivated(() => { active = true; if (available()) void load(true, false) })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(true); window.removeEventListener('mango:websocket-message', receive); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { result: computed(() => result.value), pending: computed(() => pending.value), loading, error, load, reset, requireLatest, acceptFinal, acceptStep, acceptNode }
}
