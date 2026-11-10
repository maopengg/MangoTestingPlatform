import { deleted, get, post, put } from '@/api/http'

export function postPytestCase(data: any) {
  return post({
    url: 'pytest/case',
    data: () => {
      return data
    },
  })
}

export function deletePytestCase(id: any) {
  return deleted({
    url: 'pytest/case',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getPytestCase(data: any) {
  return get({
    url: 'pytest/case',
    data: () => {
      return data
    },
  })
}

export function putPytestCase(data: object) {
  return put<unknown>({
    url: 'pytest/case',
    data: () => {
      return data
    },
  })
}

export function putPytestCasePublication(caseId: number, targetStatus: 'prepublished' | 'published' | 'unpublished') {
  return put({
    url: 'pytest/case/publication',
    data: () => ({
      case_id: caseId,
      target_status: targetStatus,
    }),
  })
}

export function postPytestCaseUpdate(projectId: number) {
  return post<unknown>({
    url: 'pytest/case/update',
    data: () => {
      return { project_id: projectId }
    },
  })
}

export function getPytestCaseRead(id: any, fileType = 'py', silentError = false) {
  return get({
    url: 'pytest/case/read',
    data: () => {
      return { id: id, file_type: fileType }
    },
    silentError,
  })
}

export function postPytestCaseWrite(
  id: number,
  file_content: string,
  fileType: 'py' | 'feature' = 'py',
  expectedCommit?: string,
  expectedContentHash?: string
): Promise<unknown> {
  return post<unknown>({
    url: 'pytest/case/write',
    data: () => {
      return {
        id: id,
        file_content: file_content,
        file_type: fileType,
        expected_commit: expectedCommit,
        expected_content_hash: expectedContentHash,
      }
    },
  })
}

export function getPytestCaseTest(id: any, test_env: any, target: any = {}) {
  return get({
    url: 'pytest/case/test',
    data: () => {
      return { id: id, test_env: test_env, ...target }
    },
  })
}

export function postPytestCaseBatch(caseIds: Array<string | number>, testEnv: number) {
  return post({
    url: 'pytest/case/batch',
    data: () => ({
      case_id_list: caseIds,
      test_env: testEnv,
    }),
  })
}

export function getPytestCaseMethodNodes(id: any, silentError = false) {
  return get({
    url: 'pytest/case/method-nodes',
    data: () => {
      return { id: id }
    },
    silentError,
  })
}

export function getPytestCaseDirectoryTree(data: {
  [key: string]: unknown
  project_product_id?: string | number | null
  repository_id?: string | number | null
  pytest_project_id?: string | number | null
  module_ids?: string
  keyword?: string
}) {
  return get({
    url: 'pytest/case/directory-tree',
    data: () => data,
  })
}

export function putPytestCaseModule(data: { case_ids: number[]; module_id: number }) {
  return put({
    url: 'pytest/case/module',
    data: () => data,
  })
}

export function putPytestCaseBatchUpdate(data: {
  updates: Array<{ id: number; changes: Record<string, unknown> }>
}) {
  return put<unknown>({
    url: 'pytest/case/batch-update',
    data: () => data,
  })
}

export function postPytestCaseAiInfer(data: { case_ids: number[] }) {
  return post<unknown>({
    url: 'pytest/case/ai-infer',
    data: () => data,
  })
}
