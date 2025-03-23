import { deleted, get, post, put } from '@/api/http'

export function getUiElement(pageId: any) {
  return get({
    url: '/ui/element',
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}

export function deleteUiElement(id: number | string[] | number[]) {
  return deleted({
    url: '/ui/element',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postUiElement(data: object) {
  return post({
    url: '/ui/element',
    data: () => {
      return data
    },
  })
}

export function putUiElement(data: object) {
  return put({
    url: '/ui/element',
    data: () => {
      return data
    },
  })
}

export function putUiUiElementPutIsIframe(id: number, isIframe: number) {
  return put({
    url: '/ui/element/iframe',
    data: () => {
      return {
        id: id,
        is_iframe: isIframe,
      }
    },
  })
}

export function putUiUiElementTest(data: object) {
  return post({
    url: '/ui/element/test',
    data: () => {
      return data
    },
  })
}

export function getUiUiElementName(id: any) {
  return get({
    url: '/ui/element/name',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getUiElementUpload(data: any) {
  return post({
    url: '/ui/element/upload',
    data: () => {
      return data
    },
  })
}
