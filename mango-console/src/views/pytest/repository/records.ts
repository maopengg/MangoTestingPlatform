import type { PytestRepository, PytestRepositoryInput } from '@/api/pytest/repository'
import type { DirectoryNode } from '../case/records'

export interface RepositoryDraft extends Omit<PytestRepositoryInput, 'id'> {
  id: number | null
}
export interface RepositoryEntry {
  path: string
  type: 'file' | 'directory'
}
export interface RepositoryTree {
  entries: RepositoryEntry[]
  directory_count: number
  file_count: number
}
export interface BranchOption {
  value: string
  label: string
}
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('仓库数据格式不正确')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('字段格式不正确')
  return value
}
function nullableText(value: unknown): string | null {
  return value == null ? null : text(value)
}
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0)
    throw new Error('数量格式不正确')
  return value
}
export function repositoryResponse(value: unknown): Record<string, unknown> {
  const response = object(value)
  if (response.code !== 200) throw new Error('仓库请求失败，请重试')
  return response
}
export function readRepository(value: unknown): PytestRepository {
  const row = object(value),
    credential = row.credential == null ? null : object(row.credential)
  if (credential && typeof credential.configured !== 'boolean')
    throw new Error('凭证状态格式不正确')
  return {
    id: count(row.id),
    name: text(row.name),
    provider: text(row.provider),
    repo_url: text(row.repo_url),
    api_base_url: nullableText(row.api_base_url),
    remote_project: text(row.remote_project),
    default_branch: text(row.default_branch),
    active_branch: nullableText(row.active_branch),
    current_commit: nullableText(row.current_commit),
    sync_status: count(row.sync_status),
    last_sync_time: nullableText(row.last_sync_time),
    last_sync_error: nullableText(row.last_sync_error),
    project_count: count(row.project_count ?? 0),
    case_count: count(row.case_count ?? 0),
    credential: credential
      ? {
          auth_type: text(credential.auth_type),
          username: nullableText(credential.username),
          configured: credential.configured as boolean,
        }
      : null,
  }
}
export function readRepositories(value: unknown): PytestRepository[] {
  const response = repositoryResponse(value)
  if (!Array.isArray(response.data)) throw new Error('仓库列表格式不正确')
  const rows = response.data.map(readRepository)
  if (new Set(rows.map((row) => row.id)).size !== rows.length) throw new Error('仓库标识重复')
  return rows
}
export function emptyRepositoryDraft(): RepositoryDraft {
  return {
    id: null,
    name: '',
    provider: 'gitlab',
    repo_url: '',
    api_base_url: '',
    remote_project: '',
    default_branch: 'master',
    credential_auth_type: 'none',
    credential_username: '',
    credential_secret: '',
  }
}
export function repositoryDraft(record: PytestRepository): RepositoryDraft {
  return {
    id: record.id,
    name: record.name,
    provider: record.provider,
    repo_url: record.repo_url,
    api_base_url: record.api_base_url ?? '',
    remote_project: record.remote_project,
    default_branch: record.default_branch,
    credential_auth_type: record.credential?.auth_type ?? 'none',
    credential_username: record.credential?.username ?? '',
    credential_secret: '',
  }
}
function repositoryHost(value: string): string {
  const ssh = value.match(/^git@([^:]+):/i)
  if (ssh) return ssh[1].toLowerCase()
  try {
    return new URL(value).hostname.toLowerCase()
  } catch {
    return ''
  }
}
export function repositoryPayload(draft: RepositoryDraft): PytestRepositoryInput {
  if (!draft.name.trim() || !draft.repo_url.trim() || !draft.default_branch.trim())
    throw new Error('请填写仓库名称、仓库地址和默认分支')
  const publicProviders: Record<string, string> = {
    'github.com': 'github',
    'gitlab.com': 'gitlab',
    'gitee.com': 'gitee',
  }
  const actual = publicProviders[repositoryHost(draft.repo_url)]
  if (actual && actual !== draft.provider) throw new Error('仓库地址与 Git 平台不一致，请检查')
  const auth = draft.credential_auth_type || 'none'
  return {
    ...(draft.id !== null ? { id: draft.id } : {}),
    name: draft.name,
    provider: draft.provider,
    repo_url: draft.repo_url,
    api_base_url: draft.api_base_url,
    remote_project: draft.remote_project,
    default_branch: draft.default_branch,
    credential_auth_type: auth,
    credential_username: auth === 'none' ? '' : draft.credential_username,
    credential_secret: auth === 'none' ? '' : draft.credential_secret,
  }
}
export function repositoryRevision(record: PytestRepository): string {
  return JSON.stringify([
    record.id,
    record.name,
    record.provider,
    record.repo_url,
    record.api_base_url,
    record.remote_project,
    record.default_branch,
    record.active_branch,
    record.current_commit,
    record.credential?.auth_type,
    record.credential?.username,
    record.credential?.configured,
  ])
}
function repositoryPath(value: unknown): string {
  const path = text(value)
  if (
    !path ||
    path.startsWith('/') ||
    path.includes('\\') ||
    path.split('/').some((part) => !part || part === '.' || part === '..')
  )
    throw new Error('仓库路径格式不正确')
  return path
}
export function readRepositoryTree(value: unknown): RepositoryTree {
  const data = object(repositoryResponse(value).data)
  if (!Array.isArray(data.entries)) throw new Error('目录树格式不正确')
  const entries = data.entries.map((value): RepositoryEntry => {
    const row = object(value),
      type = row.type
    if (type !== 'file' && type !== 'directory') throw new Error('目录节点格式不正确')
    return { path: repositoryPath(row.path), type }
  })
  if (new Set(entries.map((entry) => entry.path)).size !== entries.length)
    throw new Error('目录路径重复')
  const files = new Set(entries.filter((entry) => entry.type === 'file').map((entry) => entry.path))
  if (
    entries.some((entry) =>
      entry.path
        .split('/')
        .slice(0, -1)
        .some((_, i, parts) => files.has(parts.slice(0, i + 1).join('/')))
    )
  )
    throw new Error('目录父级类型不正确')
  return {
    entries,
    directory_count: count(data.directory_count),
    file_count: count(data.file_count),
  }
}
export function readRepositoryFile(value: unknown, path: string): string {
  const data = object(repositoryResponse(value).data)
  if (data.path !== path) throw new Error('文件上下文已变化')
  return text(data.content)
}
export function readBranches(value: unknown): BranchOption[] {
  const data = repositoryResponse(value).data
  if (!Array.isArray(data)) throw new Error('分支列表格式不正确')
  const names = new Set<string>()
  return data.map((value) => {
    const row = object(value),
      name = text(row.name)
    if (!name || names.has(name) || (row.default != null && typeof row.default !== 'boolean'))
      throw new Error('分支格式不正确')
    names.add(name)
    return { value: name, label: row.default ? `${name}（默认）` : name }
  })
}
export function repositoryRootKey(id: number): string {
  return `repository:${id}`
}
export function buildRepositoryTree(
  repository: PytestRepository,
  entries: RepositoryEntry[]
): DirectoryNode[] {
  const roots: DirectoryNode[] = [],
    directories = new Map<string, DirectoryNode>()
  function ensure(path: string): DirectoryNode | null {
    if (!path) return null
    let parent: DirectoryNode | null = null,
      current = ''
    for (const part of path.split('/')) {
      current = current ? `${current}/${part}` : part
      let node = directories.get(current)
      if (!node) {
        node = {
          key: `repository:${repository.id}:directory:${current}`,
          title: part,
          type: 'directory',
          path: current,
          breadcrumb: [repository.name, ...current.split('/')],
          repository_id: repository.id,
          case_count: 0,
          children: [],
        }
        directories.set(current, node)
        if (parent) parent.children.push(node)
        else roots.push(node)
      }
      parent = node
    }
    return parent
  }
  for (const entry of entries) {
    if (entry.type === 'directory') {
      ensure(entry.path)
      continue
    }
    const parts = entry.path.split('/'),
      parent = ensure(parts.slice(0, -1).join('/'))
    const node: DirectoryNode = {
      key: `repository:${repository.id}:file:${entry.path}`,
      title: parts.at(-1)!,
      type: 'file',
      path: entry.path,
      breadcrumb: [repository.name, ...parts],
      repository_id: repository.id,
      case_count: 0,
      children: [],
    }
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  function finish(nodes: DirectoryNode[]): number {
    nodes.sort((a, b) =>
      a.type === b.type ? a.title.localeCompare(b.title) : a.type === 'directory' ? -1 : 1
    )
    return nodes.reduce((total, node) => {
      const files = node.type === 'file' ? 1 : finish(node.children)
      if (node.type === 'directory') node.count = files
      return total + files
    }, 0)
  }
  finish(roots)
  return roots
}
