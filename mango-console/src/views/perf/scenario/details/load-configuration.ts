import { createDefaultLoadConfiguration, loadProfileHints } from './config'
import type { LoadConfiguration, LoadConfigurationChange, LoadConfigurationDraft, LoadProfile, LoadType } from './types'

const numericFields = [
  'duration_seconds', 'target_users', 'target_rate', 'preallocated_vus', 'max_vus',
  'spawn_rate', 'user_wait_min_ms', 'user_wait_max_ms', 'total_iterations', 'start_users',
  'step_users', 'step_interval_seconds', 'ramp_seconds', 'hold_seconds', 'baseline_seconds', 'recovery_seconds',
] as const
const editorDefaults = ['total_iterations', 'start_users', 'step_users', 'step_interval_seconds',
  'ramp_seconds', 'hold_seconds', 'baseline_seconds', 'recovery_seconds'] as const

export function isLoadProfile(value: unknown): value is LoadProfile {
  return typeof value === 'string' && Object.prototype.hasOwnProperty.call(loadProfileHints, value)
}

export function isRateLoadProfile(profile: LoadProfile): boolean {
  return profile === 'constant_arrival_rate' || profile === 'constant_iteration_rate'
}

export function loadTypeForProfile(profile: LoadProfile): LoadType {
  return !isRateLoadProfile(profile) ? 'concurrency' : profile === 'constant_arrival_rate' ? 'arrival_rate' : 'iteration_rate'
}

export function readLoadConfiguration(value: unknown, loadType: LoadType = 'concurrency'): LoadConfiguration {
  const result = createDefaultLoadConfiguration(loadType)
  if (value === null || value === undefined) return { ...result, duration_seconds: 0 }
  if (typeof value !== 'object' || Array.isArray(value)) throw new Error('负载配置格式不正确')
  const record = value as Record<string, unknown>
  if (record.name !== undefined) {
    if (typeof record.name !== 'string') throw new Error('负载配置名称格式不正确')
    result.name = record.name
  }
  if (record.profile !== undefined) {
    if (!isLoadProfile(record.profile)) throw new Error('负载方案格式不正确')
    result.profile = record.profile
  }
  for (const key of numericFields) {
    const input = record[key]
    if (!Object.prototype.hasOwnProperty.call(record, key)) continue
    if (input === null || input === undefined) { result[key] = null; continue }
    const number = typeof input === 'number' ? input : typeof input === 'string' && input.trim() ? Number(input) : NaN
    if (!Number.isFinite(number)) throw new Error('负载配置数值格式不正确')
    result[key] = number
  }
  if (record.rate_time_unit !== undefined) {
    if (record.rate_time_unit !== null && record.rate_time_unit !== 'second' && record.rate_time_unit !== 'minute')
      throw new Error('速率单位格式不正确')
    result.rate_time_unit = record.rate_time_unit
  }
  if (record.ramp_type !== undefined) {
    if (record.ramp_type !== 'linear' && record.ramp_type !== 'step') throw new Error('爬坡方式格式不正确')
    result.ramp_type = record.ramp_type
  }
  return result
}

export function createLoadDraft(value: unknown, loadType: LoadType): LoadConfigurationDraft {
  const defaults = createDefaultLoadConfiguration(loadType)
  const result = value === undefined || value === null ? defaults : readLoadConfiguration(value, loadType)
  for (const key of editorDefaults) if (result[key] === null) result[key] = defaults[key]
  return {
    name: result.name, profile: result.profile, ramp_type: result.ramp_type,
    rate_time_unit: result.rate_time_unit ?? undefined,
    duration_seconds: result.duration_seconds ?? undefined,
    target_users: result.target_users ?? undefined, target_rate: result.target_rate ?? undefined,
    preallocated_vus: result.preallocated_vus ?? undefined, max_vus: result.max_vus ?? undefined,
    spawn_rate: result.spawn_rate ?? undefined, user_wait_min_ms: result.user_wait_min_ms ?? undefined,
    user_wait_max_ms: result.user_wait_max_ms ?? undefined, total_iterations: result.total_iterations ?? undefined,
    start_users: result.start_users ?? undefined, step_users: result.step_users ?? undefined,
    step_interval_seconds: result.step_interval_seconds ?? undefined, ramp_seconds: result.ramp_seconds ?? undefined,
    hold_seconds: result.hold_seconds ?? undefined, baseline_seconds: result.baseline_seconds ?? undefined,
    recovery_seconds: result.recovery_seconds ?? undefined,
  }
}

