
import { reportLoadError, runLoadRequest } from '@/utils/load-error'
import { ref } from 'vue'
import { getUiCase } from '@/api/uitest/case'
import { getUserName } from '@/api/user/user'
import { readUiCaseList, readCaseUsers, type CaseListQuery, type UiCaseRow, type CaseUserOption } from '../case-list-records'
export function useUiCaseList(options: { available: () => boolean; capture: () => () => boolean; query: () => CaseListQuery; total: (value: number) => void; page: (value: number) => void; loaded: () => void }) {
  const rows = ref<UiCaseRow[]>([]), loading = ref(false), error = ref('')
  const users = ref<CaseUserOption[]>([]), usersLoading = ref(false), usersError = ref('')
  let sequence = 0, userSequence = 0
  let reading: { key: string; current: () => boolean; promise: Promise<boolean> } | null = null
  function invalidateRows(clear = false) { sequence++; reading = null; loading.value = false; if (clear) { rows.value = []; error.value = ''; options.total(0) } }
  function invalidate(clear = false) { invalidateRows(clear); userSequence++; usersLoading.value = false; if (clear) { users.value = []; usersError.value = '' } }
  function load(showLoading = true, externalCurrent: () => boolean = () => true): Promise<boolean> {
    if (!options.available()) return Promise.resolve(false)
    const query = options.query(), key = JSON.stringify(query)
    if (reading?.key === key && reading.current()) { if (showLoading) loading.value = true; return reading.promise }
    const valid = options.capture(), request = ++sequence, current = () => valid() && request === sequence && key === JSON.stringify(options.query()) && externalCurrent()
    loading.value = showLoading; error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const result = readUiCaseList(await runLoadRequest(!showLoading, () => getUiCase({ ...query })))
        if (!current()) return false
        const lastPage = Math.max(1, Math.ceil(result.total / query.pageSize))
        if (query.page > lastPage) { options.page(lastPage); return await load(showLoading, externalCurrent) }
        rows.value = result.rows; options.total(result.total); options.loaded(); return true
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "用例列表加载失败，请重试", false), error.value = '用例列表加载失败，请重试'); return false }
      finally { if (request === sequence) { loading.value = false; reading = null } }
    })
    reading = { key, current, promise }; return promise
  }
  async function loadUsers(): Promise<boolean> {
    if (!options.available()) return false
    const valid = options.capture(), request = ++userSequence, current = () => valid() && request === userSequence
    usersLoading.value = true; usersError.value = ''
    try { const result = readCaseUsers(await getUserName()); if (!current()) return false; users.value = result; return true }
    catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, "用户选项加载失败，请重试", false), usersError.value = '用户选项加载失败，请重试'); return false }
    finally { if (request === userSequence) usersLoading.value = false }
  }
  return { rows, loading, error, users, usersLoading, usersError, load, loadUsers, invalidate, invalidateRows }
}
