import { onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { deleteManualCase, deleteManualSuite } from '@/api/functional-test'
export type SuiteDeleteKind = 'suite' | 'case'
export function useSuiteDeletion(options: {
  contextKey: () => string
  blocked: () => boolean
  refresh: (kind: SuiteDeleteKind, id: number) => Promise<boolean>
}) {
  const deleting = ref<{ kind: SuiteDeleteKind; id: number } | null>(null)
  const confirming = ref(false)
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
  function confirmDelete(kind: SuiteDeleteKind, id: number, name: string) {
    if (
      !active ||
      options.blocked() ||
      deleting.value ||
      confirming.value ||
      !Number.isSafeInteger(id) ||
      id <= 0
    )
      return
    const version = generation,
      context = options.contextKey()
    const current = () => active && generation === version && options.contextKey() === context
    const dialog = Modal.confirm({
      title: kind === 'suite' ? '删除需求' : '删除测试用例',
      content:
        kind === 'suite'
          ? `确认删除需求「${name || id}」吗？需求资料会删除，已生成的用例库资产会保留。`
          : `确认删除测试用例「${name || id}」吗？`,
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      onBeforeCancel: () => !deleting.value,
      onClose: () => {
        if (confirmation === dialog) {
          confirmation = null
          confirming.value = false
        }
      },
      onBeforeOk: async () => {
        if (!current() || confirmation !== dialog || deleting.value || options.blocked())
          return false
        deleting.value = { kind, id }
        let applied = false
        try {
          const response = await (kind === 'suite' ? deleteManualSuite(id) : deleteManualCase(id))
          if (!current()) return false
          const result: unknown = response.data
          if (!result || typeof result !== 'object' || Array.isArray(result))
            throw Error('Invalid delete result')
          const ack = result as Record<string, unknown>
          if (
            kind === 'case'
              ? ack.count !== 1
              : ack.deleted_count !== 1 ||
                !Array.isArray(ack.deleted_suite_ids) ||
                ack.deleted_suite_ids.length !== 1 ||
                ack.deleted_suite_ids[0] !== id
          )
            throw Error('Invalid deleted target')
          applied = true
          close()
          Message.success('删除成功')
          const loaded = await options.refresh(kind, id)
          if (current() && !loaded) Message.error('删除已完成，列表读取失败，请重试查询')
        } catch {
          if (current())
            Message.error(
              applied
                ? '删除已完成，列表读取失败，请重试查询'
                : '删除失败或结果未确认，请刷新核对后重试'
            )
        } finally {
          deleting.value = null
        }
        return false
      },
    })
    confirmation = dialog
    confirming.value = true
  }
  return { deleting, confirming, confirmDelete }
}
