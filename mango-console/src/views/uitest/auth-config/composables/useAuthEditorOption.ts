
import { reportLoadError } from '@/utils/load-error'
import { ref, shallowRef } from 'vue'
import { useLatestRequest } from '@/hooks/use-latest-request'
import { readUiAuthOptions, uiAuthResponse, type UiAuthOption } from '../auth-editor-records'

export function useAuthEditorOption(capture: () => () => boolean, message: string) {
  const options = shallowRef<UiAuthOption[]>([]), loading = ref(false), error = ref('')
  const request = useLatestRequest()
  function clear() { request.invalidateRequests(); options.value = []; loading.value = false; error.value = '' }
  async function load(fetch: () => Promise<unknown>) {
    const id = request.beginRequest(), valid = capture(), current = () => request.isLatestRequest(id) && valid()
    loading.value = true; error.value = ''
    try { const items = readUiAuthOptions(uiAuthResponse(await fetch())); if (current()) options.value = items }
    catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), error.value = message) }
    finally { if (current()) loading.value = false }
  }
  return { options, loading, error, clear, load }
}
