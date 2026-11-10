import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { deleteGrayFeature, putGrayFeature } from '@/api/gray'
import { idOf, object } from '../editor-form'

export function useFeatureMutations(options: {
  contextKey: () => string
  blocked: () => boolean
  applied: () => Promise<boolean>
  statusApplied: (id: number, status: number) => void
}) {
  const pending = ref(''),
    confirmingId = ref<number | null>(null)
  const actionLoading = computed(
    () => pending.value || (confirmingId.value === null ? '' : `confirm-${confirmingId.value}`)
  )
  let active = true,
    generation = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  function closeConfirmation() {
    const handle = confirmation
    confirmation = null
    confirmingId.value = null
    handle?.close()
  }
  function invalidate() {
    ++generation
    closeConfirmation()
  }
  async function refresh(current: () => boolean) {
    const loaded = await options.applied()
    if (current() && !loaded) Message.error('操作已完成，列表读取失败，请重试查询')
  }
  async function onModifyStatus(value: boolean, id: number): Promise<boolean> {
    if (!active || options.blocked() || actionLoading.value || !idOf(id)) return false
    const version = generation,
      context = options.contextKey(),
      status = value ? 1 : 0
    const current = () => active && version === generation && context === options.contextKey()
    pending.value = `status-${id}`
    let applied = false
    try {
      const response = await putGrayFeature({ id, status })
      if (!current()) return false
      const row = object(response.data)
      if (response.code !== 200 || idOf(row.id) !== id || row.status !== status)
        throw Error('Invalid feature status acknowledgment')
      applied = true
      options.statusApplied(id, status)
      Message.success('状态更新成功')
      await refresh(current)
      return true
    } catch {
      if (current())
        Message.error(
          applied
            ? '状态已更新，列表读取失败，请重试查询'
            : '状态更新失败或结果未确认，请刷新核对后重试'
        )
      return applied
    } finally {
      pending.value = ''
    }
  }
  function onDelete(record: { id: number; name: string }) {
    if (!active || options.blocked() || actionLoading.value || !idOf(record.id)) return
    const id = record.id,
      name = record.name,
      version = generation,
      context = options.contextKey()
    const current = () => active && version === generation && context === options.contextKey()
    const dialog = Modal.confirm({
      title: '删除灰度开关',
      content: `确认删除 ${name}？`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      onBeforeCancel: () => !pending.value,
      onClose: () => {
        if (confirmation === dialog) {
          confirmation = null
          confirmingId.value = null
        }
      },
      onBeforeOk: async () => {
        if (!current() || confirmation !== dialog || pending.value || options.blocked())
          return false
        pending.value = `delete-${id}`
        let applied = false
        try {
          const response = await deleteGrayFeature(id)
          if (!current()) return false
          // 现有删除协议仅以 code 确认成功，不返回删除数量或 ID。
          if (response.code !== 200) throw Error('Invalid feature deletion acknowledgment')
          applied = true
          closeConfirmation()
          Message.success('删除成功')
          await refresh(current)
        } catch {
          if (current())
            Message.error(
              applied
                ? '删除已完成，列表读取失败，请重试查询'
                : '删除失败或结果未确认，请刷新核对后重试'
            )
        } finally {
          pending.value = ''
        }
        return false
      },
    })
    confirmation = dialog
    confirmingId.value = id
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
  return { actionLoading, onModifyStatus, onDelete }
}
