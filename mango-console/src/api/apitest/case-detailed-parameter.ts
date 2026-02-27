import { deleted, get, post, put } from '@/api/http'

export function getApiCaseDetailedParameter(data: object) {
  return get({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}

export function postApiCaseDetailedParameter(data: object) {
  // @ts-ignore
  return post({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}

export function putApiCaseDetailedParameter(data: object) {
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
  expression: object,
  response: object | string
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
