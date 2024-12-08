import { deleted, get, post, put } from '@/api/http'

export function getUiPageStepsDetailed(id: any) {
  return get({
    url: '/ui/page/steps/detailed',
    data: () => {
      return {
        page_step_id: id,
      }
    },
  })
}

export function postUiPageStepsDetailed(data: object) {
  return post({
    url: '/ui/page/steps/detailed',
    data: () => {
      return data
    },
  })
}
export function putUiPageStepsDetailed(data: object) {
  return put({
    url: '/ui/page/steps/detailed',
    data: () => {
      return data
    },
  })
}
export function deleteUiPageStepsDetailed(id: number | string[] | number[], parentId: number) {
  return deleted({
    url: '/ui/page/steps/detailed',
    data: () => {
      return {
        id: id,
        parent_id: parentId,
      }
    },
  })
}

export function getUiPageStepsDetailedOpe(pageType: any) {
  return get({
    url: '/ui/page/steps/detailed/ope',
    data: () => {
      return {
        page_type: pageType,
      }
    },
  })
}
export function getUiPageStepsDetailedAss(pageType: any) {
  return get({
    url: '/ui/page/steps/detailed/ass',
    data: () => {
      return {
        page_type: pageType,
      }
    },
  })
}
export function getUiPageAssMethod() {
  return get({
    url: '/ui/page/steps/detailed/ass/method',
    data: () => {
      return {}
    },
  })
}
export function putUiPagePutStepSort(data: any) {
  return put({
    url: '/ui/page/steps/detailed/sort',
    data: () => {
      return {
        step_sort_list: data,
      }
    },
  })
}
