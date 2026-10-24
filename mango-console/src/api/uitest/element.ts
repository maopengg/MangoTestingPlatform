import { deleted, get, post, put } from '@/api/http'

export function getUiElement(data: object) {
  return get({
    url: '/ui/element',
    data: () => {
      return data
    },
  })
}

export function getUiElementCategory(data: object) {
  return get({
    url: '/ui/element/category',
    data: () => {
      return data
    },
  })
}

export function getUiElementIdentity(data: {
  page_id: number | string
  name: string
  category: string
  current_id?: number | string
}) {
  return get({
    url: '/ui/element/identity',
    data: () => data,
  })
}

export function getUiElementAiInfo(data: object) {
  return get({
    url: '/ui/element/ai/info',
    data: () => {
      return data
    },
  })
}

export function getUiElementAiSnapshots(data: object) {
  return get({
    url: '/ui/element/ai/snapshots',
    data: () => data,
  })
}

export function getUiElementAiSnapshotDetail(data: object) {
  return get({
    url: '/ui/element/ai/snapshot/detail',
    data: () => data,
  })
}

export function getUiElementAiHealRecords(data: object) {
  return get({
    url: '/ui/element/ai/heal-records',
    data: () => data,
  })
}

export function getUiElementAiHealRecordDetail(data: object) {
  return get({
    url: '/ui/element/ai/heal-record/detail',
    data: () => data,
  })
}

export function putUiElementAiHealApply(data: object) {
  return put({
    url: '/ui/element/ai/heal-record/apply',
    data: () => {
      return data
    },
  })
}

export function postUiElementAiSnapshot(data: object) {
  return post({
    url: '/ui/element/ai/snapshot',
    data: () => {
      return data
    },
  })
}

export function postUiElementAiLocatorRecommend(data: object) {
  return post({
    url: '/ui/element/ai/locator/recommend',
    data: () => data,
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

export function postUiElementCheck(data: object) {
  return post({
    url: '/ui/element/check',
    data: () => {
      return data
    },
  })
}

export function postUiElementScan(data: {
  page_id: number | string
  workspace_id: string
  mode: 'quick' | 'deep' | 'region'
}) {
  return post({
    url: '/ui/element/scan',
    data: () => data,
  })
}

export function putUiElementDeepCheckApply(data: {
  element_id: number | string
  task_id: number | string
}) {
  return put({
    url: '/ui/element/check-result/apply',
    data: () => data,
  })
}

export function postUiElementOpenBrowser(data: {
  page_id: number | string
  test_env: number
}) {
  return post({
    url: '/ui/element/browser/open',
    data: () => data,
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
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    data: () => {
      return data
    },
  })
}
