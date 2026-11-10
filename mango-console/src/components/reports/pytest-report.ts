export interface ReportAttachment { name: string; type: string; source: string }
export interface ReportStep { name: string; context: string; phase: string; attachments: ReportAttachment[] }

export function reportObject(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}

export function reportText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function attachments(value: unknown): ReportAttachment[] {
  if (!Array.isArray(value)) return []
  return value.flatMap(value => {
    const item = reportObject(value)
    return item ? [{ name: reportText(item.name), type: reportText(item.type), source: reportText(item.source) }] : []
  })
}

export function readPytestReport(value: unknown) {
  const row = reportObject(value)
  const fixtures = reportObject(row?.fixtures), details = reportObject(row?.statusDetails)
  const steps: ReportStep[] = []
  const seen = new WeakSet<object>()
  const walk = (items: unknown, phase: string) => {
    const pending = (Array.isArray(items) ? [...items].reverse() : []).map(value => ({ value, parent: '' }))
    while (pending.length) {
      const current = pending.pop()!, step = reportObject(current.value)
      if (!step || seen.has(step)) continue
      seen.add(step)
      const name = reportText(step.name), label = name || '未命名步骤'
      const context = current.parent ? `${current.parent} / ${label}` : label
      steps.push({ name, context, phase, attachments: attachments(step.attachments) })
      if (Array.isArray(step.steps)) {
        for (let index = step.steps.length - 1; index >= 0; index--) pending.push({ value: step.steps[index], parent: context })
      }
    }
  }
  walk(row?.steps, '')
  walk(fixtures?.befores, '前置')
  walk(fixtures?.afters, '清理')
  const labels = row && Array.isArray(row.labels) ? row.labels.flatMap(value => {
    const label = reportObject(value)
    return label && typeof label.name === 'string' && typeof label.value === 'string' ? [{ name: label.name, value: label.value }] : []
  }) : []
  return {
    uuid: reportText(row?.uuid), name: reportText(row?.name), fullName: reportText(row?.fullName), description: reportText(row?.description),
    status: typeof row?.status === 'number' || typeof row?.status === 'string' ? row.status : null,
    start: typeof row?.start === 'number' || typeof row?.start === 'string' ? row.start : null,
    statusDetails: { message: reportText(details?.message), trace: reportText(details?.trace) },
    attachments: attachments(row?.attachments), labels, steps,
  }
}

export function reportStatus(value: unknown) {
  const normalized = typeof value === 'string' ? value.toLowerCase() : value
  if (normalized === 1 || normalized === 'passed' || normalized === 'success') return { text: '测试通过', color: 'green' }
  if (normalized === 0 || normalized === 'failed' || normalized === 'broken') return { text: '测试失败', color: 'red' }
  if (normalized === 'skipped') return { text: '已跳过', color: 'orange' }
  if (normalized === 3 || normalized === 'running') return { text: '进行中', color: 'arcoblue' }
  return { text: '未测试', color: 'gray' }
}
