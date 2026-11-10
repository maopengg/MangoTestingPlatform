import {
  computed,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  reactive,
  ref,
  shallowRef,
  watch,
} from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import {
  batchFunctionalPlanResult,
  finishFunctionalPlan,
  removeFunctionalPlanCases,
  startFunctionalPlan,
} from '@/api/functional-test'
import { parsePlanCase, planIdValue, planList, planObject } from '../presentation'
import type { PlanExecutionResult } from '../types'

interface Subject {
  id: number
  status: number
  caseIds: number[]
  hasRequirement: boolean
  unlinkedFailedCount: number
}
type Kind = 'start' | 'finish' | 'remove' | 'batch'
export function usePlanExecution(options: {
  context: () => string
  available: () => boolean
  blocked: () => boolean
  subject: () => Subject | null
  selectedIds: () => number[]
  accepted: (result: PlanExecutionResult) => void
}) {
  const kind = ref<Kind | null>(null),
    error = ref(false)
  const busy = computed(() => kind.value !== null)
  const batchResult = ref<number | null>(null)
  const startVisible = ref(false)
  const startForm = reactive({ update_requirement_status: false })
  const dialog = shallowRef<ReturnType<typeof Modal.warning> | null>(null)
  const confirming = computed(() => startVisible.value || dialog.value !== null)
  let active = true,
    generation = 0
  let startTarget: { subject: Subject; version: number } | null = null
  const available = () => active && options.available()
  const current = (version: number) => available() && generation === version
  const canCancel = () => !busy.value
  function cancelStart() {
    startVisible.value = false
    startTarget = null
    startForm.update_requirement_status = false
  }
  function invalidate() {
    ++generation
    cancelStart()
    dialog.value?.close()
    dialog.value = null
    error.value = false
  }
  function capture(): Subject | null {
    if (!available() || busy.value || options.blocked()) return null
    const value = options.subject()
    return value ? { ...value, caseIds: [...value.caseIds] } : null
  }
  async function perform(
    operation: Kind,
    target: Subject,
    version: number,
    ids: number[] = [],
    result?: number
  ) {
    const latest = options.subject()
    if (
      !current(version) ||
      busy.value ||
      options.blocked() ||
      !latest ||
      latest.id !== target.id ||
      latest.status !== target.status
    )
      return false
    kind.value = operation
    batchResult.value = operation === 'batch' ? result ?? null : null
    error.value = false
    let accepted: PlanExecutionResult | null = null
    try {
      if (operation === 'start' || operation === 'finish') {
        const response =
          operation === 'start'
            ? await startFunctionalPlan(target.id, startForm.update_requirement_status)
            : await finishFunctionalPlan(target.id)
        if (!current(version)) return false
        const data = planObject(response.data),
          status = operation === 'start' ? 2 : 3
        if (planIdValue(data.id) !== target.id || data.status !== status)
          throw Error('执行结果未确认')
        accepted = {
          kind: operation,
          id: target.id,
          status,
          started_at: typeof data.started_at === 'string' ? data.started_at : '',
          finished_at: typeof data.finished_at === 'string' ? data.finished_at : '',
        }
      } else if (operation === 'remove') {
        const response = await removeFunctionalPlanCases({
          plan_id: target.id,
          plan_case_ids: [...ids],
        })
        if (!current(version)) return false
        const count = planObject(response.data).count
        if (typeof count !== 'number' || !Number.isSafeInteger(count) || count < 0)
          throw Error('移出结果未确认')
        accepted = { kind: 'remove', ids: [...ids] }
      } else {
        const response = await batchFunctionalPlanResult({
          plan_id: target.id,
          plan_case_ids: [...ids],
          result,
        })
        if (!current(version)) return false
        const rows = planList(response.data).map(parsePlanCase)
        if (
          rows.some(
            (row) => row.plan !== target.id || !ids.includes(row.id) || row.result !== result
          )
        )
          throw Error('批量结果未确认')
        accepted = { kind: 'batch', rows }
      }
    } catch {
      if (current(version)) error.value = true
    } finally {
      kind.value = null
      batchResult.value = null
    }
    if (!accepted || !current(version)) return false
    cancelStart()
    dialog.value?.close()
    dialog.value = null
    Message.success('操作成功')
    try {
      options.accepted(accepted)
    } catch {
      Message.warning('操作已成功，请刷新计划查看最新数据')
    }
    return true
  }
  function openStart() {
    if (confirming.value) return
    const target = capture()
    if (!target || ![0, 1].includes(target.status) || !target.caseIds.length) return
    error.value = false
    startTarget = { subject: target, version: generation }
    startForm.update_requirement_status = target.hasRequirement
    startVisible.value = true
  }
  async function start() {
    if (startTarget && startVisible.value)
      await perform('start', startTarget.subject, startTarget.version)
    return false
  }
  function confirm(operation: 'remove' | 'finish') {
    if (confirming.value) return
    const target = capture()
    if (!target || (operation === 'remove' ? ![0, 1].includes(target.status) : target.status !== 2))
      return
    const ids = [...new Set(options.selectedIds())].filter((id) => target.caseIds.includes(id))
    if (operation === 'remove' && !ids.length) return
    const version = generation
    error.value = false
    dialog.value = Modal.warning({
      title: operation === 'remove' ? '移出计划' : '完成测试计划',
      hideCancel: false,
      content:
        operation === 'remove'
          ? `确认移出 ${ids.length} 条用例及其本次结果？`
          : target.unlinkedFailedCount
          ? `当前仍有 ${target.unlinkedFailedCount} 条失败或阻塞用例未关联缺陷。完成后计划和结果将只读，是否继续？`
          : '完成后计划和结果将只读。确认完成本次测试？',
      onCancel: () => {
        dialog.value = null
      },
      onBeforeCancel: canCancel,
      onBeforeOk: () => perform(operation, target, version, ids),
    })
  }
  async function batch(result: number) {
    if (confirming.value || ![1, 2, 3].includes(result)) return false
    const target = capture()
    if (!target || target.status !== 2) return false
    const ids = [...new Set(options.selectedIds())].filter((id) => target.caseIds.includes(id))
    if (!ids.length) return false
    return perform('batch', target, generation, ids, result)
  }
  watch(options.context, invalidate, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    invalidate()
  })
  return {
    busy,
    batchResult,
    kind,
    error,
    confirming,
    startVisible,
    startForm,
    canCancel,
    cancelStart,
    openStart,
    start,
    remove: () => confirm('remove'),
    finish: () => confirm('finish'),
    batch,
  }
}
