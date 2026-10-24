import { nextTick, ref } from 'vue'
import { waitForMinimumLoading } from '@/utils/minimum-loading'

export function useUiLiveWorkbench(canOpen: () => boolean | Promise<boolean>) {
  const visible = ref(false)
  const opening = ref(false)
  const sectionRef = ref<HTMLElement | null>(null)

  async function open() {
    if (opening.value || !(await canOpen())) return false
    opening.value = true
    const startedAt = Date.now()
    try {
      visible.value = true
      await nextTick()
      sectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return true
    } finally {
      await waitForMinimumLoading(startedAt)
      opening.value = false
    }
  }

  function close() {
    visible.value = false
  }

  function toggle() {
    if (opening.value) return
    if (visible.value) close()
    else void open()
  }

  return { visible, opening, sectionRef, open, close, toggle }
}
