import type { ModuleRecord } from './types'

export const moduleLevelLabels = ['一级模块', '二级模块', '三级模块']
export const moduleLevelIconLines = [[12], [9, 15], [6, 12, 18]]

export interface ModuleTreeNode {
  key: number
  title: string
  record: ModuleRecord
  children: ModuleTreeNode[]
  childCount: number
}

export function buildModuleTree(records: ModuleRecord[]): ModuleTreeNode[] {
  const nodes = new Map<number, ModuleTreeNode>()
  records.forEach((record) =>
    nodes.set(Number(record.id), {
      key: Number(record.id),
      title: record.name,
      record,
      children: [],
      childCount: 0,
    })
  )
  const roots: ModuleTreeNode[] = []
  records.forEach((record) => {
    const node = nodes.get(Number(record.id))!
    const parent = nodes.get(Number(record.parent?.id))
    if (parent && parent !== node) parent.children.push(node)
    else roots.push(node)
  })
  nodes.forEach((node) => {
    node.childCount = node.children.length
  })
  return roots
}

export function filterModuleTree(nodes: ModuleTreeNode[], keyword: string): ModuleTreeNode[] {
  const query = keyword.trim().toLocaleLowerCase()
  if (!query) return nodes
  return nodes.flatMap((node) => {
    // 命中分类时保留整个分支，命中后代时保留祖先链。
    if (node.title.toLocaleLowerCase().includes(query) || String(node.key) === query) return [node]
    const children = filterModuleTree(node.children, query)
    return children.length ? [{ ...node, children }] : []
  })
}

export function moduleBranchKeys(nodes: ModuleTreeNode[], maxExpandedLevel = Infinity): number[] {
  return nodes.flatMap((node) =>
    node.children.length && Number(node.record.level) <= maxExpandedLevel
      ? [node.key, ...moduleBranchKeys(node.children, maxExpandedLevel)]
      : []
  )
}

export function moduleCreateDraft(parent?: ModuleRecord) {
  return {
    name: '',
    parent: parent?.id ?? null,
    parentName: parent?.name || '',
    level: Number(parent?.level || 0) + 1,
  }
}
