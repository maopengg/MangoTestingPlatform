import { deleted, get, post, put } from '@/api/http'

export type PytestRepository = {
  id: number
  name: string
  provider: string
  repo_url: string
  api_base_url?: string | null
  remote_project: string
  default_branch: string
  active_branch?: string | null
  current_commit?: string | null
  sync_status: number
  last_sync_time?: string | null
  last_sync_error?: string | null
  project_count: number
  case_count: number
  credential?: {
    auth_type: string
    username?: string | null
    configured: boolean
  } | null
}

export function getPytestRepositories() {
  return get({ url: 'pytest/repository', data: () => ({}) })
}

export interface PytestRepositoryInput {
  id?: number
  name: string
  provider: string
  repo_url: string
  api_base_url: string
  remote_project: string
  default_branch: string
  credential_auth_type: string
  credential_username: string
  credential_secret: string
}

export function savePytestRepository(data: PytestRepositoryInput): Promise<unknown> {
  const request = data.id != null ? put : post
  return request({ url: 'pytest/repository', data: () => data })
}

export function deletePytestRepository(id: number) {
  return deleted({ url: 'pytest/repository', data: () => ({ id }) })
}

export function testPytestRepository(id: number) {
  return post({ url: 'pytest/repository/test', data: () => ({ id }) })
}

export function getPytestRepositoryBranches(id: number, keyword?: string) {
  return get({ url: 'pytest/repository/branches', data: () => ({ id, keyword }) })
}

export function getPytestRepositoryLocalInfo(id: number) {
  return get({ url: 'pytest/repository/local-info', data: () => ({ id }) })
}

export function getPytestRepositoryDirectories(id: number) {
  return get({ url: 'pytest/repository/directories', data: () => ({ id }) })
}

export function getPytestRepositoryTree(id: number) {
  return get({ url: 'pytest/repository/tree', data: () => ({ id }) })
}

export function getPytestRepositoryFile(id: number, path: string) {
  return get({ url: 'pytest/repository/file', data: () => ({ id, path }) })
}

export function pullPytestRepository(id: number, ref?: string) {
  return post({ url: 'pytest/repository/pull', data: () => ({ id, ref }) })
}

export function pushPytestRepository(id: number, message?: string) {
  return post({ url: 'pytest/repository/push', data: () => ({ id, message }) })
}

export function switchPytestRepositoryBranch(id: number, branch: string) {
  return post({ url: 'pytest/repository/switch-branch', data: () => ({ id, branch }) })
}
