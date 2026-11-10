import { onActivated, onDeactivated, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'

export function useEvaluationScope(
  dependencies: () => unknown[],
  reset: () => void,
  resume: () => void
) {
  const route = useRoute(),
    user = useUserStore(),
    path = route.path
  let active = true,
    version = 0
  const isActive = () => active && route.path === path
  function invalidate() {
    ++version
    reset()
  }
  function start() {
    invalidate()
    if (isActive()) resume()
  }
  function stop() {
    active = false
    invalidate()
  }
  watch(
    () => [
      route.path,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
      ...dependencies(),
    ],
    start,
    { flush: 'sync' }
  )
  onDeactivated(stop)
  onBeforeUnmount(stop)
  onActivated(() => {
    if (!active) {
      active = true
      start()
    }
  })
  return {
    isActive,
    start,
    snapshot: () => version,
    current: (value: number) => isActive() && version === value,
  }
}
