export const effectivenessQualityThresholds = {
  highRiskPassRate: 90,
  healthyPassRate: 98,
  healthyFlakyRate: 1,
}

export const componentInsightKeys = ['overview', 'status', 'modules', 'benefits'] as const
export const chartInsightKeys = [
  'trend', 'environment', 'task_type', 'coverage_scope', 'module_risk', 'issue_pareto',
  'environment_task_matrix', 'module_change', 'automation_type', 'task_health', 'failed_case_ranking',
] as const
export const aiInsightKeys = [...componentInsightKeys, ...chartInsightKeys]

export type PeriodPreset = 'natural_week' | 'natural_two_weeks' | 'natural_month' | 'natural_quarter'
  | 'recent_2_days' | 'recent_7_days' | 'recent_14_days' | 'recent_month' | 'recent_3_months'
export const defaultPeriodPreset: PeriodPreset = 'recent_7_days'
export const periodPresetOptions: Array<{ label: string; value: PeriodPreset }> = [
  { label: '自然周', value: 'natural_week' }, { label: '自然 2 周', value: 'natural_two_weeks' },
  { label: '自然月', value: 'natural_month' }, { label: '自然季度', value: 'natural_quarter' },
  { label: '最近 2 天', value: 'recent_2_days' }, { label: '最近 7 天', value: 'recent_7_days' },
  { label: '最近 14 天', value: 'recent_14_days' }, { label: '最近 1 个月', value: 'recent_month' },
  { label: '最近 3 个月', value: 'recent_3_months' },
]
