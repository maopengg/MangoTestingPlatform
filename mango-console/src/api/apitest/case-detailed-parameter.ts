import { deleted, get, post, put } from '@/api/http'
import type {
  ApiCaseParameterPayload,
  ApiCaseParameterQuery,
} from '@/types/api-test/case-parameter'

export function getApiCaseDetailedParameter(data: ApiCaseParameterQuery) {
  return get({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}

export function postApiCaseDetailedParameter(data: ApiCaseParameterPayload) {
  // @ts-ignore
  return post({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}

export function postApiCaseDetailedParameterCopy(
  data: ApiCaseParameterPayload & { id: number | null }
) {
  return post({
    url: '/api/case/detailed/parameter/copy',
    data: () => {
      return data
    },
  })
}

export function putApiCaseDetailedParameter(data: ApiCaseParameterPayload) {
  // @ts-ignore
  return put({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}

export function deleteApiCaseDetailedParameter(id: number | string[] | number[]) {
  const data: any = {
    id: id,
  }
  return deleted({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}

export function postCaseDetailedParameterTestExtractResponseAfter(
  type: string,
  expression: Record<string, unknown> | string,
  response: Record<string, unknown> | string
) {
  return post({
    url: '/api/case/detailed/parameter/test/extract/response/after',
    data: () => {
      return {
        type: type,
        expression: expression,
        response: response,
      }
    },
  })
}

export function putSetSchema(id: number) {
  return put({
    url: '/api/case/detailed/parameter/schema',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
