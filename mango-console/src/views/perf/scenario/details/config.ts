export interface PerformanceGoal {
  p95_ms: number
  error_rate_percent: number
  load_achievement_rate_percent: number
}

export type PerformanceGoalTemplateKey = 'recommended' | 'custom'

export const performanceGoalTemplateOptions = [
  { label: '系统推荐模板', value: 'recommended' },
  { label: '自定义目标', value: 'custom' },
]

export function createDefaultPerformanceGoal(): PerformanceGoal {
  return {
    p95_ms: 500,
    error_rate_percent: 1,
    load_achievement_rate_percent: 95,
  }
}

export function isRecommendedPerformanceGoal(goal: PerformanceGoal) {
  const recommended = createDefaultPerformanceGoal()
  return (
    Number(goal.p95_ms) === recommended.p95_ms &&
    Number(goal.error_rate_percent) === recommended.error_rate_percent &&
    Number(goal.load_achievement_rate_percent) === recommended.load_achievement_rate_percent
  )
}

export function performanceGoalFromApi(value?: any): PerformanceGoal {
  const goal = createDefaultPerformanceGoal()
  if (!value) return goal
  if (value.p95_ms !== undefined) goal.p95_ms = Number(value.p95_ms)
  if (value.max_error_rate !== undefined)
    goal.error_rate_percent = Number(value.max_error_rate) * 100
  if (value.min_load_achievement_rate !== undefined)
    goal.load_achievement_rate_percent = Number(value.min_load_achievement_rate) * 100
  return goal
}

export function performanceGoalToPayload(
  goal: PerformanceGoal,
  templateKey: PerformanceGoalTemplateKey
) {
  return {
    template_key: templateKey,
    p95_ms: Number(goal.p95_ms),
    max_error_rate: Number(goal.error_rate_percent) / 100,
    min_load_achievement_rate: Number(goal.load_achievement_rate_percent) / 100,
  }
}

export const assignmentModeTitles: Record<string, string> = {
  unique: '唯一分片',
  cyclic: '分片内循环',
  shared: '每节点共享',
}
