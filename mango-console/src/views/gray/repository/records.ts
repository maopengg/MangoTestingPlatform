import { normalizeEmptyListTotal } from '@/utils/api-response'
export const COMMON_ENV = '__common__'
export type ContextSource = string | (() => string)
export const contextOf = (source: ContextSource): string =>
  typeof source === 'function' ? source() : source
export interface RepositoryRow {
  id: number
  name: string
  repo_url: string
  provider: string
  api_base_url: string
  branch: string
  test_env: number | null
  config_dirs: string[]
  status: number
  access_token: '已配置' | '未配置'
}
export interface RepositoryForm {
  name: string
  repo_url: string
  provider: string
  api_base_url: string
  access_token: string
  branch: string
  test_env: string | number | null
  config_dirs: string[]
  status: number
}
export interface RepositoryQuery {
  name: string
  repo_url: string
  provider: string[]
  test_env: number | string | null | undefined
  branch: string
  status: number[]
}
export interface EditorHandle {
  open(record?: RepositoryRow): void
}
export const createQuery = (): RepositoryQuery => ({
  name: '',
  repo_url: '',
  provider: [],
  test_env: null,
  branch: '',
  status: [],
})
export function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
export function positiveId(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0
}
export function environment(value: number | string | null | undefined): number | null {
  if (value === COMMON_ENV || value == null || value === '') return null
  const result = Number(value)
  if (!Number.isSafeInteger(result)) throw Error('Invalid repository environment')
  return result
}
export function normalizeDirs(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return [
    ...new Set(
      value
        .map((item) => {
          const raw = String(item ?? '')
            .trim()
            .replace(/\\/g, '/')
            .replace(/^\/+|\/+$/g, '')
          if (!raw) return ''
          return (
            raw
              .split('/')
              .filter((part) => part !== '' && part !== '.')
              .join('/') || '.'
          )
        })
        .filter(Boolean)
    ),
  ]
}
export function createForm(record?: RepositoryRow): RepositoryForm {
  return {
    name: record?.name ?? '',
    repo_url: record?.repo_url ?? '',
    provider: record?.provider ?? 'gitlab',
    api_base_url: record?.api_base_url ?? '',
    access_token: '',
    branch: record?.branch ?? '',
    test_env: record?.test_env ?? COMMON_ENV,
    config_dirs: normalizeDirs(record?.config_dirs),
    status: record?.status ?? 1,
  }
}
export function validation(form: RepositoryForm): string | null {
  const rules = [
    [form.name, '请输入仓库名称'],
    [form.repo_url, '请输入仓库地址'],
    [form.provider, '请选择平台类型'],
    [form.api_base_url, '请输入平台域名'],
    [form.test_env, '请选择测试环境'],
    [form.branch, '请输入分支'],
  ] as const
  const invalid = rules.find(
    ([value]) => value == null || (typeof value === 'string' && !value.trim())
  )
  if (invalid) return invalid[1]
  if (!normalizeDirs(form.config_dirs).length) return '请输入配置目录，例如 app/config'
  return null
}
export function formPayload(form: RepositoryForm, id: number | null) {
  return {
    ...(id === null ? {} : { id }),
    name: form.name.trim(),
    repo_url: form.repo_url.trim(),
    provider: form.provider.trim(),
    api_base_url: form.api_base_url.trim(),
    ...(id === null || form.access_token !== '' ? { access_token: form.access_token } : {}),
    branch: form.branch.trim(),
    test_env: environment(form.test_env),
    config_dirs: normalizeDirs(form.config_dirs),
    status: form.status,
  }
}
export function requestParams(query: RepositoryQuery, page: number, pageSize: number) {
  return Object.fromEntries(
    Object.entries({
      page,
      pageSize,
      name: query.name,
      repo_url: query.repo_url,
      provider__in: query.provider.join(','),
      ...(query.test_env === COMMON_ENV
        ? { test_env__isnull: true }
        : { test_env: environment(query.test_env) }),
      branch: query.branch,
      status__in: query.status.join(','),
    }).filter(([, value]) => value !== '' && value != null)
  )
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw Error('Invalid repository text')
  return value
}
export function repositoryPage(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const response = object(value),
    list = response.data
  const total =
    response.totalSize === undefined && Array.isArray(list) && !list.length ? 0 : response.totalSize
  if (
    response.code !== 200 ||
    !Array.isArray(list) ||
    typeof total !== 'number' ||
    !Number.isSafeInteger(total) ||
    total < list.length
  )
    throw Error('Invalid repository page')
  const seen = new Set<number>()
  const rows = list.map((value): RepositoryRow => {
    const row = object(value)
    if (
      !positiveId(row.id) ||
      seen.has(row.id) ||
      typeof row.status !== 'number' ||
      ![0, 1].includes(row.status) ||
      (row.test_env !== null &&
        (typeof row.test_env !== 'number' || !Number.isSafeInteger(row.test_env))) ||
      !Array.isArray(row.config_dirs) ||
      row.config_dirs.some((item) => typeof item !== 'string') ||
      !['已配置', '未配置'].includes(String(row.access_token))
    )
      throw Error('Invalid repository record')
    seen.add(row.id)
    return {
      id: row.id,
      name: text(row.name),
      repo_url: text(row.repo_url),
      provider: text(row.provider),
      api_base_url: text(row.api_base_url),
      branch: text(row.branch),
      test_env: row.test_env as number | null,
      config_dirs: normalizeDirs(row.config_dirs),
      status: row.status,
      access_token: row.access_token as RepositoryRow['access_token'],
    }
  })
  return { rows, total }
}
