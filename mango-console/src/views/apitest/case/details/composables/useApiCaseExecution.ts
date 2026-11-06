import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { usePagePolling, type PollingContext } from '@/hooks/use-page-polling'

export function useApiCaseExecution(refresh: (context?: PollingContext) => void | Promise<unknown>) {
  const caseRunning = ref(false)
  const caseRequestPending = ref(false)
  const debugRunningStepId = ref<number | string | null>(null)
  const debugRequestPending = ref(false)
  const lastTraceId = ref('')
  const caseRunRefreshActive = ref(false)
  const polling = usePagePolling(context => refresh(context))
  const caseRunLoadingTimer = ref<ReturnType<typeof window.setTimeout> | null>(null)
  const debugRunLoadingTimer = ref<ReturnType<typeof window.setTimeout> | null>(null)

  function startCaseRunRefresh() {
    caseRunRefreshActive.value = true
    polling.start()
  }

  function stopCaseRunRefresh() {
    caseRunRefreshActive.value = false
    polling.stop()
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
    caseRunRefreshActive,
    startCaseRunRefresh,
    stopCaseRunRefresh,
    startCaseRunLoadingLimit,
    stopCaseRunLoadingLimit,
    startDebugRunLoadingLimit,
    stopDebugRunLoadingLimit,
    disposeExecutionTimers,
  }
}
