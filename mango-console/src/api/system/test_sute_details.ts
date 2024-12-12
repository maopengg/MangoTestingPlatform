import { deleted, get, post, put } from '@/api/http'

export function getSystemTestSuiteDetails(test_suite_id: number) {
  return get({
    url: 'system/test/suite/details',
    data: () => {
      return { test_suite_id: test_suite_id }
    },
  })
}
export function postSystemTestSuiteDetails(data: object) {
  return post({
    url: 'system/test/suite/details',
    data: () => {
      return data
    },
  })
}
export function putSystemTestSuiteDetails(data: object) {
  return put({
    url: 'system/test/suite/details',
    data: () => {
      return data
    },
  })
}

export function deleteSystemTestSuiteDetails(id: number | string[] | number[]) {
  return deleted({
    url: 'system/test/suite/details',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getSystemTestSuiteDetailsReport() {
  return get({
    url: 'system/test/suite/details/report',
    data: () => {
      return {}
    },
  })
}
