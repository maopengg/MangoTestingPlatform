import { createDefaultPerformanceGoal } from './config'
import type { PerformanceGoal, PerformanceGoalDraft, PerformanceGoalPayload, PerformanceGoalTemplateKey } from './types'

function numericGoal(value: unknown, label: string, min: number, max = Infinity): number {
  const number = typeof value === 'number'
    ? value
    : typeof value === 'string' && value.trim() !== '' ? Number(value) : NaN
  if (!Number.isFinite(number) || number < min || number > max) {
    throw new Error(`${label}格式或范围不正确`)
  }
  return number
}

export function performanceGoalValidationMessage(goal: PerformanceGoalDraft): string {
  try {
    const p95 = numericGoal(goal.p95_ms, 'P95 响应时间', 1)
    if (!Number.isSafeInteger(p95)) return 'P95 响应时间必须为正整数'
    numericGoal(goal.error_rate_percent, '错误率', 0, 100)
    numericGoal(goal.load_achievement_rate_percent, '负载达成率', 0, 100)
    return ''
  } catch (error) {
    return error instanceof Error ? error.message : '性能目标格式不正确'
  }
}

export function isRecommendedPerformanceGoal(goal: PerformanceGoalDraft): boolean {
  if (performanceGoalValidationMessage(goal)) return false
  const recommended = createDefaultPerformanceGoal()
  return goal.p95_ms === recommended.p95_ms &&
    goal.error_rate_percent === recommended.error_rate_percent &&
    goal.load_achievement_rate_percent === recommended.load_achievement_rate_percent
}

export function performanceGoalFromApi(value?: unknown): PerformanceGoal {
  const goal = createDefaultPerformanceGoal()
  if (value === undefined || value === null) return goal
  if (typeof value !== 'object' || Array.isArray(value)) throw new Error('性能目标格式不正确')
  // 缺失字段沿用服务端默认值；显式无效值不得被 Number(null/false) 转成零。
  if ('p95_ms' in value && value.p95_ms !== undefined)
    goal.p95_ms = numericGoal(value.p95_ms, 'P95 响应时间', 1)
  if ('max_error_rate' in value && value.max_error_rate !== undefined)
    goal.error_rate_percent = numericGoal(value.max_error_rate, '错误率', 0, 1) * 100
  if ('min_load_achievement_rate' in value && value.min_load_achievement_rate !== undefined)
    goal.load_achievement_rate_percent = numericGoal(value.min_load_achievement_rate, '负载达成率', 0, 1) * 100
  const message = performanceGoalValidationMessage(goal)
  if (message) throw new Error(message)
  return goal
}

export function performanceGoalToPayload(
  goal: PerformanceGoalDraft,
  templateKey: PerformanceGoalTemplateKey
): PerformanceGoalPayload {
  const message = performanceGoalValidationMessage(goal)
  if (message) throw new Error(message)
  if (templateKey !== 'recommended' && templateKey !== 'custom') throw new Error('性能目标模板不正确')
  return {
    template_key: templateKey,
    p95_ms: Number(goal.p95_ms),
    max_error_rate: Number(goal.error_rate_percent) / 100,
    min_load_achievement_rate: Number(goal.load_achievement_rate_percent) / 100,
  }
}
