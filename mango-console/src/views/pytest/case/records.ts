import { batchId, batchSuccess, readBatchRows } from './batch-editor'
import type { BatchOptionId, BatchPublication, BatchValues, BatchUserOption } from './batch-editor'

export interface CaseRecord extends Omit<BatchValues, 'module' | 'case_people'> {
  id: number
  module: { id: number; name: string; full_path: string } | null
  case_people: { id: number } | null
  project_product: { id: number; project_product: { id: number; name: string; project: { id: number; name: string } | null } | null } | null
  publication_status: BatchPublication
  status: number
  file_status: number
  source_status: number
  file_path: string
  feature_file_path: string | null
  missing_since: string | null
}
export interface DirectoryNode {
  key: string; title: string; type: 'repository' | 'project' | 'directory' | 'file'
  path: string; breadcrumb: string[]; repository_id: number | null; pytest_project_id?: number
  case_id?: number; case_count: number; count?: number; source_status?: number; asset_status?: number; children: DirectoryNode[]
}
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('用例响应格式不正确')
  return value as Record<string, unknown>
}
function text(value: unknown): string { if (typeof value !== 'string') throw new Error('用例文本格式不正确'); return value }
function integer(value: unknown): number { if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('用例数值格式不正确'); return value }
export function caseRecord(value: unknown): CaseRecord {
  const raw = object(value), id = batchId(raw.id), row = readBatchRows({ code: 200, data: [raw] }, [id])[0]
  const module = raw.module == null ? null : object(raw.module)
  const product = raw.project_product == null ? null : object(raw.project_product)
  const target = product?.project_product == null ? null : object(product.project_product)
  const project = target?.project == null ? null : object(target.project)
  return { id, name: row.name, level: row.level, asset_status: row.asset_status, scenario_layer: row.scenario_layer, scenario_type: row.scenario_type,
    scenario_tags: [...row.scenario_tags], scenario_description: row.scenario_description, publication_status: row.publication_status,
    module: module ? { id: batchId(module.id), name: text(module.name), full_path: text(module.full_path) } : null,
    case_people: row.case_people === null ? null : { id: batchId(row.case_people) },
    project_product: product ? { id: batchId(product.id), project_product: target ? { id: batchId(target.id), name: text(target.name), project: project ? { id: batchId(project.id), name: text(project.name) } : null } : null } : null,
    status: integer(raw.status), file_status: integer(raw.file_status), source_status: integer(raw.source_status), file_path: text(raw.file_path),
    feature_file_path: raw.feature_file_path == null ? null : text(raw.feature_file_path), missing_since: raw.missing_since == null ? null : text(raw.missing_since) }
}
export function readCase(value: unknown, id: number): CaseRecord {
  const data = batchSuccess(value).data
  if (!Array.isArray(data) || data.length !== 1) throw new Error('未返回唯一的当前用例')
  const row = caseRecord(data[0])
  if (row.id !== id) throw new Error('返回了其他用例')
  return row
}
export function readPublication(value: unknown, id: number, expected?: BatchPublication): Pick<CaseRecord, 'id' | 'publication_status' | 'asset_status'> {
  const data = object(batchSuccess(value).data)
  if (batchId(data.id) !== id || !['unpublished', 'prepublished', 'published'].includes(String(data.publication_status)) || (expected !== undefined && data.publication_status !== expected)) throw new Error('发布响应不正确')
  return { id, publication_status: data.publication_status as BatchPublication, asset_status: integer(data.asset_status) }
}
export function caseUsers(value: unknown): BatchUserOption[] {
  const data = batchSuccess(value).data
  if (!Array.isArray(data)) throw new Error('用户选项格式不正确')
  return data.map(value => { const row = object(value); return { key: batchId(row.key), title: text(row.title) } })
}
export function readDirectory(value: unknown): DirectoryNode[] {
  const data = batchSuccess(value).data, keys = new Set<string>(), cases = new Set<number>()
  function list(value: unknown): DirectoryNode[] {
    if (!Array.isArray(value)) throw new Error('目录结构格式不正确')
    return value.map(value => {
      const raw = object(value), key = text(raw.key)
      if (!key || keys.has(key) || !['repository', 'project', 'directory', 'file'].includes(String(raw.type))) throw new Error('目录节点不正确')
      keys.add(key)
      if (!Array.isArray(raw.breadcrumb)) throw new Error('目录路径格式不正确')
      const node: DirectoryNode = { key, title: text(raw.title), type: raw.type as DirectoryNode['type'], path: text(raw.path), breadcrumb: raw.breadcrumb.map(text),
        repository_id: raw.repository_id == null ? null : batchId(raw.repository_id), case_count: integer(raw.case_count), children: list(raw.children) }
      if (raw.pytest_project_id != null) node.pytest_project_id = batchId(raw.pytest_project_id)
      if (raw.case_id != null) { node.case_id = batchId(raw.case_id); if (cases.has(node.case_id)) throw new Error('目录包含重复用例'); cases.add(node.case_id) }
      if (node.type === 'file' && node.case_id === undefined) throw new Error('文件未关联用例')
      if (raw.source_status != null) node.source_status = integer(raw.source_status)
      if (raw.asset_status != null) node.asset_status = integer(raw.asset_status)
      if (raw.count != null) node.count = integer(raw.count)
      return node
    })
  }
  return list(data)
}
export function firstFile(nodes: DirectoryNode[]): DirectoryNode | null {
  for (const node of nodes) { if (node.type === 'file') return node; const child = firstFile(node.children); if (child) return child }
  return null
}
export function findFile(nodes: DirectoryNode[], id: number): DirectoryNode | null {
  for (const node of nodes) { if (node.type === 'file' && node.case_id === id) return node; const child = findFile(node.children, id); if (child) return child }
  return null
}
export function directoryCaseIds(node: DirectoryNode): number[] { return node.type === 'file' ? [batchId(node.case_id)] : node.children.flatMap(directoryCaseIds) }
export function projectNodes(nodes: DirectoryNode[]): DirectoryNode[] { return nodes.flatMap(node => [...(node.type === 'project' ? [node] : []), ...projectNodes(node.children)]) }
export function optionalCaseId(value: unknown): number | null { try { return value == null || value === '' ? null : batchId(Array.isArray(value) ? value[0] : value) } catch { return null } }
export function enumTitle(options: Array<{ key: BatchOptionId; title: string }> | undefined | null, value: BatchOptionId | null): string { return options?.find(option => String(option.key) === String(value))?.title || '-' }
