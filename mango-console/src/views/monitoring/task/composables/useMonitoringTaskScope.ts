import { onActivated, onBeforeUnmount, onDeactivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'

export function useMonitoringTaskScope(invalidate: () => void, resume: () => void = () => {}) {
  const route = useRoute(), user = useUserStore()
  let active = true, version = 0
  const available = () => active && route.path === '/monitoring/task/index'
  const reset = () => { ++version; invalidate() }
  const suspend = () => { active = false; reset() }
  watch(() => [route.fullPath, user.userId, user.roleId, user.token, user.selected_environment], () => {
    reset()
    if (available()) resume()
  }, { flush: 'sync' })
  onDeactivated(suspend)
  onBeforeUnmount(suspend)
  onActivated(() => { if (!active) { active = true; if (available()) resume() } })
  return {
    available, snapshot: () => version, current: (value: number) => available() && value === version,
    identity: () => JSON.stringify([user.userId, user.roleId, user.token, user.selected_environment]),
  }
}
