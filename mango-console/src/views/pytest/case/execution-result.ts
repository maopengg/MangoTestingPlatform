type ResultStatus = string | number | null

export interface ExecutionCase {
  key: string
  name: string
  description: string
  status: ResultStatus
  // Allure 的扩展结果仅透传给只读报告；列表状态不依赖这些动态字段。
  payload: Record<string, unknown>
}

interface SourceSummary {
  repositoryName: string
  projectName: string
  branch: string
  commit: string
  filePath: string
}

function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function identifier(value: unknown): string | number | null {
  return (typeof value === 'string' && value.length > 0) || (typeof value === 'number' && Number.isFinite(value))
    ? value : null
}

function sourceSummary(value: unknown): SourceSummary | null {
  const source = object(value)
  if (!source || !Object.keys(source).length) return null
  const projectId = identifier(source.pytest_project_id)
  return {
    repositoryName: text(source.repository_name) || '默认 Pytest 仓库',
    projectName: text(source.pytest_project_name) || (projectId !== null ? `项目 ${projectId}` : '-'),
    branch: text(source.branch) || '-',
    commit: (text(source.commit_hash) || '-').slice(0, 10),
    filePath: text(source.file_path),
  }
}

export function executionDetail(value: unknown) {
  const detail = object(value)
  const data = detail?.result_data
  const container = object(data)
  const rows = Array.isArray(data) ? data
    : container && Array.isArray(container.children) ? container.children
    : container && Array.isArray(container.cases) ? container.cases
    : container && Array.isArray(container.results) ? container.results
    : container && Object.keys(container).length ? [container] : []
  const cases: ExecutionCase[] = []
  let malformed = (value != null && !detail) || (data != null && !container && !Array.isArray(data))
  rows.forEach((value, index) => {
    if (value == null) return
    const row = object(value)
    if (!row) { malformed = true; return }
    const identity = text(row.uuid) || text(row.nodeid) || text(row.fullName) || text(row.name) || 'case'
    const status = typeof row.status === 'string' || (typeof row.status === 'number' && Number.isFinite(row.status)) ? row.status : null
    cases.push({
      key: `${identity}:${index}`,
      name: text(row.name) || text(row.title) || text(row.method_name) || `Case ${index + 1}`,
      description: text(row.fullName) || text(row.description) || text(row.nodeid),
      status,
      payload: row,
    })
  })
  return {
    id: identifier(detail?.id),
    present: detail !== null,
    cleaned: detail?.result_cleaned === true,
    source: sourceSummary(detail?.source_snapshot),
    cases,
    malformed: Boolean(malformed),
  }
}

export function resultStatus(status: ResultStatus) {
  const value = typeof status === 'string' ? status.toLocaleLowerCase() : ''
  if (status === 1 || value === 'passed' || value === 'success') return { text: '通过', color: 'green', tone: 'success' }
  if (status === 0 || value === 'failed' || value === 'broken') return { text: '失败', color: 'red', tone: 'danger' }
  if (value === 'skipped') return { text: '跳过', color: 'orange', tone: 'warning' }
  if (status === 3 || value === 'running') return { text: '进行中', color: 'arcoblue', tone: 'running' }
  return { text: '未知', color: 'gray', tone: 'neutral' }
}
