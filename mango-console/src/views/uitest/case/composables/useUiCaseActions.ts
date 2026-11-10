import { ref } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { deleteUiCase, getUiCaseRun, postUiCaseCopy, putUiCasePublication, postUiRunCaseBatch } from '@/api/uitest/case'
import { requiredUiCaseAssetId, uiCaseAssetId, uiCaseAssetResponse } from '@/components/business/ui-case-step-create'
import type { CaseId, PublicationStatus, UiCaseRow } from '../case-list-records'
type Action = 'delete' | 'copy' | 'run' | 'batch-run' | 'publication'
export function useUiCaseActions(options: {
  available: () => boolean; capture: () => () => boolean; environment: () => unknown; rows: () => readonly UiCaseRow[]
  filterKey: () => string; beforeWrite: () => void; committed: (kind: Action, ids: CaseId[], target?: PublicationStatus) => Promise<void>
}) {
  const pending = ref<{ kind: Action; ids: CaseId[] } | null>(null), error = ref('')
  let confirmation: { close: () => void } | null = null
  function closeConfirmation() { const previous = confirmation; confirmation = null; previous?.close() }
  function invalidate() { closeConfirmation(); error.value = '' }
  function capture() { const valid = options.capture(), filter = options.filterKey(); return () => valid() && filter === options.filterKey() }
  function records(ids: readonly CaseId[]) {
    if (!ids.length) throw Error('Missing selected case')
    return [...new Map(ids.map(value => { const id = requiredUiCaseAssetId(value); return [String(id), id] })).values()].map(id => { const row = options.rows().find(row => String(row.id) === String(id)); if (!row) throw Error('Missing case row'); return row })
  }
  async function dispatch(kind: Action, ids: CaseId[], current: () => boolean, environment: CaseId | null, target?: PublicationStatus): Promise<boolean> {
    if (pending.value || !options.available() || !current()) return false
    const completionCurrent = capture()
    pending.value = { kind, ids: [...ids] }; error.value = ''; options.beforeWrite()
    try {
      const response = kind === 'delete' ? await deleteUiCase(ids.length === 1 ? ids[0] : ids)
        : kind === 'copy' ? await postUiCaseCopy(ids[0])
        : kind === 'run' ? await getUiCaseRun(ids[0], requiredUiCaseAssetId(environment))
        : kind === 'batch-run' ? await postUiRunCaseBatch(ids, requiredUiCaseAssetId(environment))
        : await putUiCasePublication(ids[0], target!)
      uiCaseAssetResponse(response)
      if (!current()) return false
      Message.success(kind === 'run' || kind === 'batch-run' ? '执行任务已提交' : '操作成功')
      closeConfirmation()
      try { await options.committed(kind, [...ids], target) } catch { if (completionCurrent()) error.value = '操作已完成，列表刷新失败，请重新加载'; return true }
      return true
    } catch { if (current()) error.value = '操作失败，请检查后重试'; return false }
    finally { pending.value = null }
  }
  function run(id: CaseId): Promise<boolean> {
    if (!options.available() || pending.value) return Promise.resolve(false)
    const environment = uiCaseAssetId(options.environment())
    if (environment === null) { Message.error('请先选择用例执行的环境'); return Promise.resolve(false) }
    try { records([id]) } catch { error.value = '用例数据已变化，请重新加载'; return Promise.resolve(false) }
    return dispatch('run', [id], capture(), environment)
  }
  function copy(id: CaseId): Promise<boolean> {
    try { records([id]) } catch { error.value = '用例数据已变化，请重新加载'; return Promise.resolve(false) }
    return dispatch('copy', [id], capture(), null)
  }
  function confirm(kind: 'delete' | 'batch-run' | 'publication', values: readonly CaseId[], target?: PublicationStatus): boolean {
    if (!options.available() || pending.value || confirmation) return false
    let selected: UiCaseRow[]
    try { selected = records(values) } catch { Message.warning('请选择当前列表中的用例'); return false }
    const ids = selected.map(row => row.id), environment = kind === 'batch-run' ? uiCaseAssetId(options.environment()) : null
    if (kind === 'batch-run') {
      if (environment === null) { Message.error('请先选择用例执行的环境'); return false }
      if (new Set(selected.map(row => row.project_product?.project?.id).filter(id => id != null).map(String)).size > 1) { Message.warning('批量执行只能选择同一项目下的用例'); return false }
    }
    if (kind === 'publication' && target !== 'unpublished' && selected.some(row => row.status !== 1)) { Message.warning('用例必须执行通过后才能提交预发布'); return false }
    const current = capture(), publication = selected.map(row => row.publication_status), title = kind === 'delete' ? '删除用例' : kind === 'batch-run' ? '批量执行' : target === 'prepublished' ? '提交预发布' : '退回未发布'
    let open = true
    const close = () => { if (!open) return; open = false; confirmation = null; handle.close() }
    const handle = Modal.confirm({
      title, content: kind === 'delete' ? '确定删除选中的用例吗？' : kind === 'batch-run' ? '批量执行会生成多个浏览器，确定执行选中的用例吗？' : target === 'prepublished' ? '提交后由项目产品负责人审核，预发布用例不参与定时执行。确认提交吗？' : '退回后该用例不再参与定时执行。确认退回吗？',
      cancelText: '取消', okText: kind === 'delete' ? '删除' : kind === 'batch-run' ? '执行' : title,
      okButtonProps: kind === 'delete' || target === 'unpublished' ? { status: 'danger' } : {}, onCancel: close,
      onBeforeOk: async () => {
        if (!open || !current() || pending.value) return false
        try {
          const latest = records(ids)
          if (kind === 'publication' && latest.some((row, index) => row.publication_status !== publication[index] || (target !== 'unpublished' && row.status !== 1))) throw Error('Changed case')
        } catch { error.value = '用例已变化，请重新加载后操作'; close(); return false }
        return dispatch(kind, ids, () => open && current(), environment, target)
      },
    })
    confirmation = { close }; return true
  }
  return { pending, error, run, copy, remove: (ids: readonly CaseId[]) => confirm('delete', ids), batchRun: (ids: readonly CaseId[]) => confirm('batch-run', ids), publication: (id: CaseId, target: 'prepublished' | 'unpublished') => confirm('publication', [id], target), invalidate, closeConfirmation }
}
