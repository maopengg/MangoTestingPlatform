import { onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import {
  deleteGrayYamlFile,
  deleteGrayYamlFileBinding,
  putGrayYamlFile,
  putGrayYamlFileBinding,
} from '@/api/gray'
import { object, selectionId } from '../forms'

export interface MutationTarget {
  kind: 'yaml' | 'binding'
  id: number
  ownerId: number
  label: string
}
interface PendingMutation {
  kind: MutationTarget['kind']
  id: number
  action: 'status' | 'delete'
}
export function useYamlMutations(options: {
  contextKey: () => string
  blocked: () => boolean
  applied: (target: MutationTarget, status?: number) => Promise<boolean>
}) {
  const pending = ref<PendingMutation | null>(null),
    confirming = ref(false)
  let active = true,
    generation = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  function closeConfirmation() {
    const handle = confirmation
    confirmation = null
    confirming.value = false
    handle?.close()
  }
  function invalidate() {
    ++generation
    closeConfirmation()
  }
  const allowed = (target: MutationTarget) =>
    active &&
    !pending.value &&
    !options.blocked() &&
    !!selectionId(target.id) &&
    !!selectionId(target.ownerId)
  function snapshot(target: MutationTarget): MutationTarget {
    return { kind: target.kind, id: target.id, ownerId: target.ownerId, label: target.label }
  }
  async function changeStatus(target: MutationTarget, checked: boolean) {
    if (!allowed(target) || confirming.value) return false
    const source = snapshot(target),
      version = generation,
      context = options.contextKey(),
      status = checked ? 1 : 0
    const current = () => active && generation === version && options.contextKey() === context
    pending.value = { kind: source.kind, id: source.id, action: 'status' }
    let applied = false
    try {
      const response = await (source.kind === 'yaml' ? putGrayYamlFile : putGrayYamlFileBinding)({
        id: source.id,
        status,
      })
      if (!current()) return false
      const row = object(response.data)
      if (
        response.code !== 200 ||
        selectionId(row.id) !== source.id ||
        row.status !== status ||
        selectionId(source.kind === 'yaml' ? row.project_product : row.yaml_file) !== source.ownerId
      )
        throw Error('Invalid status acknowledgment')
      applied = true
      Message.success('状态更新成功')
      const loaded = await options.applied(source, status)
      if (current() && !loaded) Message.error('状态已更新，列表读取失败，请重试查询')
    } catch {
      if (current())
        Message.error(
          applied
            ? '状态已更新，列表读取失败，请重试查询'
            : '状态更新失败或结果未确认，请重试查询后操作'
        )
    } finally {
      pending.value = null
    }
    return false
  }
  function confirmDelete(target: MutationTarget) {
    if (!allowed(target) || confirming.value) return
    const source = snapshot(target),
      version = generation,
      context = options.contextKey()
    const current = () => active && generation === version && options.contextKey() === context
    const dialog = Modal.confirm({
      title: source.kind === 'yaml' ? '删除配置文件' : '删除仓库绑定',
      content: `确认删除 ${source.label || source.id}？`,
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      onBeforeCancel: () => !pending.value,
      onClose: () => {
        if (confirmation === dialog) {
          confirmation = null
          confirming.value = false
        }
      },
      onBeforeOk: async () => {
        if (!current() || confirmation !== dialog || !allowed(source)) return false
        pending.value = { kind: source.kind, id: source.id, action: 'delete' }
        let applied = false
        try {
          const response = await (source.kind === 'yaml'
            ? deleteGrayYamlFile
            : deleteGrayYamlFileBinding)(source.id)
          if (!current()) return false
          // 通用 CRUD 删除只返回成功 code，不返回删除数量或目标列表。
          if (response.code !== 200) throw Error('Invalid delete acknowledgment')
          applied = true
          closeConfirmation()
          Message.success('删除成功')
          const loaded = await options.applied(source)
          if (current() && !loaded) Message.error('删除已完成，列表读取失败，请重试查询')
        } catch {
          if (current())
            Message.error(
              applied
                ? '删除已完成，列表读取失败，请重试查询'
                : '删除失败或结果未确认，请刷新核对后重试'
            )
        } finally {
          pending.value = null
        }
        return false
      },
    })
    confirmation = dialog
    confirming.value = true
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
  return { pending, confirming, changeStatus, confirmDelete }
}
