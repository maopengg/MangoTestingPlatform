
import { reportLoadError } from '@/utils/load-error'
import { ref } from 'vue'
import { getUiAuthConfig } from '@/api/uitest/auth-config'
import { readUiAuthList, type UiAuthListQuery, type UiAuthListRecord } from '../auth-list-records'
import type { UiAuthId } from '../auth-editor-records'

interface Pagination { page: number; setTotalSize: (total: number) => void }
export function useAuthList(context: { available: () => boolean; capture: () => () => boolean; query: () => UiAuthListQuery; pagination: Pagination }) {
  const rows = ref<UiAuthListRecord[]>([]), loading = ref(false), error = ref('')
  let version = 0
  let inFlight: { key: string; current: () => boolean; promise: Promise<boolean> } | null = null
  function invalidate(clear = false) {
    version++; inFlight = null; loading.value = false
    if (clear) { rows.value = []; error.value = ''; context.pagination.setTotalSize(0) }
  }
  function updateStatus(id: UiAuthId, status: 0 | 1) {
    invalidate()
    rows.value = rows.value.map(row => String(row.id) === String(id) ? { ...row, status } : row)
  }
  function load(showLoading = true): Promise<boolean> {
    if (!context.available()) { loading.value = false; return Promise.resolve(false) }
    const query = context.query(), key = JSON.stringify(query)
    if (inFlight?.key === key && inFlight.current()) { if (showLoading) loading.value = true; return inFlight.promise }
    const sequence = ++version, valid = context.capture()
    const current = () => context.available() && valid() && version === sequence && key === JSON.stringify(context.query())
    loading.value = showLoading; error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const result = readUiAuthList(await getUiAuthConfig(query))
        if (!current()) return false
        const lastPage = Math.max(1, Math.ceil(result.total / query.pageSize))
        if (query.page > lastPage) { context.pagination.page = lastPage; return await load(showLoading) }
        rows.value = result.rows; context.pagination.setTotalSize(result.total); return true
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "授权列表加载失败，请重试", false), error.value = '授权列表加载失败，请重试'); return false }
      finally { if (sequence === version) { loading.value = false; inFlight = null } }
    })
    inFlight = { key, current, promise }
    return promise
  }
  return { rows, loading, error, load, invalidate, updateStatus }
}
