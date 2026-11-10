export type Selection = number | string | Array<number | string> | null
export interface Product {
  id: number
  name?: string
  project?: { id: number; name: string } | null
}
export interface Repository {
  id: number
  name: string
  branch: string
  test_env: number | null
}
export interface YamlRecord {
  id: number
  name: string
  project_product: Product | number | null
  effect_wait_seconds: number
  status: number
}
export interface BindingRecord {
  id: number
  yaml_file: number
  repository: Repository | number | null
  file_path: string
  status: number
}
export interface YamlForm {
  project_product: Selection
  name: string
  effect_wait_seconds: number | null
  status: number
}
export interface BindingForm {
  repository: number | string | null
  file_path: string | string[]
  status: number
}
export interface YamlEditorHandle {
  open(record?: YamlRecord, product?: Selection): void
}
export interface BindingEditorHandle {
  open(yaml: { id: number; name: string }, record?: BindingRecord): void
}
export interface PathNode {
  label: string
  value: string
  children?: PathNode[]
}

export function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
export function selectionId(value: unknown): number | null {
  const leaf: unknown = Array.isArray(value) ? value[value.length - 1] : value
  const id = leaf && typeof leaf === 'object' ? object(leaf).id : leaf
  if (
    (typeof id !== 'string' && typeof id !== 'number') ||
    (typeof id === 'string' && !/^\d+$/.test(id))
  )
    return null
  const result = Number(id)
  return Number.isSafeInteger(result) && result > 0 ? result : null
}
export function createYamlForm(record?: YamlRecord, product?: Selection): YamlForm {
  return {
    project_product: selectionId(record ? record.project_product : product),
    name: record?.name ?? '',
    effect_wait_seconds: record?.effect_wait_seconds ?? 10,
    status: record?.status ?? 1,
  }
}
export function yamlPayload(form: YamlForm, id: number | null) {
  return {
    ...(id === null ? {} : { id }),
    project_product: selectionId(form.project_product),
    name: form.name,
    effect_wait_seconds: form.effect_wait_seconds,
    status: form.status,
  }
}
export function yamlValidation(form: YamlForm): string | null {
  if (!selectionId(form.project_product)) return '请选择项目/产品'
  if (!form.name.trim()) return '请输入配置名称'
  if (
    form.effect_wait_seconds === null ||
    !Number.isSafeInteger(form.effect_wait_seconds) ||
    form.effect_wait_seconds < 0
  )
    return '请输入有效的等待秒数'
  return null
}
export function createBindingForm(record?: BindingRecord): BindingForm {
  return {
    repository: selectionId(record?.repository),
    file_path: record?.file_path ?? '',
    status: record?.status ?? 1,
  }
}
export function normalizePath(value: unknown): string {
  const leaf: unknown = Array.isArray(value) ? value[value.length - 1] : value
  return typeof leaf === 'string' ? leaf.trim() : ''
}
export function bindingPayload(form: BindingForm, yamlId: number, id: number | null) {
  return {
    ...(id === null ? {} : { id }),
    yaml_file: yamlId,
    repository: selectionId(form.repository),
    file_path: normalizePath(form.file_path),
    status: form.status,
  }
}
export function pathTree(paths: string[]): PathNode[] {
  const root: PathNode[] = [],
    nodes = new Map<string, PathNode>()
  for (const value of paths
    .map((path) =>
      path
        .trim()
        .replace(/\\/g, '/')
        .replace(/^\/+|\/+$/g, '')
    )
    .filter(Boolean)
    .sort()) {
    let children = root,
      path = ''
    for (const part of value.split('/')) {
      path = path ? `${path}/${part}` : part
      let node = nodes.get(path)
      if (!node) {
        node = { label: part, value: path, children: [] }
        nodes.set(path, node)
        children.push(node)
      }
      children = node.children!
    }
  }
  const prune = (items: PathNode[]): PathNode[] =>
    items.map((node) =>
      node.children?.length
        ? { ...node, children: prune(node.children) }
        : { label: node.label, value: node.value }
    )
  return prune(root)
}
export function repositories(value: unknown): Repository[] {
  if (!Array.isArray(value)) throw Error('Invalid repository list')
  return value.map((value) => {
    const row = object(value),
      id = selectionId(row.id)
    if (
      id === null ||
      typeof row.name !== 'string' ||
      typeof row.branch !== 'string' ||
      (row.test_env != null && (typeof row.test_env !== 'number' || !Number.isFinite(row.test_env)))
    )
      throw Error('Invalid repository')
    return {
      id,
      name: row.name,
      branch: row.branch,
      test_env: typeof row.test_env === 'number' ? row.test_env : null,
    }
  })
}
