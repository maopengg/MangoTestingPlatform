import { onActivated, onBeforeUnmount, onDeactivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
export function useActuatorScope(reset: () => void, resume: () => void = () => {}) {
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
  function stop() {
    active = false
    invalidate()
  }
  onDeactivated(stop)
  onBeforeUnmount(stop)
  onActivated(() => {
    if (!active) {
      active = true
      if (isActive()) resume()
    }
  })
  watch(
    () => [route.path, user.userId, user.roleId, user.token, user.selected_environment],
    () => {
      invalidate()
      if (isActive()) resume()
    },
    { flush: 'sync' }
  )
  return {
    isActive,
    snapshot: () => version,
    current: (value: number) => isActive() && value === version,
  }
}
