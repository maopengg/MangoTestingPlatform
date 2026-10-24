import { deleted, get, post, put } from '@/api/http'
import request from '@/api/axios.config'

export function updateReportDisposition(id: number, data: { is_excluded: boolean; failure_reason: string; failure_description: string }) {
  return post({ url: 'test/suite/details/disposition', data: () => ({ id, ...data }) })
}

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

export function getSystemTestSuiteDetailsReport(data: Record<string, any> = {}) {
  return get({
    url: 'system/test/suite/details/report',
    data: () => data,
  })
}

export function getSystemTestSuiteDetailsExecutionOptions() {
  return get({
    url: 'system/test/suite/details/execution/options',
    data: () => ({}),
  })
}

export function getSystemTestSuiteDetailsAllRetry(
  test_suite_id: number,
  testEnv?: number | null,
  apiConcurrencyLimit?: number | null
) {
  return get({
    url: 'system/test/suite/details/all/retry',
    data: () => {
      const params: Record<string, any> = {
        test_suite_id: test_suite_id,
        test_env: testEnv,
      }
      if (apiConcurrencyLimit !== null && apiConcurrencyLimit !== undefined) {
        params.api_concurrency_limit = apiConcurrencyLimit
      }
      return params
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

export function retryFailedReportCases(testSuiteId: number) {
  return post({
    url: 'system/test/suite/details/failed/retry',
    data: () => ({ test_suite_id: testSuiteId }),
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

export function getSystemTestSuiteDetailsExecutionTrace(data: object) {
  return get({
    url: 'system/test/suite/details/execution-trace',
    data: () => data,
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

export function getSystemTestSuiteDetailsResultShare(
  testSuiteDetailId: number | string,
  resultId?: number | string | null
) {
  return get({
    url: 'system/test/suite/details/result/share',
    data: () => {
      const params: Record<string, any> = { test_suite_detail_id: testSuiteDetailId }
      if (resultId !== null && resultId !== undefined && resultId !== '') {
        params.result_id = resultId
      }
      return params
    },
  })
}

export function getSystemTestSuiteDetailsResultOptionsShare(
  testSuiteDetailId: number | string,
  limit = 20
) {
  return get({
    url: 'system/test/suite/details/result/options/share',
    data: () => {
      return { test_suite_detail_id: testSuiteDetailId, limit }
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

export function getSystemTestSuiteDetailsFailureReasonsShare(test_suite_id: number | string) {
  return get({
    url: 'system/test/suite/details/failure-reasons/share',
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
