import { deleted, get, post, put } from '@/api/http'
import * as url from './url'

export function getUiPage(data: object) {
  return get({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
}

export function postUiPage(data: object) {
  return post({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
}
export function putUiPage(data: object) {
  return put({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
}
export function deleteUiPage(id: number | string[] | number[]) {
  return deleted({
    url: url.uiPage,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function postUiPageCopy(pageId: number | string) {
  return post({
    url: url.uiPageCopy,
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}

export function getUiElement(pageId: any) {
  return get({
    url: url.uiUiElement,
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}
export function getUiPageStepsDetailedOpe(pageType: any) {
  return get({
    url: url.uiPageStepsDetailedOpe,
    data: () => {
      return {
        page_type: pageType,
      }
    },
  })
}
