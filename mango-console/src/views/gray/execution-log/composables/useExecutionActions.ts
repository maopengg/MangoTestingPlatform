import { onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { reportLoadError } from '@/utils/load-error'
import { postGrayExecutionLogCleanupExpired, postGrayExecutionRetryRestore } from '@/api/gray'
import { canRestore, isStatus, object, positiveId } from '../records'

type Action = { kind: 'restore'; id: number } | { kind: 'cleanup' }
export function useExecutionActions(options: {
  contextKey: () => string
  blocked: () => boolean
  applied: () => Promise<boolean>
}) {
  const pending = ref<Action | null>(null),
    confirming = ref(false)
  let active = true,
    generation = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  function close() {
    const handle = confirmation
    confirmation = null
    confirming.value = false
    handle?.close()
  }
  function invalidate() {
    ++generation
    close()
  }
  function confirm(action: Action) {
    if (!active || options.blocked() || pending.value || confirming.value) return
    const source: Action =
      action.kind === 'restore' ? { kind: 'restore', id: action.id } : { kind: 'cleanup' }
    const version = generation,
      context = options.contextKey()
    const current = () => active && generation === version && options.contextKey() === context
    const dialog = Modal.confirm({
      title: source.kind === 'restore' ? '恢复灰度' : '清理灰度执行记录',
      content:
        source.kind === 'restore'
          ? `确认根据执行记录 ${source.id} 重新恢复灰度？`
          : '确认删除 1 个月前的灰度执行记录？该操作不可恢复。',
      okText: source.kind === 'restore' ? '恢复' : '清理',
      cancelText: '取消',
      okButtonProps: source.kind === 'cleanup' ? { status: 'danger' } : undefined,
      onBeforeCancel: () => !pending.value,
      onClose: () => {
        if (confirmation === dialog) {
          confirmation = null
          confirming.value = false
        }
      },
      onBeforeOk: async () => {
        if (!current() || confirmation !== dialog || pending.value || options.blocked())
          return false
        pending.value = source
        let applied = false
        try {
          const response = await (source.kind === 'restore'
            ? postGrayExecutionRetryRestore({ execution_log_id: source.id })
            : postGrayExecutionLogCleanupExpired({ retention_days: 30 }))
          if (!current()) return false
          const row = object(response.data)
          if (response.code !== 200) throw Error('Invalid action response')
          if (source.kind === 'restore') {
            // 恢复接口返回新建的恢复记录 ID，而非来源记录 ID。
            if (!positiveId(row.execution_log_id) || !isStatus(row.status))
              throw Error('Invalid restore acknowledgment')
            if (row.status === 1) Message.success('恢复成功')
            else Message.error('恢复失败，请在执行记录中查看详情')
          } else {
            if (
              row.retention_days !== 30 ||
              typeof row.deleted_count !== 'number' ||
              !Number.isSafeInteger(row.deleted_count) ||
              row.deleted_count < 0
            )
              throw Error('Invalid cleanup acknowledgment')
            Message.success(`清理完成，共删除 ${row.deleted_count} 条`)
          }
          applied = true
          close()
          await options.applied()
        } catch (error) {
          if (current()) {
            if (applied) reportLoadError(error)
            else Message.error('操作失败或结果未确认，请刷新核对后重试')
          }
        } finally {
          pending.value = null
        }
        return false
      },
    })
    confirmation = dialog
    confirming.value = true
  }
  function restore(record: { id: number; status: number }) {
    if (positiveId(record.id) && canRestore(record.status))
      confirm({ kind: 'restore', id: record.id })
  }
  const cleanupExpired = () => confirm({ kind: 'cleanup' })
  watch(options.contextKey, invalidate, { flush: 'sync' })
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
  return { pending, confirming, restore, cleanupExpired }
}
