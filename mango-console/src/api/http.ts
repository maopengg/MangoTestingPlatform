import { AxiosResponse } from 'axios'
import type { App } from 'vue'
import request from './axios.config'
import { Message } from '@arco-design/web-vue'
import { handleAuthExpired, isAuthExpiredResponse } from './auth-expired'
import { ApiBusinessError } from './errors'
import usePermissionStore from '@/store/modules/permission'
import { requestPermission } from '@/utils/permission'
import {
  containsLosslessJsonNumber,
  parseApiConfigLosslessJson,
  stringifyLosslessJson,
} from '@/utils/lossless-json'

// 定义请求选项
export interface HttpOption {
  url: string
  data?: any
  method?: string
  headers?: any
  losslessJson?: boolean
  silentError?: boolean
  timeout?: number
  beforeRequest?: () => void
  afterRequest?: () => void
}

// 定义响应数据选项，这个需要根据后台人员给的实际字段来配置
export interface Response<T = any> {
  totalSize: number | 0
  code: number
  msg: string
  data: T
}

// 通用的http请求方法，需要自己指定 'POST' 还是 'GET' 请求
export function http<T = any>({
  url,
  data,
  method,
  headers,
  losslessJson,
  silentError,
  timeout,
  beforeRequest,
  afterRequest,
}: HttpOption) {
  const successHandler = (res: AxiosResponse<Response<T>>) => {
    if (res.data.code === 200) {
      return res.data
    } else if (!res.data.msg) {
      return res.data
    }
    if (isAuthExpiredResponse(res.status, res.data.code, res.data.msg)) {
      handleAuthExpired(res.data.msg)
    } else if (!silentError) {
      Message.error(res.data.msg)
    }
    throw new ApiBusinessError(res.data.msg || '请求失败，未知异常', res.data.code)
  }
  const failHandler = (error: Response<Error>) => {
    afterRequest && afterRequest()
    throw new Error(error.msg || '请求失败，未知异常')
  }
  method = method || 'GET'
  const params = Object.assign(typeof data === 'function' ? data() : data || {}, {})
  const permissions = usePermissionStore()
  const required = requestPermission(permissions.httpPermissions || [], method, url, params)
  if (required && !permissions.hasPermission(required)) {
    if (!silentError) Message.error('当前角色没有此操作权限，请联系管理员授权')
    afterRequest && afterRequest()
    return Promise.reject(new ApiBusinessError('当前角色没有此操作权限，请联系管理员授权', 403))
  }
  beforeRequest && beforeRequest()
  const requestData = containsLosslessJsonNumber(params) ? stringifyLosslessJson(params) : params
  const requestConfig = {
    headers,
    ...(timeout === undefined ? {} : { timeout }),
    ...(losslessJson
      ? {
          transformResponse: [
            (responseData: any) =>
              typeof responseData === 'string' && responseData
                ? parseApiConfigLosslessJson(responseData)
                : responseData,
          ],
        }
      : {}),
  }
  return method === 'GET'
    ? request.get(url, { params, ...requestConfig }).then(successHandler, failHandler)
    : method === 'DELETE'
    ? request.delete(url, { params, ...requestConfig }).then(successHandler, failHandler)
    : method === 'PUT'
    ? request.put(url, requestData, requestConfig).then(successHandler, failHandler)
    : request.post(url, requestData, requestConfig).then(successHandler, failHandler)
}

// 请求方式被固定成 'GET'的请求方法
export function get<T = any>({
  url,
  data,
  method = 'GET',
  beforeRequest,
  afterRequest,
  losslessJson,
  silentError,
  timeout,
}: HttpOption): Promise<Response<T>> {
  return http<T>({
    url,
    method,
    data,
    beforeRequest,
    afterRequest,
    losslessJson,
    silentError,
    timeout,
  })
}

// 请求方式被固定成 'POST'的请求方法
export function post<T = any>({
  url,
  data,
  method = 'POST',
  headers,
  beforeRequest,
  afterRequest,
  losslessJson,
  silentError,
}: HttpOption): Promise<Response> {
  return http<T>({
    url,
    method,
    data,
    headers,
    beforeRequest,
    afterRequest,
    losslessJson,
    silentError,
  })
}

export function put<T = any>({
  url,
  data,
  method = 'PUT',
  beforeRequest,
  afterRequest,
  losslessJson,
  silentError,
}: HttpOption): Promise<Response> {
  return http<T>({
    url,
    method,
    data,
    beforeRequest,
    afterRequest,
    losslessJson,
    silentError,
  })
}

export function deleted<T = any>({
  url,
  data,
  method = 'DELETE',
  beforeRequest,
  afterRequest,
  silentError,
}: HttpOption): Promise<Response> {
  return http<T>({
    url,
    method,
    data,
    beforeRequest,
    afterRequest,
    silentError,
  })
}

// 这里的声明主要以 'option api' 方式定义的组件提供选项，当然前提是你使用typescript语言开发的
function install(app: App): void {
  app.config.globalProperties.$http = http

  app.config.globalProperties.$get = get

  app.config.globalProperties.$post = post
  app.config.globalProperties.$put = put
  app.config.globalProperties.$deleted = deleted
}

export default {
  install,
  get,
  post,
  put,
  deleted,
}

declare module '@vue/runtime-core' {
  // 为 `this.$` 提供类型声明
  interface ComponentCustomProperties {
    $get: <T>(options: HttpOption) => Promise<Response<T>>
    $post: <T>(options: HttpOption) => Promise<Response<T>>
    $put: <T>(options: HttpOption) => Promise<Response<T>>
    $delete: <T>(options: HttpOption) => Promise<Response<T>>
    $http: <T>(options: HttpOption) => Promise<Response<T>>
  }
}
