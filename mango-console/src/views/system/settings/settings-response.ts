export interface SettingsTestResult {
  status: boolean
  message: string
}

// Only cache inspection accepts arbitrary JSON; configuration editors use their own contracts.
export type SettingsCacheValue = null | string | number | boolean | SettingsCacheValue[] |
  { [key: string]: SettingsCacheValue }

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Invalid settings response')
  }
  return value as Record<string, unknown>
}

export function settingsSuccess(value: unknown): { data: unknown; message: string } {
  const response = record(value)
  if (response.code !== 200 || (response.msg !== undefined && typeof response.msg !== 'string')) {
    throw new Error('Settings request failed')
  }
  return { data: response.data, message: typeof response.msg === 'string' ? response.msg : '' }
}

export function settingsTestResult(value: unknown, resultKey?: string): SettingsTestResult {
  const response = settingsSuccess(value)
  const data = record(response.data)
  const result = resultKey === undefined ? data : record(data[resultKey])
  if (typeof result.status !== 'boolean' ||
    (result.message !== undefined && typeof result.message !== 'string')) {
    throw new Error('Invalid settings test result')
  }
  return { status: result.status, message: typeof result.message === 'string' ? result.message : response.message }
}

export function settingsDebugStatus(value: unknown): boolean {
  const data = record(settingsSuccess(value).data)
  if (typeof data.is_debug !== 'boolean') throw new Error('Invalid debug status')
  return data.is_debug
}

export function copySettingsCache(value: unknown): SettingsCacheValue {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (Array.isArray(value)) return value.map(copySettingsCache)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, value]) => [key, copySettingsCache(value)]))
  }
  throw new Error('Invalid cache content')
}
