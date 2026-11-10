
import { reportLoadError } from '@/utils/load-error'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getUiCaseStepsDetailed } from '@/api/uitest/case-steps-detailed'
import { uiCaseAssetId, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import { mergeActiveCaseSteps, readCaseStepRows, type CaseStepRow } from '../step-list'

export function useCaseStepList(options: { caseId: () => UiCaseAssetId | null; running: () => boolean; loaded: (current: () => boolean) => void }) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const rows = shallowRef<CaseStepRow[]>([]), selectedId = ref<UiCaseAssetId | null>(null), loading = ref(false), error = ref('')
  const selected = computed(() => rows.value.find(row => selectedId.value !== null && String(row.id) === String(selectedId.value)) ?? null)
  let active = true, disposed = false, version = 0, sequence = 0
  let reading: { current: () => boolean; promise: Promise<boolean> } | null = null
  const identity = () => JSON.stringify([route.path, route.fullPath, options.caseId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  function capture() { const key = identity(), revision = version; return () => available() && key === identity() && revision === version }
  function invalidate(clear = false) { version++; sequence++; reading = null; loading.value = false; error.value = ''; if (clear) { rows.value = []; selectedId.value = null } }
  function select(id: UiCaseAssetId) { if (rows.value.some(row => String(row.id) === String(id))) selectedId.value = id }
  function replace(next: CaseStepRow[]) {
    rows.value = next
    if (!selected.value) selectedId.value = next[0]?.id ?? null
  }
  watch(rows, () => { if (!selected.value) selectedId.value = rows.value[0]?.id ?? null }, { flush: 'sync' })
  function load(showLoading = true, externalCurrent: () => boolean = () => true): Promise<boolean> {
    if (!available() || options.caseId() === null || !externalCurrent()) return Promise.resolve(false)
    const caseId = uiCaseAssetId(options.caseId())
    if (caseId === null) return Promise.resolve(false)
    if (reading?.current()) { if (showLoading) loading.value = true; return reading.promise }
    const valid = capture(), request = ++sequence, current = () => valid() && externalCurrent() && request === sequence
    loading.value = showLoading; error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const incoming = readCaseStepRows(await getUiCaseStepsDetailed(caseId), caseId)
        if (!current()) return false
        replace(options.running() ? mergeActiveCaseSteps(incoming, rows.value) : incoming)
        options.loaded(current)
        return true
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "执行步骤加载失败，请重试", false), error.value = '执行步骤加载失败，请重试'); return false }
      finally { if (request === sequence) { loading.value = false; reading = null } }
    })
    reading = { current, promise }; return promise
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate(); else if (available()) void load(false) }
  watch(identity, () => { invalidate(true); if (available()) void load() }, { flush: 'sync' })
  onMounted(() => { document.addEventListener('visibilitychange', visibilityChanged); void load() })
  onActivated(() => { active = true; if (available()) void load(false) })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(true); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { rows: computed(() => rows.value), selected, loading, error, select, replace, load, invalidate, capture }
}
