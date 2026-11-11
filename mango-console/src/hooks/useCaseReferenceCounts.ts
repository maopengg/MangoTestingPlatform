import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import useUserStore from '@/store/modules/user'
import { reportLoadError } from '@/utils/load-error'
import type { TableColumnData } from '@arco-design/web-vue'

type EntityId = string | number
type ReferenceRow = { id: EntityId; status?: number }
type ReferenceColumn = TableColumnData & { key?: string | number }

export function useCaseReferenceCounts(
  rows: () => ReferenceRow[],
  columns: ReferenceColumn[],
  read: (ids: EntityId[]) => Promise<{ data: Record<string, number> }>,
  listLoading: () => boolean,
  closeDetails: () => void
) {
  const user = useUserStore()
  const active = ref(true), loading = ref(false), counts = ref<Record<string, number>>({})
  let sequence = 0
  const tableColumns = computed(() => {
    const result = [...columns]
    const index = result.findIndex(column => column.key === 'status')
    result.splice(index < 0 ? Math.max(0, result.length - 1) : index + 1, 0, {
      key: 'case_reference_count', title: '引用Case数', width: 120, align: 'center',
    })
    return result
  })
  function invalidate() {
    sequence++
    loading.value = false
    counts.value = {}
    closeDetails()
  }
  async function refresh() {
    invalidate()
    if (!active.value || listLoading()) return
    const ids = rows().filter(row => row.status !== 1).map(row => row.id)
    if (!ids.length) return
    const current = sequence
    loading.value = true
    try {
      const response = await read(ids)
      if (current !== sequence) return
      const result: Record<string, number> = {}
      for (const id of ids) {
        const count = response.data?.[String(id)]
        if (!Number.isInteger(count) || count < 0) throw new Error('Invalid reference count')
        result[String(id)] = count
      }
      counts.value = result
    } catch (error) {
      if (current === sequence) reportLoadError(error, '引用Case数量加载失败，请重新查询', false)
    } finally {
      if (current === sequence) loading.value = false
    }
  }
  watch([() => rows().map(row => `${row.id}:${row.status === 1}`).join(','), listLoading], () => { void refresh() }, { immediate: true })
  watch(() => [user.userId, user.roleId, user.token], () => {
    invalidate()
  }, { flush: 'sync' })
  function close() { active.value = false; invalidate() }
  onBeforeUnmount(close)
  onDeactivated(close)
  onActivated(() => {
    if (active.value) return
    active.value = true
    void refresh()
  })
  return { loading, counts, tableColumns, refresh }
}
