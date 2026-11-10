
import { reportLoadError } from '@/utils/load-error'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getUiCase, putUiCase } from '@/api/uitest/case'
import { cloneLosslessJson } from '@/utils/lossless-json'
import { requiredUiCaseAssetId, uiCaseAssetResponse } from '@/components/business/ui-case-step-create'
import { emptyUiCaseConfiguration, readUiCaseConfiguration, readUiCaseConfigurationRecord, uiCaseConfigurationPayload, uiCaseConfigurationSignature, type UiCaseConfiguration, type UiCaseConfigurationMode, type UiCaseConfigurationRecord } from '../case-configuration'

export function useUiCaseConfiguration(caseId: () => unknown) {
  const record = ref<UiCaseConfigurationRecord | null>(null), draft: UiCaseConfiguration = reactive(emptyUiCaseConfiguration())
  const loading = ref(false), loadError = ref(''), saving = ref(false), saveError = ref('')
  const baseline = ref<UiCaseConfiguration | null>(null)
  const pendingOperationRows = shallowRef(new Set<object>())
  const pendingOperations = computed(() => [...draft.front_sql, ...draft.posterior_sql].some(item => pendingOperationRows.value.has(item)))
  const dirty = computed(() => pendingOperations.value || baseline.value !== null && uiCaseConfigurationSignature(draft) !== uiCaseConfigurationSignature(baseline.value))
  function operationDraftChanged(item: unknown, pending: boolean) {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return
    const rows = new Set(pendingOperationRows.value)
    if (pending && [...draft.front_sql, ...draft.posterior_sql].some(row => row === item)) rows.add(item)
    else rows.delete(item)
    pendingOperationRows.value = rows
  }
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  let active = true, disposed = false, version = 0, readVersion = 0
  let reading: { current: () => boolean; promise: Promise<boolean> } | null = null
  let writing: { current: () => boolean; promise: Promise<boolean> } | null = null
  const queue: Array<{ mode: UiCaseConfigurationMode; source: UiCaseConfigurationRecord; payload: ReturnType<typeof uiCaseConfigurationPayload>; saved: UiCaseConfiguration }> = []
  const identity = () => JSON.stringify([route.path, route.fullPath, caseId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  function capture() { const key = identity(), sequence = version; return () => available() && key === identity() && sequence === version }
  function invalidate(clear = false) {
    version++; readVersion++; reading = null; loading.value = false; queue.length = 0; loadError.value = ''; saveError.value = ''
    if (clear) { record.value = null; baseline.value = null; pendingOperationRows.value = new Set(); Object.assign(draft, emptyUiCaseConfiguration()) }
  }
  function load(showLoading = true, externalCurrent: () => boolean = () => true): Promise<boolean> {
    if (!available()) return Promise.resolve(false)
    if (reading?.current()) { if (showLoading) loading.value = true; return reading.promise }
    let id: number | string
    try { id = requiredUiCaseAssetId(caseId()) } catch (loadFailure0) { (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = '未找到有效用例ID'); return Promise.resolve(false) }
    const valid = capture(), sequence = ++readVersion
    const current = () => valid() && sequence === readVersion && externalCurrent()
    loading.value = showLoading; loadError.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const value = readUiCaseConfigurationRecord(await getUiCase({ id, page: 1, pageSize: 1 }), id)
        if (!current()) return false
        record.value = value
        if (!dirty.value && !writing?.current()) {
          Object.assign(draft, readUiCaseConfiguration(value)); baseline.value = readUiCaseConfiguration(value)
        }
        return true
      } catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, "用例配置加载失败，请重试", false), loadError.value = '用例配置加载失败，请重试'); return false }
      finally { if (sequence === readVersion) { loading.value = false; reading = null } }
    })
    reading = { current, promise }; return promise
  }
  function save(mode: UiCaseConfigurationMode = 'all'): Promise<boolean> {
    if (!available() || !record.value || !baseline.value) return Promise.resolve(false)
    if (mode === 'all' && pendingOperations.value) { saveError.value = '数据库操作存在未提交的内容，请检查 JSON 格式并移出输入框后重试'; return Promise.resolve(false) }
    if (writing && !writing.current()) return Promise.resolve(false)
    try {
      const source = cloneLosslessJson(record.value), saved = readUiCaseConfiguration(draft)
      queue.push({ mode, source, saved, payload: uiCaseConfigurationPayload(source, saved, mode) })
    } catch { saveError.value = '用例配置格式异常，请检查后重试'; return Promise.resolve(false) }
    if (writing) return writing.promise
    const valid = capture()
    saving.value = true; saveError.value = ''; readVersion++; reading = null; loading.value = false
    const promise = Promise.resolve().then(async () => {
      let success = true, wrote = false
      try {
        while (queue.length && valid() && record.value && baseline.value) {
          const task = queue.shift()
          if (!task) break
          const { mode: next, source, payload: snapshot, saved } = task
          if (uiCaseConfigurationSignature(snapshot) === uiCaseConfigurationSignature(uiCaseConfigurationPayload(source, baseline.value, next))) continue
          uiCaseAssetResponse(await putUiCase(snapshot))
          if (!valid()) return false
          wrote = true; readVersion++; reading = null; loading.value = false
          if (next === 'all') baseline.value = cloneLosslessJson(saved)
          else if (baseline.value) { baseline.value.front_public = [...saved.front_public]; baseline.value.front_auth_config = [...saved.front_auth_config] }
          record.value = { ...source, ...cloneLosslessJson(snapshot) }
        }
        if (!valid()) return false
        if (wrote) Message.success('用例配置已保存')
      } catch { if (valid()) saveError.value = '用例配置保存失败，请重试'; success = false }
      finally { queue.length = 0; saving.value = false; writing = null }
      return success
    })
    writing = { current: valid, promise }; return promise
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate(); else if (available()) void load(false) }
  watch(identity, () => { invalidate(true); if (available()) void load(true) }, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onActivated(() => { active = true; if (available()) void load(false) })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(true); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { record, draft, loading, loadError, saving, saveError, dirty, load, save, operationDraftChanged }
}
