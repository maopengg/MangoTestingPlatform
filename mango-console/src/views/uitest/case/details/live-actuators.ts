import { uiCaseAssetObject, uiCaseAssetResponse } from '@/components/business/ui-case-step-create'

export interface CaseLiveActuator {
  username: string; name: string; owner: boolean; full: boolean; activeUsers: number; maxUsers: number; users: string[]
}
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid actuator text'); return value }
function flag(value: unknown): boolean { if (value == null) return false; if (typeof value !== 'boolean') throw Error('Invalid actuator flag'); return value }
function count(value: unknown, fallback: number): number { if (value == null) return fallback; if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw Error('Invalid actuator occupancy'); return value }
export function readCaseLiveActuators(response: unknown): CaseLiveActuator[] {
  const values = uiCaseAssetObject(uiCaseAssetResponse(response)).available_actuators
  if (!Array.isArray(values)) throw Error('Invalid actuator list')
  const rows = values.flatMap(value => {
    const row = uiCaseAssetObject(value)
    if (!flag(row.web_live_stream_supported)) return []
    const username = text(row.username)
    if (!username) throw Error('Missing actuator username')
    if (row.users != null && !Array.isArray(row.users)) throw Error('Invalid actuator users')
    return [{ username, name: text(row.name), owner: flag(row.is_owner), full: flag(row.is_full), activeUsers: count(row.active_user_count, 0), maxUsers: count(row.max_user_count, 5), users: (Array.isArray(row.users) ? row.users : []).map(value => text(uiCaseAssetObject(value).username)) }]
  })
  if (new Set(rows.map(row => row.username)).size !== rows.length) throw Error('Duplicate actuators')
  return rows
}
