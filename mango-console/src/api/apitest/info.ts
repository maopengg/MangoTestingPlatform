import { deleted, get, post, put } from '@/api/http'

export function postApiImportUrl(data: object) {
  return post({
    url: '/api/info/import/api',
    data: () => {
      return data
    },
  })
}

export function getApiInfoName(moduleId: any) {
  return get({
    url: '/api/info/name',
    data: () => {
      return {
        module_id: moduleId,
      }
    },
  })
}

export function getApiInfo(data: object) {
  return get({
    url: '/api/info',
    data: () => {
      return data
    },
  })
}

export function postApiInfo(data: object) {
  return post({
    url: '/api/info',
    data: () => {
      return data
    },
  })
}

export function putApiInfo(data: object) {
  return put({
    url: '/api/info',
    data: () => {
      return data
    },
  })
}

export function deleteApiInfo(id: number | string[] | number[]) {
  return deleted({
    url: '/api/info',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getApiCaseInfoRun(id: number | string[], testObj: any) {
  return get({
    url: '/api/info/test',
    data: () => {
      return {
        id: id,
        test_env: testObj,
      }
    },
  })
}

export function putApiPutApiInfoType(idList: string[], type: number) {
  return put({
    url: '/api/info/type',
    data: () => {
      return {
        id_list: idList,
        type: type,
      }
    },
  })
}

export function postApiCopyInfo(id: number) {
  return post({
    url: '/api/info/copy',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postApiUploadApi(type: number, file?: File) {
  const formData = new FormData()
  formData.append('type', type.toString())
  if (file) {
    formData.append('file', file)
  }
  
  return post({
    url: '/api/upload/api',
    data: () => formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
