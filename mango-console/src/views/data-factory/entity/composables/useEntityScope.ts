import { onActivated, onBeforeUnmount, onDeactivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'

export function useEntityScope(reset: () => void, resume: () => void = () => {}) {
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
