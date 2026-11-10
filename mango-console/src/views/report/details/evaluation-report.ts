import type { ExecutionSummary } from '@/views/evaluation/types'
import { reportIdentifier, reportObject } from './report-overview'
import { reportRecords } from './report-rows'

interface EvaluationMetricRow {
  key: string
  grader_key: string
  version: string
  average_score: number | string
  counts: string
  pass_rate_text: string
}
export interface EvaluationReportView {
  key: string
  name: string
  status: number | null
  executionNo: string
  datasetId: string
  datasetVersion: string
  targetText: string
  total: number | null
  valid: number | null
  invalid: number | null
  averageScore: number | null
  validRate: string
  effectPassRate: string
  errorMessage: string
  memory: { correct: string; hallucination: string; omission: string } | null
  aiSummary: Required<NonNullable<ExecutionSummary['ai_summary']>> | null
  metrics: EvaluationMetricRow[]
}
const text = (value: unknown) => typeof value === 'string' ? value : ''
const numeric = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null
const strings = (value: unknown): string[] => Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : []
const identifier = (value: unknown) => reportIdentifier(value) ?? '—'
export function evaluationPercent(value: unknown): string {
  const number = numeric(value)
  return number === null ? '—' : `${(number * 100).toFixed(1)}%`
}
export function evaluationReportRows(value: unknown): EvaluationReportView[] {
  return reportRecords(value).map((record, index) => {
    const payload = reportObject(record.children), summary = reportObject(payload?.summary)
    const dataset = reportObject(payload?.dataset), target = reportObject(payload?.target), version = reportObject(target?.version_ref)
    const memory = reportObject(summary?.memory_qa), rates = reportObject(memory?.rates)
    const ai = reportObject(summary?.ai_summary), names = reportObject(payload?.grader_names)
    const metrics = Object.entries(reportObject(summary?.metrics) ?? {}).flatMap(([key, value]) => {
      const metric = reportObject(value)
      if (!metric) return []
      const variants = Array.isArray(metric.variants) ? reportRecords(metric.variants) : [metric]
      return variants.map((entry, entryIndex): EvaluationMetricRow => {
        const grader = text(entry.grader_key) || key
        return {
          key: `${key}-${entryIndex}`, grader_key: text(names?.[grader]) || grader,
          version: `V${identifier(entry.grader_version)}`, average_score: numeric(entry.average_score) ?? '—',
          counts: `${numeric(entry.passed) ?? '—'} / ${numeric(entry.total) ?? '—'}`,
          pass_rate_text: evaluationPercent(entry.pass_rate),
        }
      })
    })
    return {
      key: `${identifier(record.id)}-${index}`, name: text(record.case_name) || text(record.name),
      status: numeric(record.status), executionNo: text(payload?.execution_no) || '—',
      datasetId: identifier(dataset?.id), datasetVersion: identifier(dataset?.version_no),
      targetText: target?.type === 'script' ? 'Python 脚本'
        : `接口 #${identifier(target?.ref_id)} · ${version?.kind === 'api_info_release' ? '发布' : '修订'} #${identifier(version?.id)}`,
      total: numeric(record.case_sum), valid: numeric(summary?.valid), invalid: numeric(summary?.invalid),
      averageScore: numeric(summary?.average_score), validRate: evaluationPercent(summary?.valid_rate),
      effectPassRate: evaluationPercent(summary?.effect_pass_rate), errorMessage: text(payload?.error_message),
      memory: memory ? { correct: evaluationPercent(rates?.correct), hallucination: evaluationPercent(rates?.hallucination), omission: evaluationPercent(rates?.omission) } : null,
      aiSummary: ai ? { status: text(ai.status), overview: text(ai.overview), findings: strings(ai.findings), recommendations: strings(ai.recommendations), error_message: text(ai.error_message) } : null,
      metrics,
    }
  })
}
