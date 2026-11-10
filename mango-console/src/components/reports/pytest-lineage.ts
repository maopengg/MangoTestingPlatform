import { reportObject, reportText } from './pytest-report'

export interface LineageNode {
  id: string
  kind: string
  label: string
  source: string
  entity_type: string
  entity_id: string | number | null
  status: string
  data: unknown
}
export interface LineageEdge { source: string; target: string; relation: string }

function id(value: unknown): string {
  return typeof value === 'string' ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : ''
}

export function readLineage(value: unknown) {
  const graph = reportObject(value), summary = reportObject(graph?.summary), seen = new Set<string>()
  const nodes: LineageNode[] = []
  let malformed = value != null && !graph
  if (graph?.nodes != null && !Array.isArray(graph.nodes)) malformed = true
  if (graph && Array.isArray(graph.nodes)) graph.nodes.forEach(value => {
    const row = reportObject(value), key = id(row?.id)
    if (!row || !key || seen.has(key)) { malformed = true; return }
    seen.add(key)
    nodes.push({ id: key, kind: reportText(row.kind), label: reportText(row.label), source: reportText(row.source), entity_type: reportText(row.entity_type), entity_id: typeof row.entity_id === 'string' || typeof row.entity_id === 'number' ? row.entity_id : null, status: reportText(row.status), data: row.data })
  })
  const edges: LineageEdge[] = []
  if (graph?.edges != null && !Array.isArray(graph.edges)) malformed = true
  if (graph && Array.isArray(graph.edges)) graph.edges.forEach(value => {
    const row = reportObject(value), source = id(row?.source), target = id(row?.target)
    if (!row || !seen.has(source) || !seen.has(target)) { malformed = true; return }
    edges.push({ source, target, relation: reportText(row.relation) })
  })
  const count = (value: unknown) => typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : null
  return { nodes, edges, malformed, summary: { factories: count(summary?.factories), operations: count(summary?.operations), entities: count(summary?.entities), relations: count(summary?.relations) } }
}
