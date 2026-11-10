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
    losslessJson: true,
    data: () => {
      return data
    },
  })
}

export async function getApiInfoOptions(projectProductId: number | string, isCurrent: () => boolean = () => true) {
  const items: any[] = []
  const seen = new Set<string>()
  const pageSize = 200
  for (let page = 1; isCurrent(); page += 1) {
    const response = await getApiInfo({ project_product: projectProductId, summary: true, page, pageSize })
    if (!isCurrent()) return []
    const batch = response.data || []
    const fresh = batch.filter((item: any) => !seen.has(String(item.id)))
    fresh.forEach((item: any) => seen.add(String(item.id)))
    items.push(...fresh)
    if (!fresh.length || batch.length < pageSize || items.length >= Number(response.totalSize)) break
  }
  return items
}

export function getApiInfoBoundCases(id: number | string) {
  return get({
    url: '/api/info/bound/cases',
    data: () => {
      return {
        id,
      }
    },
  })
}

export function postApiInfo(data: object) {
  return post({
    url: '/api/info',
    losslessJson: true,
    data: () => {
      return data
    },
  })
}

export function putApiInfo(data: object) {
  return put({
    url: '/api/info',
    losslessJson: true,
    data: () => {
      return data
    },
  })
}

export function deleteApiInfo(id: number | string | Array<number | string>) {
  return deleted({
    url: '/api/info',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getApiInfoExecutionParameters(target: { id: number | string; revision_id?: number; release_id?: number }) {
  return get({ url: '/api/info/execution/parameters', data: () => target })
}

export function getApiCaseInfoRun(id: number | string[] | string, testObj: any, version?: object, runtimeParameters?: Record<string, unknown>) {
  return post({
    url: '/api/info/test',
    data: () => {
      return {
        id: id,
        test_env: testObj,
        ...(version || {}),
        runtime_parameters: runtimeParameters || {},
      }
    },
  })
}

export function postApiInfoBatchRun(
  apiItems: Array<{ api_info_id: number | string; api_info_release_id: number | string }>,
  testEnv: number | string,
  runtimeParameters?: Record<string, unknown>
) {
  return post({
    url: '/api/info/batch',
    data: () => ({
      api_items: apiItems,
      test_env: testEnv,
      runtime_parameters: runtimeParameters || {},
    }),
  })
}

export function putSetSchema(id: number) {
  return put({
    url: '/api/info/schema',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postApiUploadApi(file?: File) {
  const formData = new FormData()
  if (file) {
    formData.append('file', file)
  }

  return post({
    url: '/api/upload/api',
    data: () => formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function getGrpcServices(data: object) {
  return get({
    url: '/api/grpc/service',
    data: () => data,
  })
}

export function getGrpcMethods(data: object) {
  return get({
    url: '/api/grpc/method',
    data: () => data,
  })
}

export function postGrpcMethodSync(data: object) {
  return post({
    url: '/api/grpc/method/sync',
    data: () => data,
  })
}

export function postGrpcMethodImportApiInfo(data: object) {
  return post({
    url: '/api/grpc/method/import/api-info',
    data: () => data,
  })
}
