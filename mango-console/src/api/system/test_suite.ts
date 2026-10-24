import { deleted, get, post, put } from '@/api/http'
import type { DiagnosticMarkdownResult } from '@/api/system/tasks'

export function getSystemTestSuite(data: object) {
  return get({
    url: 'system/test/suite',
    data: () => {
      return data
    },
  })
}

export function postSystemTestSuite(data: object) {
  return post({
    url: 'system/test/suite',
    data: () => {
      return data
    },
  })
}

export function putSystemTestSuite(data: object) {
  return put({
    url: 'system/test/suite',
    data: () => {
      return data
    },
  })
}

export function postSystemTestSuiteSendNotice(data: object) {
  return post({
    url: 'system/test/suite/send/notice',
    data: () => {
      return data
    },
  })
}

export function postSystemTestSuiteStop(id: number | string) {
  return post({
    url: 'system/test/suite/stop',
    data: () => ({ id }),
  })
}

export function deleteSystemTestSuite(id: number | string[] | number[]) {
  return deleted({
    url: 'system/test/suite',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getSystemTestSuiteShare(id: number | string) {
  return get({
    url: 'system/test/suite/share',
    data: () => {
      return { id: id }
    },
  })
}

export function getSystemTestSuiteDiagnosticMarkdown(id: number | string) {
  return get<DiagnosticMarkdownResult>({
    url: 'system/test/suite/diagnostic/markdown',
    data: () => ({ id }),
  })
}
