import { deleted, get, post, put } from '@/api/http'
import request from '@/api/axios.config'
import type { ApiCaseDataFactoryPayload, ApiCasePayload, ApiCaseQuery } from '@/types/api-test/case'

export function postApiImportUrl(data: Record<string, unknown>) {
  return post({
    url: '/api/import/api',
    data: () => {
      return data
    },
  })
}

export function getApiCase(data: ApiCaseQuery) {
  return get({
    url: '/api/case',
    data: () => {
      return data
    },
  })
}

export function getApiCaseConfigurationSummary(caseIds: number[]) {
  return get({
    url: '/api/case/configuration/summary',
    data: () => ({ case_ids: caseIds.join(',') }),
    silentError: true,
  })
}

export function getApiCaseConfigurationDetails(id: number, page: number, pageSize: number) {
  return get({
    url: '/api/case/configuration/details',
    data: () => ({ id, page, pageSize }),
    silentError: true,
  })
}

export function getApiCaseBoundTasks(id: number | string) {
  return get({
    url: '/api/case/bound/tasks',
    data: () => ({ id }),
  })
}

export function getApiCaseRelatedTasks(id: number | string) {
  return get({
    url: '/api/case/related/tasks',
    data: () => ({ id }),
  })
}

export function postApiCase(data: ApiCasePayload) {
  return post({
    url: '/api/case',
    data: () => {
      return data
    },
  })
}

export function putApiCase(data: ApiCasePayload) {
  return put({
    url: '/api/case',
    data: () => {
      return data
    },
  })
}

export function deleteApiCase(id: number | string[] | number[]) {
  return deleted({
    url: '/api/case',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getApiCaseRun(
  caseId: number | string,
  test_env: number | string,
  caseSort: number | string | null,
  revisionId?: number,
  releaseId?: number | null
) {
  return get({
    url: '/api/case/test',
    data: () => {
      return {
        case_id: caseId,
        test_env: test_env,
        case_sort: caseSort,
        revision_id: revisionId,
        release_id: releaseId,
      }
    },
  })
}

export function getApiCaseRunRaw(
  caseId: number | string,
  test_env: number | string,
  caseSort: number | string | null,
  revisionId?: number,
  releaseId?: number | null
) {
  return request.get('/api/case/test', {
    params: {
      case_id: caseId,
      test_env,
      case_sort: caseSort,
      revision_id: revisionId,
      release_id: releaseId,
    },
  })
}

export function postApiCaseStepDebugRaw(data: {
  case_id: number | string
  case_detailed_id: number | string
  test_env: number | string
  context_id?: string | null
}) {
  return request.post('/api/case/step/debug', data)
}

export function getApiCaseExecutionOptions() {
  return get({
    url: '/api/case/execution/options',
    data: () => ({}),
  })
}

export function postApiCaseBatchRun(
  caseIds: number[],
  test_env: number | string,
  executionName: string,
  apiConcurrencyLimit?: number | null,
  executionVersion: 'editing' | 'published' = 'editing'
) {
  return post({
    url: '/api/case/batch',
    data: () => {
      return {
        case_id_list: caseIds,
        test_env: test_env,
        execution_name: executionName,
        api_concurrency_limit: apiConcurrencyLimit,
        execution_version: executionVersion,
      }
    },
  })
}

export function postApiCaseCody(caseId: number) {
  return post({
    url: '/api/case/copy',
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}

export function getApiCaseName(moduleId: number | string) {
  return get({
    url: '/api/case/name',
    data: () => {
      return {
        module_id: moduleId,
      }
    },
  })
}

export function getApiCaseDataFactory(data: Record<string, unknown>) {
  return get({
    url: '/api/case/data-factory',
    data: () => data,
  })
}

export function postApiCaseDataFactory(data: ApiCaseDataFactoryPayload) {
  return post({
    url: '/api/case/data-factory',
    data: () => data,
  })
}

export function putApiCaseDataFactory(data: ApiCaseDataFactoryPayload) {
  return put({
    url: '/api/case/data-factory',
    data: () => data,
  })
}

export function putApiCaseDataFactorySort(data: {
  case_sort_list: Array<{ id: number; sort: number }>
}) {
  return put({
    url: '/api/case/data-factory/sort',
    data: () => data,
  })
}

export function deleteApiCaseDataFactory(id: number | string[] | number[]) {
  return deleted({
    url: '/api/case/data-factory',
    data: () => ({ id }),
  })
}

export function postApiCaseDataFactoryPreview(data: ApiCaseDataFactoryPayload) {
  return post({
    url: '/api/case/data-factory/preview',
    data: () => data,
  })
}
