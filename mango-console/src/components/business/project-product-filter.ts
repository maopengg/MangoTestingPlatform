export interface ProjectProductOption {
  label: string
  value: string | number
  description?: string
  children?: ProjectProductOption[]
}

export interface ProjectProductFilterNode {
  key: string
  title: string
  selectable?: boolean
  productId?: string | number
  productDescription?: string
  moduleId?: string | number
  projectGroupStart?: boolean
  children?: ProjectProductFilterNode[]
}

export interface ModuleOption {
  key: string | number
  title?: string
  name?: string
  children?: ModuleOption[]
}

export interface ModuleLevelStats {
  level1: number
  level2: number
  level3: number
}

export function groupModuleTreeByProjectProduct(
  nodes: ModuleOption[]
): Record<string, ModuleOption[]> {
  return (nodes || []).reduce<Record<string, ModuleOption[]>>((result, node) => {
    const projectProductId = (node as ModuleOption & { project_product_id?: string | number })
      .project_product_id
    if (projectProductId === null || projectProductId === undefined) return result
    const key = String(projectProductId)
    ;(result[key] ||= []).push(node)
    return result
  }, {})
}

export function getModuleLevelStats(nodes: ModuleOption[], depth = 1): ModuleLevelStats {
  return (nodes || []).reduce(
    (stats, node) => {
      if (depth === 1) stats.level1 += 1
      if (depth === 2) stats.level2 += 1
      if (depth === 3) stats.level3 += 1
      const children = getModuleLevelStats(node.children || [], depth + 1)
      stats.level1 += children.level1
      stats.level2 += children.level2
      stats.level3 += children.level3
      return stats
    },
    { level1: 0, level2: 0, level3: 0 }
  )
}

export function filterProjectProductOptions(
  options: ProjectProductOption[],
  keyword: string
): ProjectProductOption[] {
  const normalizedKeyword = keyword.trim().toLocaleLowerCase()
  if (!normalizedKeyword) return options

  return options.flatMap((project) => {
    if (project.label.toLocaleLowerCase().includes(normalizedKeyword)) return [project]

    const children = (project.children || []).filter((product) =>
      product.label.toLocaleLowerCase().includes(normalizedKeyword)
    )
    return children.length ? [{ ...project, children }] : []
  })
}

export function getFirstProductId(options: ProjectProductOption[]): string | number | null {
  for (const project of options || []) {
    const product = project.children?.[0]
    if (product) return product.value
  }
  return null
}

export function flattenProjectProducts(options: ProjectProductOption[]) {
  return sortProjectProductOptions(options).flatMap((project) =>
    sortByLabel(project.children || []).map((product, productIndex) => ({
      projectProductId: product.value,
      title: `${project.label} / ${product.label}`,
      ...(product.description?.trim() ? { productDescription: product.description.trim() } : {}),
      projectGroupStart: productIndex === 0,
    }))
  )
}

export function getFirstProductIdWithModules(
  entries: Array<{ projectProductId: string | number }>,
  modulesByProduct: Record<string, ModuleOption[]>
): string | number | null {
  if (!entries.length) return null
  const matched = entries.find(
    (entry) => (modulesByProduct[String(entry.projectProductId)] || []).length > 0
  )
  return matched?.projectProductId ?? entries[0].projectProductId
}

export function buildProjectProductFilterTree(
  options: ProjectProductOption[]
): ProjectProductFilterNode[] {
  return sortProjectProductOptions(options).map((project) => ({
    key: `project:${project.value}`,
    title: project.label,
    selectable: false,
    projectGroupStart: true,
    children: sortByLabel(project.children || []).map((product) => ({
      key: `product:${product.value}`,
      title: product.label,
      productId: product.value,
      ...(product.description?.trim() ? { productDescription: product.description.trim() } : {}),
    })),
  }))
}

function sortProjectProductOptions(options: ProjectProductOption[]) {
  return sortByLabel(options || [])
}

function sortByLabel<T extends { label: string }>(items: T[]): T[] {
  return [...items].sort((left, right) =>
    String(left.label || '').localeCompare(String(right.label || ''), 'zh-CN', {
      numeric: true,
      sensitivity: 'base',
    })
  )
}

export function getProductIdFromTreeKey(key?: string): string | number | null {
  if (!key?.startsWith('product:')) return null
  const value = key.slice('product:'.length)
  return /^\d+$/.test(value) ? Number(value) : value
}

