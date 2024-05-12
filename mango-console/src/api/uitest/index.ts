import { deleted, get, post, put } from '@/api/http'
import { Message } from '@arco-design/web-vue'
import * as url from './url'
import { uiPageStepsDetailedOpe, uiUiElement } from '@/api/url'

export function getUiPage(data: object, table: any, pagination: any) {
  get({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
    .catch(console.log)
}

export function postUiPage(data: object) {
  post({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
    .then((res) => {
      Message.success(res.msg)
    })
    .catch(console.log)
}
export function putUiPage(data: object) {
  put({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
    .then((res) => {
      Message.success(res.msg)
    })
    .catch(console.log)
}
export function deleteUiPage(id: number | string[] | number[]) {
  deleted({
    url: url.uiPage,
    data: () => {
      return {
        id: id,
      }
    },
  })
    .then((res) => {
      Message.success(res.msg)
    })
    .catch(console.log)
}
export function postUiPageCopy(pageId: number | string) {
  post({
    url: url.uiPageCopy,
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
    .then((res) => {
      Message.success(res.msg)
    })
    .catch(console.log)
}

export function getUiElement(pageId: any, pageEleData: any) {
  get({
    url: url.uiUiElement,
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
    .then((res) => {
      pageEleData.data = res.data
      pageEleData.totalSize = res.totalSize
    })
    .catch(console.log)
}
export function getUiPageStepsDetailedOpe(pageType: any) {
  get({
    url: url.uiPageStepsDetailedOpe,
    data: () => {
      return {
        page_type: pageType,
      }
    },
  })
    .then((res) => {
      data.ope = res.data
    })
    .catch(console.log)
}
