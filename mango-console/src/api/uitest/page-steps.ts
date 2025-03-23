import { deleted, get, post, put } from '@/api/http'

export function getUiSteps(data: object) {
  return get({
    url: '/ui/page/steps',
    data: () => {
      return data
    },
  })
}

export function deleteUiSteps(id: number | string[] | number[]) {
  return deleted({
    url: '/ui/page/steps',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postUiSteps(data: object) {
  return post({
    url: '/ui/page/steps',
    data: () => {
      return data
    },
  })
}

export function putUiSteps(data: object) {
  return put({
    url: '/ui/page/steps',
    data: () => {
      return data
    },
  })
}

export function getUiStepsTest(id: any, testObj: number) {
  return get({
    url: '/ui/page/steps/test',
    data: () => {
      return {
        page_step_id: id,
        te: testObj,
      }
    },
  })
}

export function getUiStepsPageStepsName(pageId: number) {
  return get({
    url: '/ui/page/steps/name',
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}

export function getUiPageStepsCopy(pageId: number) {
  return post({
    url: '/ui/page/steps/copy',
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}
