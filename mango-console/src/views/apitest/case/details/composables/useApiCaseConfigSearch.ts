import { reactive } from 'vue'
import type { ConfigSearchDocument, ConfigSearchMatch } from '../types'

export type { ConfigSearchDocument, ConfigSearchMatch, ConfigSearchTarget } from '../types'

function preview(value: any, keyword: string) {
  const text =
    typeof value === 'string'
      ? value
      : typeof value === 'number' || typeof value === 'boolean'
      ? String(value)
      : JSON.stringify(value) || String(value ?? '')
  const normalizedText = text.toLocaleLowerCase()
  const matchIndex = normalizedText.indexOf(keyword.toLocaleLowerCase())
  const start = Math.max(0, matchIndex - 42)
  const end = Math.min(text.length, matchIndex + keyword.length + 68)
  return `${start > 0 ? '…' : ''}${text.slice(start, end)}${end < text.length ? '…' : ''}`
}

function findValue(
  value: any,
  keyword: string,
  path = ''
): { path: string; preview: string } | null {
  if (value === undefined || value === null) return null
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index++) {
      const result = findValue(value[index], keyword, `${path}[${index + 1}]`)
      if (result) return result
    }
    return null
  }
  if (typeof value === 'object') {
    for (const [key, childValue] of Object.entries(value)) {
      const childPath = path ? `${path}.${key}` : key
      if (String(key).toLocaleLowerCase().includes(keyword.toLocaleLowerCase())) {
        return { path: childPath, preview: preview(childValue, keyword) }
      }
      const result = findValue(childValue, keyword, childPath)
      if (result) return result
    }
    return null
  }
  const text = String(value)
  if (!text.toLocaleLowerCase().includes(keyword.toLocaleLowerCase())) return null
  return { path, preview: preview(text, keyword) }
}

export async function mapWithConcurrency<T>(
  items: T[],
  worker: (item: T) => Promise<void>,
  concurrency = 4
) {
  let nextIndex = 0
  async function runWorker() {
    while (nextIndex < items.length) {
      const currentIndex = nextIndex
      nextIndex += 1
      await worker(items[currentIndex])
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, () => runWorker()))
}

export function useApiCaseConfigSearch(limit = 200) {
  const state = reactive({
    visible: false,
    loading: false,
    keyword: '',
    searched: false,
    truncated: false,
    completed: 0,
    total: 0,
    matches: [] as ConfigSearchMatch[],
  })
  let documents: ConfigSearchDocument[] = []

  function reset() {
    state.loading = true
    state.searched = false
    state.truncated = false
    state.completed = 0
    state.total = 0
    state.matches = []
    documents = []
  }

  function setDocuments(value: ConfigSearchDocument[]) {
    documents = value
  }

  function search() {
    const keyword = String(state.keyword || '').trim()
    if (!keyword) {
      state.searched = false
      state.matches = []
      return
    }
    const matches: ConfigSearchMatch[] = []
    let matchedCount = 0
    for (const document of documents) {
      const result = findValue(document.value, keyword)
      if (!result) continue
      matchedCount += 1
      if (matches.length < limit) {
        matches.push({
          location: document.location,
          path: result.path ? `${document.fieldLabel}.${result.path}` : document.fieldLabel,
          preview: result.preview,
          stepId: document.stepId,
          scenarioId: document.scenarioId,
          caseApiType: document.caseApiType,
          caseApiSonType: document.caseApiSonType,
          detailType: document.detailType,
          detailTab: document.detailTab,
        })
      }
    }
    state.matches = matches
    state.truncated = matchedCount > limit
    state.searched = true
  }

  return { state, reset, search, setDocuments }
}