export function loadDuration(value: LoadConfiguration | LoadConfigurationDraft): number {
  if (value.profile === 'staircase')
    return Math.ceil(Number(value.target_users) / Math.max(1, Number(value.step_users))) * Number(value.step_interval_seconds) + Number(value.hold_seconds)
  if (value.profile === 'linear_ramp') return Number(value.ramp_seconds) + Number(value.hold_seconds)
  if (value.profile === 'spike') return Number(value.baseline_seconds) + Number(value.ramp_seconds) + Number(value.hold_seconds) + Number(value.recovery_seconds)
  return Number(value.duration_seconds)
}

function integer(value: number | null, label: string, min = 1, max = 1_000_000_000): void {
  if (value === null || !Number.isSafeInteger(value) || value < min || value > max)
    throw new Error(`${label}必须为 ${min}～${max} 之间的整数`)
}

function integralRatePerMinute(value: number, unit: LoadConfiguration['rate_time_unit']): boolean {
  // 与后端 Decimal 保持一致，不能把接近整数但实际有小数的速率静默取整。
  const [coefficient, exponent = '0'] = String(value).toLowerCase().split('e')
  const [whole, fraction = ''] = coefficient.split('.')
  const places = fraction.length - Number(exponent)
  if (places <= 0) return true
  const digits = whole + fraction
  const multiplier = unit === 'minute' ? 1 : 60
  let product = '', carry = 0
  for (let index = digits.length - 1; index >= 0; index--) {
    const current = Number(digits[index]) * multiplier + carry
    product = String(current % 10) + product
    carry = Math.floor(current / 10)
  }
  if (carry) product = String(carry) + product
  return !/[1-9]/.test(product.slice(-places))
}

export function commitLoadDraft(draft: LoadConfiguration | LoadConfigurationDraft, executorCount: number): LoadConfigurationChange {
  const value = readLoadConfiguration(draft, loadTypeForProfile(draft.profile))
  integer(executorCount, '执行器数量')
  if (!value.name.trim() || value.name.trim().length > 64) throw new Error('配置名称不能为空且不能超过 64 字')
  integer(value.user_wait_min_ms, '最小迭代等待', 0, 3600000)
  integer(value.user_wait_max_ms, '最大迭代等待', 0, 3600000)
  if (Number(value.user_wait_min_ms) > Number(value.user_wait_max_ms)) throw new Error('最大迭代等待不能小于最小值')
  if (isRateLoadProfile(value.profile)) {
    if (value.target_rate === null || !Number.isFinite(value.target_rate) || value.target_rate <= 0 || value.target_rate > 10_000_000)
      throw new Error('目标速率必须在 0～10000000 之间')
    const perMinute = value.target_rate * (value.rate_time_unit === 'minute' ? 1 : 60)
    if (perMinute < executorCount || !integralRatePerMinute(value.target_rate, value.rate_time_unit))
      throw new Error('每分钟目标速率必须是整数且不能低于执行器数量')
    integer(value.preallocated_vus, '预分配 VU')
    integer(value.max_vus, '最大 VU')
    if (Number(value.max_vus) < Number(value.preallocated_vus) || Number(value.preallocated_vus) < executorCount)
      throw new Error('最大 VU 不得小于预分配 VU，预分配 VU 不得少于执行器数')
    value.target_users = null
    value.rate_time_unit ??= 'second'
  } else {
    integer(value.target_users, '目标并发')
    if (Number(value.target_users) < executorCount) throw new Error('目标并发不能少于执行器数量')
    value.target_rate = value.rate_time_unit = value.preallocated_vus = value.max_vus = null
    if (value.profile === 'fixed_iterations') {
      integer(value.total_iterations, 'Case 执行次数')
      if (Number(value.total_iterations) < Number(value.target_users)) throw new Error('Case 执行次数不能少于目标并发用户数')
    } else if (value.profile === 'staircase') {
      integer(value.step_users, '每阶增加并发')
      integer(value.step_interval_seconds, '阶梯间隔')
      integer(value.hold_seconds, '峰值保持时间', 0)
      if (Number(value.step_users) < executorCount || Math.ceil(Number(value.target_users) / Number(value.step_users)) > 99)
        throw new Error('每阶增加并发不能少于执行器数，且最多 99 阶')
    } else if (value.profile === 'linear_ramp' || value.profile === 'spike') {
      integer(value.start_users, '起始并发', value.profile === 'spike' ? executorCount : 0)
      integer(value.ramp_seconds, '爬坡时间')
      integer(value.hold_seconds, '峰值保持时间', value.profile === 'spike' ? 1 : 0)
      if (Number(value.start_users) >= Number(value.target_users)) throw new Error('起始并发必须小于目标并发')
      if (value.profile === 'spike') {
        integer(value.baseline_seconds, '基线时间')
        integer(value.recovery_seconds, '恢复时间')
      }
    }
  }
  const duration = loadDuration(value)
  integer(duration, '总时长', 1, 86400)
  value.duration_seconds = duration
  return { loadType: loadTypeForProfile(value.profile), configuration: value }
}
