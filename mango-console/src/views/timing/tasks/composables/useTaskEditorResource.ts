
import { reportLoadError } from '@/utils/load-error'
import { ref, shallowRef } from 'vue'
import { taskEditorResponse } from '../task-editor-records'

// 单项元数据独立加载；窗口、身份和产品的失效边界由调用方提供。
export function useTaskEditorResource<T>(capture: () => () => boolean, message: string) {
  const value = shallowRef<T | null>(null), loading = ref(false), error = ref('')
  let version = 0
  function clear() { version++; value.value = null; loading.value = false; error.value = '' }
  async function load(request: () => Promise<unknown>, parse: (data: unknown) => T): Promise<boolean> {
    const currentVersion = ++version, validContext = capture()
    const current = () => currentVersion === version && validContext()
    loading.value = true; error.value = ''
    try {
      const parsed = parse(taskEditorResponse(await request()))
      if (!current()) return false
      value.value = parsed
      return true
    } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), error.value = message); return false }
    finally { if (current()) loading.value = false }
  }
  return { value, loading, error, clear, load }
}
