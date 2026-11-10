import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { deleteUiCaseStepsDetailed, getUiCaseStepsRefreshCacheData, putUiCasePutCaseSort } from '@/api/uitest/case-steps-detailed'
import { requiredUiCaseAssetId, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import { caseStepIds, caseStepSyncMessage, moveCaseStep, type CaseStepStructureChange } from '../step-structure'

export function useCaseStepStructure(options: {
  caseId: () => unknown
  stepIds: () => unknown
  committed: (change: CaseStepStructureChange) => void
}) {
  const pending = ref<{ kind: 'delete' | 'sync' | 'sort'; caseId: UiCaseAssetId; recordId: UiCaseAssetId | null } | null>(null)
  const error = ref('')
  const draggingId = ref<UiCaseAssetId | null>(null)
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  let active = true, disposed = false, version = 0, closeConfirmation: (() => void) | null = null
  let drag: { id: UiCaseAssetId; valid: () => boolean } | null = null
  const identity = () => JSON.stringify([route.path, route.fullPath, options.caseId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  function capture() { const key = identity(), sequence = version; return () => available() && key === identity() && sequence === version }
  function cancelDrag() { drag = null; draggingId.value = null }
  function invalidate() { version++; closeConfirmation?.(); cancelDrag(); error.value = '' }
  function snapshot(record: unknown) {
    const caseId = requiredUiCaseAssetId(options.caseId()), recordId = requiredUiCaseAssetId(record)
    if (!caseStepIds(options.stepIds()).some(id => String(id) === String(recordId))) throw Error('Unknown case step')
    return { caseId, recordId }
  }
  function confirm(kind: 'delete' | 'sync', record: unknown): boolean {
    if (!available() || pending.value || closeConfirmation) return false
    let target: ReturnType<typeof snapshot>
    try { target = snapshot(record) }
    catch { error.value = '步骤数据异常，请重新加载核对'; return false }
    const valid = capture()
    let open = true
    const close = () => { if (!open) return; open = false; closeConfirmation = null; shell.close() }
    const shell = Modal.confirm({
      title: kind === 'delete' ? '删除步骤' : '同步页面步骤',
      content: kind === 'delete' ? '是否要删除此步骤？' : '仅同步当前页面步骤中发生变化的节点，未变化节点及其 Case 入参会保留。是否继续？',
      cancelText: '取消', okText: kind === 'delete' ? '删除' : '同步',
      okButtonProps: kind === 'delete' ? { status: 'danger' } : {},
      onCancel: close,
      onBeforeOk: async () => {
        if (!open || !valid() || pending.value) return false
        try { snapshot(target.recordId) }
        catch { error.value = '步骤已变化，请重新加载核对'; close(); return false }
        pending.value = { ...target, kind }; error.value = ''
        try {
          const response: unknown = kind === 'delete'
            ? await deleteUiCaseStepsDetailed(target.recordId, target.caseId)
            : await getUiCaseStepsRefreshCacheData(target.recordId)
          uiCaseAssetResponse(response)
          if (!valid()) return false
          try { options.committed({ ...target, kind }) }
          catch { error.value = '操作已完成，页面更新失败，请重新加载核对'; close(); return true }
          if (open) { Message.success(kind === 'delete' ? '删除成功' : caseStepSyncMessage(response, target.recordId)); close() }
          return true
        } catch {
          if (valid()) error.value = kind === 'delete' ? '步骤删除失败，请重试' : '步骤同步失败，请重试'
          return false
        } finally { pending.value = null }
      },
    })
    closeConfirmation = close
    return true
  }
  async function move(source: unknown, target: unknown): Promise<boolean> {
    if (!available() || pending.value || closeConfirmation) return false
    let caseId: UiCaseAssetId, order: UiCaseAssetId[]
    try { caseId = requiredUiCaseAssetId(options.caseId()); order = moveCaseStep(caseStepIds(options.stepIds()), requiredUiCaseAssetId(source), requiredUiCaseAssetId(target)) }
    catch { error.value = '步骤顺序已变化，请重新拖动重试'; return false }
    const valid = capture()
    pending.value = { kind: 'sort', caseId, recordId: null }; error.value = ''
    try {
      uiCaseAssetResponse(await putUiCasePutCaseSort(order.map((id, case_sort) => ({ id, case_sort }))))
      if (!valid()) return false
      try { options.committed({ kind: 'sort', caseId, order }) }
      catch { error.value = '排序已保存，页面更新失败，请重新加载核对'; return true }
      Message.success('步骤顺序已保存'); return true
    } catch {
      if (valid()) error.value = '排序保存失败，请重新拖动重试'
      return false
    } finally { pending.value = null }
  }
  function beginDrag(record: unknown): boolean {
    cancelDrag()
    if (!available() || pending.value || closeConfirmation) return false
    try { const target = snapshot(record); drag = { id: target.recordId, valid: capture() }; draggingId.value = target.recordId; return true }
    catch { error.value = '步骤数据异常，请重新加载核对'; return false }
  }
  function drop(target: unknown): Promise<boolean> {
    const source = drag; cancelDrag()
    if (!source || !source.valid() || String(source.id) === String(target)) return Promise.resolve(false)
    return move(source.id, target)
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate() }
  watch(identity, invalidate, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { pending, error, draggingId, beginDrag, cancelDrag, drop, remove: (id: unknown) => confirm('delete', id), sync: (id: unknown) => confirm('sync', id), move, invalidate }
}
