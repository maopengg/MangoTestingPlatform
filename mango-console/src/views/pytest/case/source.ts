import { batchId, batchSuccess } from './batch-editor'

export type PytestFileType = 'py' | 'feature'
export interface SourceSnapshot { path: string; content: string; commitHash: string | null; contentHash: string }
export interface CodeTarget { id: number; name: string; featurePath: string | null; executable: boolean }
export interface PytestMethodNode {
  nodeid: string
  node_type: 'file' | 'class' | 'method' | 'parameter'
  class_name: string | null
  method_name: string
  parameter_id: string | null
  line_number: number | null
}
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('源码响应格式不正确')
  return value as Record<string, unknown>
}
function text(value: unknown): string { if (typeof value !== 'string') throw new Error('源码字段格式不正确'); return value }
function nonempty(value: unknown): string { const result = text(value); if (!result.length) throw new Error('源码字段不能为空'); return result }
function optionalText(value: unknown): string | null { return value == null ? null : text(value) }
export function sourceSnapshot(value: unknown): SourceSnapshot {
  const data = object(batchSuccess(value).data)
  return { path: nonempty(data.path), content: text(data.content), commitHash: optionalText(data.commit_hash), contentHash: nonempty(data.content_hash) }
}
export function codeTarget(value: unknown): CodeTarget {
  const row = object(value)
  const status = (value: unknown) => { if (typeof value !== 'number' || !Number.isSafeInteger(value)) throw new Error('用例状态格式不正确'); return value }
  const source = status(row.source_status ?? 0), asset = status(row.asset_status ?? (row.publication_status === 'published' ? 1 : 0))
  return { id: batchId(row.id), name: text(row.name), featurePath: optionalText(row.feature_file_path), executable: ![2, 3, 4].includes(source) && ![2, 3, 4].includes(asset) }
}
export function methodNodes(value: unknown): PytestMethodNode[] {
  const data = batchSuccess(value).data
  if (!Array.isArray(data)) throw new Error('方法列表格式不正确')
  const seen = new Set<string>()
  return data.map(value => {
    const row = object(value), nodeid = nonempty(row.nodeid)
    if (seen.has(nodeid)) throw new Error('方法列表包含重复节点')
    seen.add(nodeid)
    if (!['file', 'class', 'method', 'parameter'].includes(String(row.node_type))) throw new Error('方法类型不正确')
    if (row.line_number != null && (typeof row.line_number !== 'number' || !Number.isSafeInteger(row.line_number) || row.line_number < 1)) throw new Error('方法行号不正确')
    return { nodeid, node_type: row.node_type as PytestMethodNode['node_type'], class_name: optionalText(row.class_name),
      method_name: nonempty(row.method_name), parameter_id: optionalText(row.parameter_id), line_number: row.line_number == null ? null : row.line_number as number }
  })
}
export function methodTarget(node: PytestMethodNode) {
  return { nodeid: node.nodeid, node_type: node.node_type, class_name: node.class_name, method_name: node.method_name, parameter_id: node.parameter_id }
}
export function unboundFeature(error: unknown): boolean {
  // 后端 PYTEST_FILE_BINDING_INVALID；网络、鉴权或其他读取失败不能据此判为没有文件。
  return error != null && typeof error === 'object' && 'code' in error && error.code === 32001
}
export function executionEnvironment(value: unknown): number {
  if ((typeof value !== 'number' && (typeof value !== 'string' || !/^\d+$/.test(value))) || !Number.isSafeInteger(Number(value)) || Number(value) < 0) throw new Error('执行环境不正确')
  return Number(value)
}
