import { deleted, get, post, put } from '@/api/http'
import type {
  ApiCaseDataFactoryPayload,
  ApiCasePayload,
  ApiCaseQuery,
} from '@/types/api-test/case'

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
  caseSort: number | string | null
) {
  return get({
    url: '/api/case/test',
    data: () => {
      return {
        case_id: caseId,
        test_env: test_env,
        case_sort: caseSort,
      }
    },
  })
}

export function postApiCaseBatchRun(caseIdList: Array<string | number>, test_env: number | string) {
  return post({
    url: '/api/case/batch',
    data: () => {
      return {
        case_id_list: caseIdList,
        test_env: test_env,
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

export function putApiCaseDataFactorySort(data: { case_sort_list: Array<{ id: number; sort: number }> }) {
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
