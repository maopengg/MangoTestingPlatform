import { copySettingsCache, settingsSuccess } from './settings-response'

export interface ConfigItem {
  id: number | string
  key: string
  describe: string
  value: unknown
  value_type: number | null
  is_secret: boolean
  management_level: number
  has_value: boolean
  placeholder?: string
  runtime_status?: unknown
  performance_notice?: string
}

export interface ConfigGroup {
  key: string
  title: string
  items: ConfigItem[]
}

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid configuration record')
  return value as Record<string, unknown>
}

export function copyConfigGroups(response: unknown): ConfigGroup[] {
  const data = settingsSuccess(response).data
  if (!Array.isArray(data)) throw new Error('Invalid configuration groups')
  const groups = new Set<string>(), keys = new Set<string>()
  return data.map(value => {
    const group = record(value)
    if (typeof group.key !== 'string' || !group.key || groups.has(group.key) ||
      typeof group.title !== 'string' || !Array.isArray(group.items)) throw new Error('Invalid configuration group')
    groups.add(group.key)
    const items = group.items.map(value => {
      const item = record(value)
      const validId = (typeof item.id === 'number' && Number.isSafeInteger(item.id) && item.id >= 0) ||
        (typeof item.id === 'string' && /^\d+$/.test(item.id))
      if (!validId || typeof item.key !== 'string' || !item.key || keys.has(item.key) ||
        (item.describe !== null && typeof item.describe !== 'string') ||
        (item.value_type !== null && (typeof item.value_type !== 'number' || !Number.isInteger(item.value_type))) ||
        typeof item.is_secret !== 'boolean' || typeof item.has_value !== 'boolean' ||
        typeof item.management_level !== 'number' || !Number.isInteger(item.management_level) ||
        (item.placeholder != null && typeof item.placeholder !== 'string') ||
        (item.performance_notice != null && typeof item.performance_notice !== 'string')) throw new Error('Invalid configuration item')
      keys.add(item.key)
      const copied: ConfigItem = {
        id: item.id as number | string,
        key: item.key,
        describe: item.describe ?? item.key,
        value: copySettingsCache(item.value),
        value_type: item.value_type,
        is_secret: item.is_secret,
        has_value: item.has_value,
        management_level: item.management_level,
      }
      if (typeof item.placeholder === 'string') copied.placeholder = item.placeholder
      if (typeof item.performance_notice === 'string') copied.performance_notice = item.performance_notice
      if (item.runtime_status !== undefined) copied.runtime_status = copySettingsCache(item.runtime_status)
      return copied
    })
    return { key: group.key, title: group.title, items }
  })
}