export function buildModuleFilterTree(
  options: ModuleOption[],
  depth = 1
): ProjectProductFilterNode[] {
  return (options || []).flatMap((module) => {
    const children = buildModuleFilterTree(module.children || [], depth + 1)
    const title = module.name || module.title || String(module.key)
    if (title.trim() === '-') return children
    return [
      {
        key: `${depth === 3 ? 'module' : 'module-group'}:${module.key}`,
        title,
        moduleId: module.key,
        selectable: true,
        ...(children.length ? { children } : {}),
      },
    ]
  })
}

export function buildAllProductModuleFilterTree(
  entries: Array<{
    projectProductId: string | number
    title: string
    projectGroupStart?: boolean
    productDescription?: string
  }>,
  modulesByProduct: Record<string, ModuleOption[]>
): ProjectProductFilterNode[] {
  return entries.flatMap((entry) => {
    const children = buildModuleFilterTree(modulesByProduct[String(entry.projectProductId)] || [])
    return [
      {
        key: `product-group:${entry.projectProductId}`,
        title: entry.title,
        productId: entry.projectProductId,
        ...(entry.productDescription ? { productDescription: entry.productDescription } : {}),
        projectGroupStart: entry.projectGroupStart,
        selectable: true,
        ...(children.length ? { children } : {}),
      },
    ]
  })
}

export function getProductIdForTreeSelection(
  nodes: ProjectProductFilterNode[],
  key: string,
  parentProductId: string | number | null = null
): string | number | null {
  for (const node of nodes || []) {
    const productId = node.productId ?? parentProductId
    if (node.key === key) return productId
    const matched = getProductIdForTreeSelection(node.children || [], key, productId)
    if (matched !== null) return matched
  }
  return null
}

export function getTreeSelectionPath(nodes: ProjectProductFilterNode[], key: string): string[] {
  for (const node of nodes || []) {
    if (node.key === key) return [node.key]
    const childPath = getTreeSelectionPath(node.children || [], key)
    if (childPath.length) return [node.key, ...childPath]
  }
  return []
}

export function getModuleIdFromTreeKey(key?: string): string | number | null {
  if (!key?.startsWith('module:')) return null
  const value = key.slice('module:'.length)
  return /^\d+$/.test(value) ? Number(value) : value
}

export function getSelectedModuleIdFromTreeKey(key?: string): string | number | null {
  if (!key || (!key.startsWith('module:') && !key.startsWith('module-group:'))) return null
  const value = key.slice(key.indexOf(':') + 1)
  return /^\d+$/.test(value) ? Number(value) : value
}

export function getModuleIdsForSelection(
  nodes: ProjectProductFilterNode[],
  key: string
): Array<string | number> {
  for (const node of nodes || []) {
    if (node.key === key) return collectLeafModuleIds(node)
    const matched = getModuleIdsForSelection(node.children || [], key)
    if (matched.length) return matched
  }
  return []
}

export function getExpandableTreeKeys(nodes: ProjectProductFilterNode[]): string[] {
  return (nodes || []).flatMap((node) => [
    ...(node.children?.length ? [node.key] : []),
    ...getExpandableTreeKeys(node.children || []),
  ])
}

function collectLeafModuleIds(node: ProjectProductFilterNode): Array<string | number> {
  if (!node.children?.length) return node.moduleId == null ? [] : [node.moduleId]
  return node.children.flatMap(collectLeafModuleIds)
}

export function getFirstSelectableModulePath(nodes: ProjectProductFilterNode[]): string[] {
  for (const node of nodes || []) {
    if (node.key.startsWith('module:')) return [node.key]
    const childPath = getFirstSelectableModulePath(node.children || [])
    if (childPath.length) return [node.key, ...childPath]
  }
  return []
}

export function filterModuleTree(
  nodes: ProjectProductFilterNode[],
  keyword: string
): ProjectProductFilterNode[] {
  const normalizedKeyword = keyword.trim().toLocaleLowerCase()
  if (!normalizedKeyword) return nodes
  return nodes.reduce<ProjectProductFilterNode[]>((result, node) => {
    const children = filterModuleTree(node.children || [], normalizedKeyword)
    if (node.title.toLocaleLowerCase().includes(normalizedKeyword) || children.length) {
      result.push({ ...node, ...(children.length ? { children } : {}) })
    }
    return result
  }, [])
}
