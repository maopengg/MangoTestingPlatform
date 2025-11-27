import { AxiosResponse } from 'axios'
import type { App } from 'vue'
import request from './axios.config'
import { Message } from '@arco-design/web-vue'

// 用于节流登录过期提示，记录上次提示时间
let lastExpiredMessageTime = 0
const EXPIRED_MESSAGE_INTERVAL = 5000 // 5秒间隔

// 定义请求选项
export interface HttpOption {
  url: string
  data?: any
  method?: string
  headers?: any
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
  beforeRequest,
  afterRequest,
}: HttpOption) {
  const successHandler = (res: AxiosResponse<Response<T>>) => {
    if (res.data.code === 200) {
      return res.data
    } else if (!res.data.msg) {
      return res.data
    }
    if (res.data.msg === '当前用户登录已过期，请重新登录') {
      // 节流处理，确保登录过期提示每5秒最多显示一次
      const now = Date.now()
      if (now - lastExpiredMessageTime > EXPIRED_MESSAGE_INTERVAL) {
        Message.error(res.data.msg)
        lastExpiredMessageTime = now
      }
    } else {
      Message.error(res.data.msg)
    }
    throw new Error(res.data.msg || '请求失败，未知异常')
  }
  const failHandler = (error: Response<Error>) => {
    afterRequest && afterRequest()
    throw new Error(error.msg || '请求失败，未知异常')
  }
  beforeRequest && beforeRequest()
  method = method || 'GET'
  const params = Object.assign(typeof data === 'function' ? data() : data || {}, {})
  return method === 'GET'
    ? request.get(url, { params, headers }).then(successHandler, failHandler)
    : method === 'DELETE'
    ? request.delete(url, { params, headers }).then(successHandler, failHandler)
    : method === 'PUT'
    ? request.put(url, params, { headers: headers }).then(successHandler, failHandler)
    : request.post(url, params, { headers: headers }).then(successHandler, failHandler)
}

// 请求方式被固定成 'GET'的请求方法
export function get<T = any>({
  url,
  data,
  method = 'GET',
  beforeRequest,
  afterRequest,
}: HttpOption): Promise<Response> {
  return http<T>({
    url,
    method,
    data,
    beforeRequest,
    afterRequest,
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
}: HttpOption): Promise<Response> {
  return http<T>({
    url,
    method,
    data,
    headers,
    beforeRequest,
    afterRequest,
  })
}

export function put<T = any>({
  url,
  data,
  method = 'PUT',
  beforeRequest,
  afterRequest,
}: HttpOption): Promise<Response> {
  return http<T>({
    url,
    method,
    data,
    beforeRequest,
    afterRequest,
  })
}

export function deleted<T = any>({
  url,
  data,
  method = 'DELETE',
  beforeRequest,
  afterRequest,
}: HttpOption): Promise<Response> {
  return http<T>({
    url,
    method,
    data,
    beforeRequest,
    afterRequest,
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
