import { computed, watch } from 'vue'
import { Message } from '@arco-design/web-vue'

import { useRowSelection } from '@/hooks/table'

export interface ProjectLockedSelectionProject {
  id: number | string
  name: string
}

export interface ProjectLockedSelectionOptions {
  scopeLabel?: string
  actionLabel?: string
  itemLabel?: string
}

export function useProjectLockedRowSelection<T extends { id: number | string }>(
  getRows: () => T[],
  getProject: (row?: T) => ProjectLockedSelectionProject | undefined,
  options: ProjectLockedSelectionOptions = {}
) {
  const scopeLabel = options.scopeLabel || '项目'
  const actionLabel = options.actionLabel || '执行'
  const itemLabel = options.itemLabel || '用例'
  const { selectedRowKeys, showCheckedAll } = useRowSelection()
  const normalizeId = (id: string | number | null | undefined) => id == null ? '' : String(id).trim()
  const rowsById = computed(() => new Map(getRows().map(row => [normalizeId(row.id), row])))
  const projectId = (row?: T) => normalizeId(getProject(row)?.id)

  function currentKeys<K extends string | number>(keys: K[]): K[] {
    const seen = new Set<string>()
    return keys.filter(key => {
      const id = normalizeId(key)
      if (!rowsById.value.has(id) || seen.has(id)) return false
      seen.add(id)
      return true
    })
  }

  // 列表翻页/刷新后不保留不可见的选择；静默轮询仍保留当前页已有 ID。
  watch(() => getRows().map(row => normalizeId(row.id)), () => {
    const keys = currentKeys(selectedRowKeys.value)
    if (keys.length !== selectedRowKeys.value.length) selectedRowKeys.value = keys
  })

  const selectedRows = computed(() => {
    const selectedIds = new Set(selectedRowKeys.value.map(normalizeId))
    return getRows().filter((row) => selectedIds.has(normalizeId(row.id)))
  })

  const selectedProject = computed(() => getProject(selectedRows.value.find(row => projectId(row))))

  const selectableDataList = computed(() => {
    const lockedId = normalizeId(selectedProject.value?.id)
    const selectedIds = new Set(selectedRowKeys.value.map(normalizeId))
    return getRows().map((row) => ({
      ...row,
      disabled: Boolean(
        lockedId && projectId(row) && projectId(row) !== lockedId &&
          !selectedIds.has(normalizeId(row.id))
      ),
    }))
  })

  function onSelectionChange(keys: Array<string | number>) {
    const visibleKeys = currentKeys(keys)
    const selectedIds = new Set(visibleKeys.map(normalizeId))
    const rows = getRows().filter((row) => selectedIds.has(normalizeId(row.id)))
    const previous = selectedRows.value.find(row => selectedIds.has(normalizeId(row.id)) && projectId(row))
    const lockedProject = getProject(previous) || getProject(rows.find(row => projectId(row)))
    if (!lockedProject) {
      selectedRowKeys.value = visibleKeys as string[]
      return
    }
    const retainedKeys = visibleKeys.filter((key) => {
      const row = rowsById.value.get(normalizeId(key))
      return !projectId(row) || projectId(row) === normalizeId(lockedProject.id)
    })
    if (retainedKeys.length !== visibleKeys.length) {
      Message.warning(
        `一次批量${actionLabel}只能选择同一${scopeLabel}下的${itemLabel}，已保留“${lockedProject.name}”${scopeLabel}的选择`
      )
    }
    selectedRowKeys.value = retainedKeys as string[]
  }

  function validateSingleProject(prefix = '所选用例') {
    const keys = currentKeys(selectedRowKeys.value)
    if (keys.length !== selectedRowKeys.value.length) {
      selectedRowKeys.value = keys
      Message.warning('部分已选记录已不在当前列表中，已清理失效选择，请重新确认后操作')
      return false
    }
    if (selectedRows.value.some(row => !projectId(row))) {
      Message.warning(`${prefix}缺少${scopeLabel}归属信息，请刷新后重新选择`)
      return false
    }
    const projects = new Map(
      selectedRows.value
        .map(getProject)
        .filter((project): project is ProjectLockedSelectionProject => Boolean(normalizeId(project?.id)))
        .map((project) => [normalizeId(project.id), project.name])
    )
    if (projects.size <= 1) return true
    Message.warning(
      `${prefix}来自多个${scopeLabel}：${Array.from(projects.values()).join(
        '、'
      )}。一次批量${actionLabel}只能选择同一${scopeLabel}下的${itemLabel}`
    )
    return false
  }

  return {
    selectedRowKeys,
    showCheckedAll,
    selectableDataList,
    onSelectionChange,
    validateSingleProject,
  }
}
