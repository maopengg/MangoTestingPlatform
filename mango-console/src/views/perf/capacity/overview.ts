import type { CapacityExecutor, CapacityOverview } from './types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid capacity response')
  return value as Record<string, unknown>
}

function numeric(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) throw new Error('Invalid capacity number')
  return value
}

function count(value: unknown): number {
  const result = numeric(value)
  if (!Number.isSafeInteger(result)) throw new Error('Invalid capacity count')
  return result
}

function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid capacity text')
  return value
}

function executor(value: unknown): CapacityExecutor {
  const row = object(value)
  if (typeof row.online !== 'boolean') throw new Error('Invalid executor state')
  return {
    fingerprint: text(row.fingerprint), executor_name: text(row.executor_name), online: row.online,
    engine: text(row.engine), engine_version: row.engine_version == null ? null : text(row.engine_version),
    safe_vus: numeric(row.safe_vus), safe_rps: numeric(row.safe_rps),
    reserved_vus: numeric(row.reserved_vus), reserved_rps: numeric(row.reserved_rps),
    available_vus: numeric(row.available_vus), available_rps: numeric(row.available_rps),
  }
}

export function readCapacityOverview(value: unknown): CapacityOverview {
  const response = object(value)
  if (response.code !== 200) throw new Error('Capacity request failed')
  const data = object(response.data), summary = object(data.summary), defaults = object(data.defaults)
  if (!Array.isArray(data.rows)) throw new Error('Invalid capacity rows')
  const factor = numeric(defaults.safety_factor)
  if (factor > 1) throw new Error('Invalid safety factor')
  return {
    summary: {
      executor_count: count(summary.executor_count), online_count: count(summary.online_count),
      available_vus: numeric(summary.available_vus), available_rps: numeric(summary.available_rps),
    },
    defaults: { safe_vus: numeric(defaults.safe_vus), safe_rps: numeric(defaults.safe_rps), safety_factor: factor },
    rows: data.rows.map(executor),
  }
}

const formatter = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 })
export function formatCapacity(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? '—' : formatter.format(value)
}
