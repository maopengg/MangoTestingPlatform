import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import {
  deleteGrayRepository,
  postGrayRepositorySync,
  postGrayRepositoryTest,
  putGrayRepository,
} from '@/api/gray'
import { object, positiveId, type RepositoryRow } from '../records'

export function useRepositoryActions(options: {
  contextKey: () => string
  blocked: () => boolean
  applied: () => Promise<boolean>
  statusApplied: (id: number, status: number) => void
}) {
  const pending = ref(''),
    confirmingId = ref<number | null>(null),
    actionLoading = computed(
      () => pending.value || (confirmingId.value === null ? '' : `confirm-${confirmingId.value}`)
    )
  let active = true,
    generation = 0,
    confirmation: ReturnType<typeof Modal.confirm> | null = null
  function close() {
    const handle = confirmation
    confirmation = null
    confirmingId.value = null
    handle?.close()
  }
  function invalidate() {
    ++generation
    close()
  }
  async function refresh(current: () => boolean) {
    try {
      const loaded = await options.applied()
      if (current() && !loaded) Message.error('操作已完成，列表读取失败，请重试查询')
    } catch {
      if (current()) Message.error('操作已完成，列表读取失败，请重试查询')
    }
  }
  async function run(
    kind: 'test' | 'sync' | 'status',
    source: RepositoryRow | number,
    value?: boolean
  ): Promise<boolean> {
    const id = typeof source === 'number' ? source : source.id
    if (!active || options.blocked() || actionLoading.value || !positiveId(id)) return false
    const rowSource =
      typeof source === 'number'
        ? null
        : { provider: source.provider, repo_url: source.repo_url, branch: source.branch }
    const version = generation,
      context = options.contextKey(),
      current = () => active && version === generation && context === options.contextKey(),
      status = value ? 1 : 0
    pending.value = `${kind}-${id}`
    let applied = false
    try {
      const response = await (kind === 'status'
        ? putGrayRepository({ id, status })
        : kind === 'test'
        ? postGrayRepositoryTest({ repository_id: id })
        : postGrayRepositorySync({ repository_id: id }))
      if (!current()) return false
      const row = object(response.data)
      if (response.code !== 200) throw Error('Invalid repository action response')
      if (kind === 'status') {
        if (row.id !== id || row.status !== status)
          throw Error('Invalid repository status acknowledgment')
        options.statusApplied(id, status)
      } else if (kind === 'test') {
        // 连接测试返回 Git 平台当前用户，不包含仓库 ID。
        if (!positiveId(row.id)) throw Error('Invalid connection acknowledgment')
      } else if (
        row.repository_id !== id ||
        row.provider !== rowSource?.provider ||
        row.repo_url !== rowSource?.repo_url ||
        row.branch !== rowSource?.branch ||
        !Array.isArray(row.files) ||
        row.files.some((file) => typeof file !== 'string') ||
        typeof row.file_count !== 'number' ||
        !Number.isSafeInteger(row.file_count) ||
        row.file_count !== row.files.length
      )
        throw Error('Invalid sync acknowledgment')
      applied = true
      Message.success(
        kind === 'test' ? '连接测试成功' : kind === 'sync' ? '同步成功' : '状态更新成功'
      )
      if (kind !== 'test') await refresh(current)
      return true
    } catch {
      if (current())
        Message.error(
          applied
            ? '操作已完成，列表读取失败，请重试查询'
            : '操作失败或结果未确认，请刷新核对后重试'
        )
      return applied
    } finally {
      pending.value = ''
    }
  }
  function onDelete(source: RepositoryRow) {
    if (!active || options.blocked() || actionLoading.value || !positiveId(source.id)) return
    const id = source.id,
      name = source.name,
      version = generation,
      context = options.contextKey(),
      current = () => active && version === generation && context === options.contextKey()
    const dialog = Modal.confirm({
      title: '删除灰度仓库',
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
        try {
          const response = await deleteGrayRepository(id)
          if (!current()) return false
          if (response.code !== 200) throw Error('Invalid repository deletion acknowledgment')
          close()
          Message.success('删除成功')
          await refresh(current)
        } catch {
          if (current()) Message.error('删除失败或结果未确认，请刷新核对后重试')
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
  return {
    actionLoading,
    onTest: (row: RepositoryRow) => run('test', row),
    onSync: (row: RepositoryRow) => run('sync', row),
    onModifyStatus: (value: boolean, id: number) => run('status', id, value),
    onDelete,
  }
}
