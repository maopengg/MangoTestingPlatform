export interface CapacityValues {
  safe_vus: number
  safe_rps: number
  safety_factor: number
}

export interface CapacityExecutor {
  fingerprint: string
  executor_name: string
  online: boolean
  engine: string
  engine_version: string | null
  safe_vus: number
  safe_rps: number
  reserved_vus: number
  reserved_rps: number
  available_vus: number
  available_rps: number
}

export interface CapacityOverview {
  summary: {
    executor_count: number
    online_count: number
    available_vus: number
    available_rps: number
  }
  defaults: CapacityValues
  rows: CapacityExecutor[]
}
