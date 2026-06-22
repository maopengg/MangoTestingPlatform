import { deleted, get, post, put } from '@/api/http'
import request from '@/api/axios.config'

export function getSystemTestSuiteDetails(data: object) {
  return get({
    url: 'system/test/suite/details',
    data: () => {
      return data
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

export function getSystemTestSuiteDetailsAllRetry(test_suite_id: number) {
  return get({
    url: 'system/test/suite/details/all/retry',
    data: () => {
      return { test_suite_id: test_suite_id }
    },
  })
}
export function getSystemTestSuiteDetailsRetry(id: number) {
  return get({
    url: 'system/test/suite/details/retry',
    data: () => {
      return { id: id }
    },
  })
}

export function getSystemTestSuiteDetailsSummary(test_suite_id: number) {
  return get({
    url: 'system/test/suite/details/summary',
    data: () => {
      return { test_suite_id: test_suite_id }
    },
  })
}

export function getSystemTestSuiteDetailsShare(data: object) {
  return get({
    url: 'system/test/suite/details/share',
    data: () => {
      return data
    },
  })
}

export function getSystemTestSuiteDetailsSummaryShare(test_suite_id: number | string) {
  return get({
    url: 'system/test/suite/details/summary/share',
    data: () => {
      return { test_suite_id: test_suite_id }
    },
  })
}

export function postSystemTestSuiteDetailsApiExport(data: object) {
  return post({
    url: 'system/test/suite/details/api/export',
    data: () => data,
  })
}

export function getSystemTestSuiteDetailsApiExportStatus(task_id: string) {
  return get({
    url: 'system/test/suite/details/api/export/status',
    data: () => ({ task_id }),
  })
}

export function downloadSystemTestSuiteDetailsApiExport(task_id: string) {
  return request.get('system/test/suite/details/api/export/download', {
    params: { task_id },
    responseType: 'blob',
  })
}
