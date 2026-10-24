import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'

export function useApiCaseExecution(refresh: () => void | Promise<unknown>) {
  const caseRunning = ref(false)
  const caseRequestPending = ref(false)
  const debugRunningStepId = ref<number | string | null>(null)
  const debugRequestPending = ref(false)
  const lastTraceId = ref('')
  const caseRunRefreshTimer = ref<ReturnType<typeof window.setInterval> | null>(null)
  const caseRunLoadingTimer = ref<ReturnType<typeof window.setTimeout> | null>(null)
  const debugRunLoadingTimer = ref<ReturnType<typeof window.setTimeout> | null>(null)

  function startCaseRunRefresh() {
    if (caseRunRefreshTimer.value) return
    caseRunRefreshTimer.value = window.setInterval(() => refresh(), 5000)
  }

  function stopCaseRunRefresh() {
    if (!caseRunRefreshTimer.value) return
    window.clearInterval(caseRunRefreshTimer.value)
    caseRunRefreshTimer.value = null
  }

  function startCaseRunLoadingLimit() {
    stopCaseRunLoadingLimit()
    caseRunLoadingTimer.value = window.setTimeout(() => {
      caseRunning.value = false
      caseRunLoadingTimer.value = null
      Message.info('执行时间超过30秒，已刷新当前结果；用例仍在后台继续执行')
      refresh()
    }, 30000)
  }

  function stopCaseRunLoadingLimit() {
    if (!caseRunLoadingTimer.value) return
    window.clearTimeout(caseRunLoadingTimer.value)
    caseRunLoadingTimer.value = null
  }

  function startDebugRunLoadingLimit() {
    stopDebugRunLoadingLimit()
    debugRunLoadingTimer.value = window.setTimeout(() => {
      debugRunningStepId.value = null
      debugRunLoadingTimer.value = null
      Message.info('调试时间超过30秒，已刷新当前结果；步骤仍在后台继续执行')
      refresh()
    }, 30000)
  }

  function stopDebugRunLoadingLimit() {
    if (!debugRunLoadingTimer.value) return
    window.clearTimeout(debugRunLoadingTimer.value)
    debugRunLoadingTimer.value = null
  }

  function disposeExecutionTimers() {
    stopCaseRunRefresh()
    stopCaseRunLoadingLimit()
    stopDebugRunLoadingLimit()
  }

  return {
    caseRunning,
    caseRequestPending,
    debugRunningStepId,
    debugRequestPending,
    lastTraceId,
    caseRunRefreshTimer,
    startCaseRunRefresh,
    stopCaseRunRefresh,
    startCaseRunLoadingLimit,
    stopCaseRunLoadingLimit,
    startDebugRunLoadingLimit,
    stopDebugRunLoadingLimit,
    disposeExecutionTimers,
  }
}
