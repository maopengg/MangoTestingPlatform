import { computed } from 'vue'
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

  const selectedRows = computed(() => {
    const selectedIds = new Set(selectedRowKeys.value.map(String))
    return getRows().filter((row) => selectedIds.has(String(row.id)))
  })

  const selectedProject = computed(() => getProject(selectedRows.value[0]))

  const selectableDataList = computed(() => {
    const projectId = selectedProject.value?.id
    const selectedIds = new Set(selectedRowKeys.value.map(String))
    return getRows().map((row) => ({
      ...row,
      disabled: Boolean(
        projectId &&
          getProject(row)?.id &&
          getProject(row)?.id !== projectId &&
          !selectedIds.has(String(row.id))
      ),
    }))
  })

  function onSelectionChange(keys: Array<string | number>) {
    const selectedIds = new Set(keys.map(String))
    const rows = getRows().filter((row) => selectedIds.has(String(row.id)))
    const lockedProject = selectedProject.value || getProject(rows[0])
    if (!lockedProject) {
      selectedRowKeys.value = keys as string[]
      return
    }
    const retainedKeys = keys.filter((key) => {
      const row = rows.find((item) => String(item.id) === String(key))
      return getProject(row)?.id === lockedProject.id
    })
    if (retainedKeys.length !== keys.length) {
      Message.warning(
        `一次批量${actionLabel}只能选择同一${scopeLabel}下的${itemLabel}，已保留“${lockedProject.name}”${scopeLabel}的选择`
      )
    }
    selectedRowKeys.value = retainedKeys as string[]
  }

  function validateSingleProject(prefix = '所选用例') {
    const projects = new Map(
      selectedRows.value
        .map(getProject)
        .filter((project): project is ProjectLockedSelectionProject => Boolean(project?.id))
        .map((project) => [project.id, project.name])
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
