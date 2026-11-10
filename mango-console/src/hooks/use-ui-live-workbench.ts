import { nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref } from 'vue'
import { waitForMinimumLoading } from '@/utils/minimum-loading'

export function useUiLiveWorkbench(canOpen: () => boolean | Promise<boolean>) {
  const visible = ref(false)
  const opening = ref(false)
  const sectionRef = ref<HTMLElement | null>(null)
  let active = true, disposed = false, version = 0
  const available = () => !disposed && active && document.visibilityState === 'visible'

  async function open() {
    if (opening.value || !available()) return false
    opening.value = true
    const epoch = version
    const startedAt = Date.now()
    try {
      if (!(await canOpen()) || !available() || epoch !== version) return false
      visible.value = true
      await nextTick()
      if (!available() || epoch !== version) return false
      sectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return true
    } catch {
      return false
    } finally {
      await waitForMinimumLoading(startedAt)
      opening.value = false
    }
  }

  function close() {
    version++
    visible.value = false
  }
  function visibilityChanged() { if (!available()) close() }
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; close() })
  onBeforeUnmount(() => { disposed = true; close(); document.removeEventListener('visibilitychange', visibilityChanged) })

  function toggle() {
    if (opening.value) return
    if (visible.value) close()
    else void open()
  }

  return { visible, opening, sectionRef, open, close, toggle }
}
