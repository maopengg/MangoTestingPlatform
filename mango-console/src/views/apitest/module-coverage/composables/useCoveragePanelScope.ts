import { onBeforeUnmount, onDeactivated, watch, type Ref } from 'vue'

// 每次打开及关闭都改变会话，分页或嵌套请求只接受当前窗口的结果。
export function useCoveragePanelScope(visible: Ref<boolean>, reset: () => void) {
  let session = 0
  const begin = () => ++session
  const current = (token: number) => visible.value && token === session
  function invalidate() {
    ++session
    reset()
  }
  function close() {
    visible.value = false
    invalidate()
  }
  watch(
    visible,
    (value) => {
      if (!value) invalidate()
    },
    { flush: 'sync' }
  )
  onDeactivated(close)
  onBeforeUnmount(close)
  return { begin, current, close }
}
