import { deleted, get, post, put } from '@/api/http'
import type { UiCasePayload } from '@/types/ui-test/case'

export function getUiCase(data: Record<string, unknown>) {
  return get({
    url: '/ui/case',
    data: () => {
      return data
    },
  })
}

export function postUiCase(data: UiCasePayload) {
  return post({
    url: '/ui/case',
    data: () => {
      return data
    },
  })
}

export function putUiCase(data: UiCasePayload) {
  return put({
    url: '/ui/case',
    data: () => {
      return data
    },
  })
}

export function putUiCasePublication(caseId: number | string, targetStatus: 'prepublished' | 'published' | 'unpublished') {
  return put({
    url: '/ui/case/publication',
    data: () => ({
      case_id: caseId,
      target_status: targetStatus,
    }),
  })
}

export function deleteUiCase(id: number | string | Array<string | number>) {
  return deleted({
    url: '/ui/case',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postUiCaseCopy(caseId: number | string) {
  return post({
    url: '/ui/case/copy',
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}

export function postUiRunCaseBatch(caseIdList: Array<number | string>, testingEnvironment: number | string) {
  return post({
    url: 'ui/case/batch',
    data: () => {
      return {
        case_id_list: caseIdList,
        test_env: testingEnvironment,
      }
    },
  })
}

export function getUiCaseRun(caseId: number | string, testingEnvironment: number | string, actuatorUsername?: string) {
  return get({
    url: '/ui/case/test',
    data: () => {
      const params: { case_id: number | string; test_env: number | string; actuator_username?: string } = {
        case_id: caseId,
        test_env: testingEnvironment,
      }
      if (actuatorUsername) params.actuator_username = actuatorUsername
      return params
    },
  })
}
