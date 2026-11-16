import { onActivated, onBeforeUnmount, onDeactivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'

// 同一连接可能经历 A→B→A；身份、缓存停用也必须使旧响应失效。
export function useSourceScope(reset: () => void, resume: () => void = () => {}) {
  const route = useRoute()
  const user = useUserStore()
  const ownerPath = route.path
  let active = true
  let version = 0
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
    [() => route.path, () => user.token, () => user.roleId],
    () => {
      invalidate()
      if (isActive()) resume()
    },
    { flush: 'sync' }
  )
  return {
    current: (snapshot: number) => isActive() && snapshot === version,
    snapshot: () => version,
    isActive,
    invalidate,
  }
}
