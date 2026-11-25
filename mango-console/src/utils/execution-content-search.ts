import type { ContentSearchTask } from '@/api/system/execution_content_search'

export function parseContentSearch(value: unknown): ContentSearchTask {
  if (!value || typeof value !== 'object') throw new Error('检索响应格式错误')
  const data = value as Record<string, unknown>
  const query = data.query as Record<string, unknown> | undefined
  if (typeof data.task_id !== 'string' || !/^[a-f0-9]{32}$/.test(data.task_id) ||
    !['running', 'completed', 'partial', 'cancelled', 'failed'].includes(String(data.status)) ||
    !query || typeof query.keyword !== 'string' || !query.keyword || typeof query.day !== 'string' ||
    (query.project_product_id != null && typeof query.project_product_id !== 'number') ||
    (query.test_env != null && typeof query.test_env !== 'number') ||
    !['scanned', 'skipped', 'read_bytes', 'count', 'page'].every(key => Number.isSafeInteger(data[key]) && Number(data[key]) >= 0) ||
    typeof data.message !== 'string' || !Array.isArray(data.items) || data.items.length > 20) throw new Error('检索响应格式错误')
  for (const row of data.items) {
    if (!row || typeof row !== 'object' || !Number.isSafeInteger(row.record_id) || row.record_id <= 0 ||
      !['target_type', 'name', 'create_time', 'source_type', 'stage', 'trigger_user', 'path', 'snippet'].every(key => typeof row[key] === 'string')) throw new Error('检索命中记录格式错误')
  }
  return data as unknown as ContentSearchTask
}

export function highlightSearchText(text: string, keyword: string) {
  if (!keyword) return [{ text, matched: false }]
  const parts: Array<{ text: string; matched: boolean }> = []
  const haystack = text.toLocaleLowerCase(), needle = keyword.toLocaleLowerCase()
  let offset = 0, index = haystack.indexOf(needle)
  while (index >= 0) {
    parts.push({ text: text.slice(offset, index), matched: false }, { text: text.slice(index, index + keyword.length), matched: true })
    offset = index + keyword.length; index = haystack.indexOf(needle, offset)
  }
  parts.push({ text: text.slice(offset), matched: false })
  return parts
}
