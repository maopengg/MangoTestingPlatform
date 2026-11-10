import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import type { PollingContext } from '@/hooks/use-page-polling'
import { readRunRouteId } from '../records'
import type { RunContext, RunIdentity } from '../types'

export function useRunContext(options: {
  onInvalidate: (clear: boolean) => void
  onPause: () => void
  onResume: (silent: boolean) => void
}) {
  const route = useRoute(), user = useUserStore()
  const id = computed(() => readRunRouteId(route.query.id))
  let epoch = 0, active = true, mounted = false, disposed = false, needsInitialLoad = true
  const identity = (): RunIdentity => ({ userId: user.userId, roleId: user.roleId, token: user.token, environment: user.selected_environment })
  const available = () => !disposed && active && route.path === '/perf/run/details' && id.value !== null && document.visibilityState === 'visible'
  function capture(parent?: PollingContext): RunContext | null {
    if (!available() || (parent && !parent.isCurrent())) return null
    const snapshot = epoch, runId = id.value!
    return { id: runId, epoch: snapshot, identity: identity(), isCurrent: () => available() && snapshot === epoch && (!parent || parent.isCurrent()) }
  }
  function invalidate(clear: boolean) {
    epoch++
    if (clear) needsInitialLoad = true
    options.onInvalidate(clear)
    options.onPause()
  }
  function resume(silent: boolean) {
    if (!available()) return
    const quiet = silent && !needsInitialLoad
    needsInitialLoad = false
    options.onResume(quiet)
  }
  function visibilityChanged() {
    if (document.visibilityState !== 'visible') invalidate(false)
    else resume(true)
  }
  watch(() => [route.path, route.fullPath, route.query.id, user.userId, user.roleId, user.token, user.selected_environment], () => {
    invalidate(true)
    if (mounted) resume(false)
  }, { flush: 'sync' })
  onMounted(() => {
    mounted = true
    document.addEventListener('visibilitychange', visibilityChanged)
    resume(false)
  })
  onDeactivated(() => { active = false; invalidate(false) })
  onActivated(() => { if (!active) { active = true; resume(true) } })
  onBeforeUnmount(() => {
    disposed = true
    active = false
    invalidate(true)
    document.removeEventListener('visibilitychange', visibilityChanged)
  })
  return { id, capture, available, identity }
}
