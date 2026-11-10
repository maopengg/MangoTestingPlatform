
import { reportLoadError } from '@/utils/load-error'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getUiSteps } from '@/api/uitest/page-steps'
import { uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import { readCasePageStep, type CasePageStep, type CaseStepRow } from '../step-list'

interface StepDetailTarget { pageStepsId: UiCaseAssetId; pageId: UiCaseAssetId; pageType: number }
export function useCaseStepDetail(options: { caseId: () => UiCaseAssetId | null; rows: () => readonly CaseStepRow[] }) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), path = route.path
  const visible = ref(false), target = shallowRef<StepDetailTarget | null>(null), loading = ref(false), error = ref('')
  let active = true, disposed = false, version = 0, selected: UiCaseAssetId | null = null, requestedStepId: UiCaseAssetId | null = null
  let reading: { current: () => boolean; promise: Promise<boolean> } | null = null
  const identity = () => JSON.stringify([route.path, route.fullPath, options.caseId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === path && document.visibilityState === 'visible' && options.caseId() !== null
  function clear() { version++; visible.value = false; selected = null; requestedStepId = null; target.value = null; error.value = ''; loading.value = false; reading = null }
  function detail(step: CasePageStep | null): StepDetailTarget {
    if (!step?.page || step.project_product?.ui_client_type == null) throw Error('Incomplete page step')
    return { pageStepsId: step.id, pageId: step.page.id, pageType: step.project_product.ui_client_type }
  }
  function load(): Promise<boolean> {
    if (!available() || !visible.value || selected === null) return Promise.resolve(false)
    if (reading?.current()) return reading.promise
    const row = options.rows().find(row => String(row.id) === String(selected)), step = row?.page_step
    if (!step) { error.value = '未找到页面步骤，请刷新用例步骤'; return Promise.resolve(false) }
    const id = step.id, recordId = row.id, key = identity(), revision = ++version
    requestedStepId = id
    const current = () => available() && visible.value && key === identity() && revision === version && String(selected) === String(recordId) && options.rows().some(row => String(row.id) === String(recordId) && String(row.page_step?.id) === String(id))
    loading.value = true; error.value = ''; target.value = null
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        let complete = step
        if (!step.page || step.project_product?.ui_client_type == null) {
          const rows = uiCaseAssetResponse(await getUiSteps({ id }))
          if (!current()) return false
          if (!Array.isArray(rows)) throw Error('Invalid page steps')
          const parsed = rows.map(readCasePageStep).filter((row): row is CasePageStep => row !== null)
          const match = parsed.find(row => String(row.id) === String(id))
          if (!match) throw Error('Missing requested page step')
          complete = match
        }
        if (!current()) return false
        target.value = detail(complete); return true
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "页面步骤信息加载失败，请重试", false), error.value = '页面步骤信息加载失败，请重试'); return false }
      finally { if (revision === version) { loading.value = false; reading = null } }
    })
    reading = { current, promise }; return promise
  }
  function open(recordId: UiCaseAssetId): Promise<boolean> {
    if (!available()) return Promise.resolve(false)
    if (!visible.value || String(selected) !== String(recordId)) { clear(); selected = recordId; visible.value = true }
    return load()
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') clear() }
  watch(identity, clear, { flush: 'sync' })
  watch(() => options.rows().map(row => [row.id, row.page_step?.id]), () => {
    if (selected !== null && !options.rows().some(row => String(row.id) === String(selected) && (requestedStepId === null || String(row.page_step?.id) === String(requestedStepId)))) clear()
  }, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; clear() })
  onBeforeUnmount(() => { disposed = true; clear(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { visible: computed({ get: () => visible.value, set: value => { if (!value) clear() } }), target: computed(() => target.value), loading, error, open, close: clear, retry: load }
}
