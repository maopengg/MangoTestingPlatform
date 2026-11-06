import { onActivated, onBeforeUnmount, onDeactivated, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createPagePolling, type PollingContext } from '@/utils/page-polling'

export { isPendingExecution } from '@/utils/page-polling'
export type { PollingContext } from '@/utils/page-polling'

export function usePagePolling(
  refresh: (context: PollingContext) => unknown | Promise<unknown>,
  onPause?: () => void,
) {
  const route = useRoute()
  const path = route.path
  let active = true
  const available = () => active && route.path === path && document.visibilityState === 'visible'
  const polling = createPagePolling(refresh, available)
  function sync() {
    if (available()) polling.resume()
    else { polling.pause(); onPause?.() }
  }
  onMounted(() => document.addEventListener('visibilitychange', sync))
  onActivated(() => { active = true; sync() })
  onDeactivated(() => { active = false; sync() })
  watch(() => route.path, sync, { flush: 'sync' })
  onBeforeUnmount(() => {
    active = false
    polling.dispose()
    onPause?.()
    document.removeEventListener('visibilitychange', sync)
  })
  return { ...polling, isAvailable: available }
}
