import { deleted, get, post, put } from '@/api/http'

export function getUiCase(data: object) {
  return get({
    url: '/ui/case',
    data: () => {
      return data
    },
  })
}

export function postUiCase(data: object) {
  return post({
    url: '/ui/case',
    data: () => {
      return data
    },
  })
}
export function putUiCase(data: object) {
  return put({
    url: '/ui/case',
    data: () => {
      return data
    },
  })
}
export function deleteUiCase(id: number | string[] | number[]) {
  return deleted({
    url: '/ui/case',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function postUiCaseCopy(caseId: number) {
  return post({
    url: '/ui/case/copy',
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}
export function postUiRunCaseBatch(caseIdList: number[] | string[], testingEnvironment: any) {
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
export function getUiCaseRun(caseId: any, testingEnvironment: any) {
  return get({
    url: '/ui/case/test',
    data: () => {
      return {
        case_id: caseId,
        test_env: testingEnvironment,
      }
    },
  })
}
