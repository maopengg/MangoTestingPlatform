import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { ProjectProductOption } from '@/store/modules/project-options'

export interface BindingRecord {
  id: number
  name: string
  file_name: string
  auto_type: number
  test_dir: string[]
  pytest_config_path: string
  init_file: string
  case_count: number
  update_time: string
  update_user: { name: string; username: string } | null
  project_product: { id: number; name: string; project: { id: number; name: string } | null } | null
  repository: { id: number; name: string; active_branch: string; default_branch: string } | null
}
export interface BindingDraft {
  project_product: number | string | Array<number | string> | null
  repository: number | null
  file_name: string
  name: string
  auto_type: number | null
  test_dir: string[]
  pytest_config_path: string
}
export interface DirectoryEntry {
  value: string
  file_count: number
}
export interface DirectoryOption {
  label: string
  value: string
  children?: DirectoryOption[]
  stale?: boolean
  fileCount?: number
}
export function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('数据格式不正确')
  return value as Record<string, unknown>
}
export function bindingId(value: unknown): number {
  if (
    (typeof value !== 'number' && typeof value !== 'string') ||
    (typeof value === 'string' && !value.trim())
  )
    throw new Error('标识不正确')
  const id = Number(value)
  if (!Number.isSafeInteger(id) || id < 0) throw new Error('标识不正确')
  return id
}
const text = (value: unknown): string => (typeof value === 'string' ? value : '')
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0)
    throw new Error('数量格式不正确')
  return value
}
export function stringList(value: unknown): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string' || !item.trim()))
    throw new Error('目录格式不正确')
  return [...new Set(value as string[])]
}
export function checkBindingResponse(value: unknown): Record<string, unknown> {
  const response = object(value)
  if (response.code !== 200) throw new Error('请求失败，请重试')
  return response
}
export function readBinding(value: unknown): BindingRecord {
  const row = object(value),
    product = row.project_product == null ? null : object(row.project_product)
  const repository = row.repository == null ? null : object(row.repository)
  const user = row.update_user == null ? null : object(row.update_user)
  const project = product?.project == null ? null : object(product.project)
  if ((row.name != null && typeof row.name !== 'string') || typeof row.file_name !== 'string')
    throw new Error('项目绑定格式不正确')
  return {
    id: bindingId(row.id),
    name: text(row.name),
    file_name: row.file_name,
    auto_type: bindingId(row.auto_type),
    test_dir: stringList(row.test_dir ?? []),
    pytest_config_path: text(row.pytest_config_path),
    init_file: text(row.init_file),
    case_count: count(row.case_count ?? 0),
    update_time: text(row.update_time),
    update_user: user ? { name: text(user.name), username: text(user.username) } : null,
    project_product: product
      ? {
          id: bindingId(product.id),
          name: text(product.name),
          project: project ? { id: bindingId(project.id), name: text(project.name) } : null,
        }
      : null,
    repository: repository
      ? {
          id: bindingId(repository.id),
          name: text(repository.name),
          active_branch: text(repository.active_branch),
          default_branch: text(repository.default_branch),
        }
      : null,
  }
}
export function readBindingList(value: unknown): { rows: BindingRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const response = checkBindingResponse(value)
  if (!Array.isArray(response.data)) throw new Error('项目绑定列表格式不正确')
  const rows = response.data.map(readBinding)
  if (new Set(rows.map((row) => row.id)).size !== rows.length) throw new Error('项目绑定重复')
  return { rows, total: count(response.totalSize) }
}
export function emptyBindingDraft(): BindingDraft {
  return {
    project_product: null,
    repository: null,
    file_name: '',
    name: '',
    auto_type: null,
    test_dir: [],
    pytest_config_path: '',
  }
}
export function bindingDraft(record: BindingRecord): BindingDraft {
  return {
    project_product: record.project_product?.id ?? null,
    repository: record.repository?.id ?? null,
    file_name: record.file_name,
    name: record.name,
    auto_type: record.auto_type,
    test_dir: [...record.test_dir],
    pytest_config_path: record.pytest_config_path,
  }
}
export function bindingPayload(
  draft: BindingDraft,
  options: ProjectProductOption[],
  id: number | null
) {
  const value = Array.isArray(draft.project_product)
    ? draft.project_product.at(-1)
    : draft.project_product
  const project_product = bindingId(value)
  if (
    !options.some((project) =>
      project.children?.some((product) => String(product.value) === String(project_product))
    )
  )
    throw new Error('请选择有效的项目/产品')
  if (
    !draft.name.trim() ||
    !draft.file_name.trim() ||
    draft.auto_type == null ||
    !draft.test_dir.length
  )
    throw new Error('请完整填写必填项')
  const payload = {
    project_product,
    repository: bindingId(draft.repository),
    file_name: draft.file_name,
    name: draft.name,
    auto_type: bindingId(draft.auto_type),
    test_dir: stringList(draft.test_dir),
    pytest_config_path: draft.pytest_config_path,
  }
  return id === null ? payload : { ...payload, id }
}
export function readDirectories(value: unknown): DirectoryEntry[] {
  const response = checkBindingResponse(value)
  if (!Array.isArray(response.data)) throw new Error('目录列表格式不正确')
  return response.data.map((value) => {
    const row = object(value)
    if (
      typeof row.value !== 'string' ||
      !row.value ||
      row.value.split('/').some((part) => part === '..')
    )
      throw new Error('目录路径不正确')
    return { value: row.value, file_count: count(row.file_count ?? 0) }
  })
}
export function readRepositories(value: unknown): Array<{ value: number; label: string }> {
  const response = checkBindingResponse(value)
  if (!Array.isArray(response.data)) throw new Error('仓库列表格式不正确')
  return response.data.map((value) => {
    const row = object(value)
    if (typeof row.name !== 'string') throw new Error('仓库名称不正确')
    return { value: bindingId(row.id), label: row.name }
  })
}
export function directoryTree(
  entries: DirectoryEntry[],
  configured: string[] = [],
  tests = false
): DirectoryOption[] {
  const roots: DirectoryOption[] = [],
    nodes = new Map<string, DirectoryOption>()
  const ensure = (directory: string): DirectoryOption | undefined => {
    if (directory === '.') return undefined
    let children = roots,
      current = '',
      node: DirectoryOption | undefined
    for (const segment of directory.split('/').filter(Boolean)) {
      current = current ? `${current}/${segment}` : segment
      node = nodes.get(current)
      if (!node) {
        node = { value: current, label: segment, children: [], fileCount: 0 }
        nodes.set(current, node)
        children.push(node)
      }
      children = node.children!
    }
    return node
  }
  for (const entry of entries) {
    ensure(entry.value)
    let current = ''
    for (const part of entry.value.split('/').filter(Boolean)) {
      current = current ? `${current}/${part}` : part
      const node = nodes.get(current)
      if (node) node.fileCount = (node.fileCount ?? 0) + entry.file_count
    }
  }
  for (const directory of configured) {
    const node = ensure(directory)
    if (node && !entries.some((entry) => entry.value === directory) && !node.fileCount) {
      node.stale = true
      node.label += '（当前配置，当前分支未发现）'
    }
  }
  function finish(options: DirectoryOption[]): void {
    options.sort((a, b) => a.value.localeCompare(b.value))
    for (const option of options) {
      if (option.children?.length) finish(option.children)
      else delete option.children
    }
  }
  finish(roots)
  const root =
    entries.some((entry) => entry.value === '.' || (tests && entry.file_count > 0)) ||
    configured.includes('.')
  return [...(root ? [{ label: '项目根目录', value: '.' }] : []), ...roots]
}
