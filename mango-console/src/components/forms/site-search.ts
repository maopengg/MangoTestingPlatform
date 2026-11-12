import type { RouteRecordRaw } from 'vue-router'

export interface SearchSource {
  key: string
  title: string
  menu: string
  detail: string
  endpoint: string
  nameField: string
}
export interface SearchRow {
  id: string
  title: string
  context: string
}
export const searchSources: SearchSource[] = [
  {
    key: 'api-case',
    title: 'API 用例',
    menu: '/apitest/case/index',
    detail: '/apitest/case/details',
    endpoint: '/api/case',
    nameField: 'name',
  },
  {
    key: 'ui-case',
    title: 'UI 用例',
    menu: '/uitest/case/index',
    detail: '/uitest/case/details',
    endpoint: '/ui/case',
    nameField: 'name',
  },
  {
    key: 'api-info',
    title: '接口',
    menu: '/apitest/info/index',
    detail: '/apitest/info/details',
    endpoint: '/api/info',
    nameField: 'name',
  },
  {
    key: 'report',
    title: '执行报告',
    menu: '/report/index',
    detail: '/report/system/details',
    endpoint: '/system/test/suite',
    nameField: 'execution_name',
  },
]

export function collectSearchMenus(
  routes: RouteRecordRaw[],
  parent = '',
  ancestors: string[] = []
): { title: string; path: string; context: string }[] {
  return routes.flatMap((route) => {
    if (route.meta?.hidden || !route.meta?.title) return []
    const path = route.path.startsWith('/')
      ? route.path
      : `${parent}/${route.path}`.replace(/\/+/g, '/')
    const title = String(route.meta.title)
    const context = [...ancestors, title].join(' / ')
    return route.children?.length
      ? collectSearchMenus(route.children, path, [...ancestors, title])
      : [{ title, path, context }]
  })
}

export function buildSearchQueries(
  source: SearchSource,
  keyword: string,
  page = 1
): Record<string, unknown>[] {
  const text = keyword.trim()
  const base = { page, pageSize: 8 }
  if (/^\d+$/.test(text)) return [{ ...base, id: text }]
  if (source.key === 'api-info' && /[/?]/.test(text)) return [{ ...base, url: text }]
  return [{ ...base, [source.nameField]: text }]
}

export function toSearchRow(raw: unknown): SearchRow | null {
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Record<string, unknown>
  if (typeof row.id !== 'string' && typeof row.id !== 'number') return null
  const label = (value: unknown): string =>
    typeof value === 'string'
      ? value
      : value && typeof value === 'object'
      ? String(
          (value as Record<string, unknown>).full_path ||
            (value as Record<string, unknown>).name ||
            ''
        )
      : ''
  return {
    id: String(row.id),
    title: label(row.name) || label(row.execution_name) || `执行报告 ${row.id}`,
    context: [label(row.project_product), label(row.module), label(row.url)]
      .filter(Boolean)
      .join(' / '),
  }
}
