import { onActivated, onBeforeUnmount, onDeactivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'

export function useProductPageScope(
  context: () => unknown[],
  reset: () => void,
  resume: () => void = () => {}
) {
  const route = useRoute(),
    user = useUserStore(),
    ownerPath = route.path
  let active = true,
    version = 0
  const isActive = () => active && route.path === ownerPath
  function invalidate() {
    ++version
    reset()
  }
  function deactivate() {
    active = false
    invalidate()
  }
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!active) {
      active = true
      if (isActive()) resume()
    }
  })
  watch(
    () => [route.path, user.token, user.roleId, ...context()],
    () => {
      invalidate()
      if (isActive()) resume()
    },
    { flush: 'sync' }
  )
  return {
    snapshot: () => version,
    current: (snapshot: number) => isActive() && snapshot === version,
    isActive,
  }
}
