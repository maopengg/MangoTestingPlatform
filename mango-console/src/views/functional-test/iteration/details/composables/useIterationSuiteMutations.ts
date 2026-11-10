import { reactive, ref } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { confirmManualSuiteSubmit, transitionManualSuiteStatus } from '@/api/functional-test'
import { iterationList, iterationObject, parseIterationSuite } from '../../presentation'
import type { IterationSuite } from '../../types'

export function useIterationSuiteMutations(options: {
  context: () => number
  active: () => boolean
  available: (id: number) => boolean
  owns: (row: IterationSuite) => boolean
  saved: (row: IterationSuite) => void
}) {
  const busy = reactive(new Map<number, 'transition' | 'submit'>())
  const writeScopes = new Map<number, number>()
  const error = ref('')
  const state = ref<'idle' | 'saving' | 'saved' | 'failed'>('idle')
  let dialog: ReturnType<typeof Modal.confirm> | null = null
  const current = (context: number) => options.active() && options.context() === context
  function invalidate() {
    dialog?.close()
    dialog = null
    error.value = ''
    state.value = 'idle'
  }
  async function write(
    row: IterationSuite,
    kind: 'transition' | 'submit',
    status?: number,
    context = options.context(),
    snapshot = row
  ) {
    if (
      !current(context) ||
      row.id !== snapshot.id ||
      !options.owns(row) ||
      !options.available(row.id) ||
      busy.has(row.id)
    )
      return false
    const id = row.id
    const payload = { id, status, expected_update_time: snapshot.update_time }
    busy.set(id, kind)
    writeScopes.set(id, context)
    error.value = ''
    state.value = 'saving'
    try {
      const data: unknown = (
        await (kind === 'submit'
          ? confirmManualSuiteSubmit(id)
          : transitionManualSuiteStatus(payload))
      ).data
      if (!current(context)) return false
      const response = iterationObject(data)
      const saved = parseIterationSuite(kind === 'submit' ? response : response.suite)
      if (saved.id !== id) throw Error('更新结果未确认')
      const warnings =
        kind === 'transition' && response.warnings != null
          ? iterationList(response.warnings).filter(
              (value): value is string => typeof value === 'string'
            )
          : []
      options.saved(saved)
      state.value = 'saved'
      if (warnings.length) Message.warning(warnings.join('；'))
      else Message.success(kind === 'submit' ? '已确认提测' : '需求状态已更新')
      return true
    } catch {
      if (current(context)) {
        state.value = 'failed'
        error.value = '需求更新失败，请重试'
      }
      return false
    } finally {
      busy.delete(id)
      writeScopes.delete(id)
      if (current(context) && Array.from(writeScopes.values()).includes(context))
        state.value = 'saving'
    }
  }
  function transition(row: IterationSuite, status: number) {
    if (
      !Number.isSafeInteger(status) ||
      row.status === status ||
      !options.active() ||
      !options.owns(row) ||
      !options.available(row.id) ||
      busy.has(row.id)
    )
      return
    if (status !== 6 && status !== 7) return write(row, 'transition', status)
    if (dialog) return
    const context = options.context()
    // Capture concurrency and identity fields before the confirmation can outlive the row.
    const snapshot = { ...row }
    let handle: ReturnType<typeof Modal.confirm> | null = null
    handle = (status === 7 ? Modal.warning : Modal.confirm)({
      title: status === 7 ? '确认取消需求' : '确认测试完成',
      content:
        status === 7
          ? `取消后需求将从当前看板中隐藏，但不会删除业务数据。确定取消「${
              row.requirement_name || row.id
            }」吗？`
          : '系统将检查执行中计划，并提示未执行用例和未关闭缺陷。确定继续吗？',
      hideCancel: false,
      onBeforeOk: () => {
        if (!current(context) || !options.owns(row)) return Promise.resolve(false)
        return write(row, 'transition', status, context, snapshot)
      },
      onBeforeCancel: () => !busy.has(row.id),
      onClose: () => {
        if (dialog === handle) dialog = null
      },
    })
    dialog = handle
  }
  function submit(row: IterationSuite) {
    if (row.status >= 4) return Promise.resolve(false)
    return write(row, 'submit')
  }
  return { busy, error, state, transition, submit, invalidate }
}
