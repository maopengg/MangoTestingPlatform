export interface ReportTraceQuery {
  result_id?: number | string
  trace_id?: string
  test_suite_detail_id?: number | string
  case_id?: number | string
}

export interface ReportTrace {
  trace_id: string
  status: number | null
  duration_ms: number | null
  source_type: number | null
  started_at: string
  finished_at: string
  worker_name: string
}

export interface ReportTraceNode {
  id: string
  parent_step_id: string | null
  label: string
  step_type: string
  status: number | null
  duration_ms: number | null
  error_message: string
  detail_ref_type: string
  detail_ref_id: string | null
  summary: unknown
}

function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : null
}
function text(value: unknown) { return typeof value === 'string' ? value : '' }
function number(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null
}
function identifier(value: unknown): string | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? String(value) : null
  return typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null
}

export function reportTraceQuery(value: ReportTraceQuery): ReportTraceQuery | null {
  const query: ReportTraceQuery = {}
  for (const key of ['result_id', 'test_suite_detail_id', 'case_id'] as const) {
    const id = identifier(value[key])
    if (id !== null) query[key] = id
  }
  if (typeof value.trace_id === 'string' && value.trace_id.trim()) query.trace_id = value.trace_id.trim()
  return Object.keys(query).length ? query : null
}

export function parseReportTrace(response: unknown, query: ReportTraceQuery) {
  const envelope = object(response), payload = object(envelope?.data)
  if (!envelope || envelope.code !== 200 || !payload || !Array.isArray(payload.nodes)) {
    throw new Error('执行链路响应格式不正确')
  }
  if (payload.trace === null) {
    if (payload.nodes.length) throw new Error('执行链路缺少所属记录')
    return { trace: null, nodes: [] as ReportTraceNode[] }
  }
  const raw = object(payload.trace)
  if (!raw || !text(raw.trace_id) || (query.trace_id && query.trace_id !== raw.trace_id)) {
    throw new Error('执行链路记录不匹配')
  }
  const trace: ReportTrace = {
    trace_id: text(raw.trace_id), status: number(raw.status), duration_ms: number(raw.duration_ms),
    source_type: number(raw.source_type), started_at: text(raw.started_at),
    finished_at: text(raw.finished_at), worker_name: text(raw.worker_name),
  }
  const nodes = payload.nodes.map((value): ReportTraceNode => {
    const row = object(value), id = identifier(row?.id)
    if (!row || id === null) throw new Error('执行链路节点格式不正确')
    const parent = row.parent_step_id == null ? null : identifier(row.parent_step_id)
    if (row.parent_step_id != null && parent === null) throw new Error('执行链路父节点格式不正确')
    return {
      id, parent_step_id: parent, label: text(row.label), step_type: text(row.step_type),
      status: number(row.status), duration_ms: number(row.duration_ms),
      error_message: text(row.error_message), detail_ref_type: text(row.detail_ref_type),
      detail_ref_id: identifier(row.detail_ref_id), summary: row.summary === undefined ? {} : row.summary,
    }
  })
  const byId = new Map(nodes.map(node => [node.id, node]))
  if (byId.size !== nodes.length) throw new Error('执行链路包含重复节点')
  const checked = new Set<string>()
  for (const node of nodes) {
    let current: ReportTraceNode | undefined = node
    const visiting = new Set<string>()
    while (current && !checked.has(current.id)) {
      if (visiting.has(current.id)) throw new Error('执行链路包含循环父子关系')
      visiting.add(current.id)
      if (current.parent_step_id === null) break
      const parent = byId.get(current.parent_step_id)
      if (!parent) throw new Error('执行链路缺少父节点')
      current = parent
    }
    visiting.forEach(id => checked.add(id))
  }
  return { trace, nodes }
}

export function traceAncestors(node: ReportTraceNode, byId: Map<string, ReportTraceNode>) {
  const ancestors: ReportTraceNode[] = [], visited = new Set([node.id])
  let id = node.parent_step_id
  while (id !== null) {
    const parent = byId.get(id)
    if (!parent || visited.has(id)) break
    visited.add(id)
    ancestors.push(parent)
    id = parent.parent_step_id
  }
  return ancestors
}

export function traceStatusText(status: number | null) {
  return status === null ? '未知' : ({ 0: '失败', 1: '通过', 2: '待开始', 3: '进行中', 4: '清理失败', 5: '跳过' }[status] || '未知')
}
export function traceNodeClass(status: number | null) {
  return status === null ? '' : ({ 0: 'is-fail', 1: 'is-success', 2: 'is-pending', 3: 'is-running', 4: 'is-warning', 5: 'is-skip' }[status] || '')
}
export function traceSourceText(source: number | null) {
  return source === null ? '未知' : ({ 1: '测试报告', 2: '定时任务', 3: 'MCP', 4: '单 Case 执行', 5: '调试执行', 6: '其他' }[source] || '未知')
}
export function formatTraceSummary(value: unknown) {
  return JSON.stringify(value === undefined ? {} : value, null, 2)
}
