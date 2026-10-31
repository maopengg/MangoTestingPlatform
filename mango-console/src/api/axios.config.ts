import Axios, { AxiosResponse } from 'axios'
import { Message } from '@arco-design/web-vue'
import qs from 'qs'
import { normalizeIdSearchParams } from '@/utils/id-search'
import CustomRequestInterceptor from './interceptors/CustomRequestInterceptor'
import UserTokenExpiredInterceptor from './interceptors/UserTokenExpiredInterceptor'

const deploymentConfig: { apiBase?: string; socketURL?: string; storageBase?: string } =
  typeof window === 'undefined' ? {} : (window as any).__MANGO_CONFIG__ || {}

function currentWebSocketURL(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  const host = window.location.port === '5173'
    ? `${window.location.hostname}:8011`
    : window.location.host
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${host}/ws/web/socket?`
}

function currentApiHost(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  if (window.location.port === '5173') {
    return `${window.location.hostname}:8000`
  }
  return window.location.host
}

function currentBaseURL(): string {
  if (typeof deploymentConfig.apiBase === 'string') return deploymentConfig.apiBase
  const envBaseURL = import.meta.env.VITE_APP_BASE_URL || ''
  if (typeof window === 'undefined') {
    return envBaseURL
  }
  if (window.location.port === '5173' && (!envBaseURL || envBaseURL.startsWith('/'))) {
    const protocol = window.location.protocol
    return `${protocol}//${currentApiHost()}${envBaseURL || '/api'}`
  }
  return envBaseURL
}

export const baseURL = currentBaseURL()
export const minioURL = deploymentConfig.storageBase ?? import.meta.env.VITE_APP_MINIO_URL
export const webSocketURL = deploymentConfig.socketURL || import.meta.env.VITE_APP_SOCKET_URL || currentWebSocketURL()

export const CONTENT_TYPE = 'Content-Type'

export const FORM_URLENCODED = 'application/x-www-form-urlencoded; charset=UTF-8'

export const APPLICATION_JSON = 'application/json; charset=UTF-8'

export const TEXT_PLAIN = 'text/plain; charset=UTF-8'

const service = Axios.create({
  baseURL,
  timeout: 10 * 60 * 1000,
})

const HTTP_ERROR_MESSAGE_MAP: Record<number, string> = {
  502: '服务网关异常，请稍后重试',
  503: '服务暂时不可用，请稍后重试或联系管理员检查服务状态',
  504: '服务响应超时，请稍后重试',
}

const ERROR_MESSAGE_INTERVAL = 3000
let lastHttpErrorMessageTime = 0

function showHttpErrorMessage(message: string) {
  const now = Date.now()
  if (now - lastHttpErrorMessageTime > ERROR_MESSAGE_INTERVAL) {
    Message.error(message)
    lastHttpErrorMessageTime = now
  }
}

function getHttpErrorMessage(error: any): string {
  const status = error.response?.status
  const responseMessage = error.response?.data?.msg
  if (responseMessage) {
    return responseMessage
  }
  if (status && HTTP_ERROR_MESSAGE_MAP[status]) {
    return HTTP_ERROR_MESSAGE_MAP[status]
  }
  if (!error.response) {
    return '服务连接异常，请检查网络或稍后重试'
  }
  return '服务器异常，请稍后重试'
}

// 在正式发送请求之前进行拦截配置
service.interceptors.request.use(
  (config) => {
    if (config.method?.toLowerCase() === 'get' && config.params &&
        typeof config.params === 'object' && !(config.params instanceof URLSearchParams)) {
      config.params = normalizeIdSearchParams(config.params)
    }
    !config.headers && (config.headers = {})
    if (!config.headers[CONTENT_TYPE]) {
      config.headers[CONTENT_TYPE] = APPLICATION_JSON
    }
    if (config.headers[CONTENT_TYPE] === FORM_URLENCODED) {
      config.data = qs.stringify(config.data)
    }
    return CustomRequestInterceptor(config)
  },
  (error) => {
    return Promise.reject(error.response)
  }
)

// 在接口返回数据的时候进行一次拦截
service.interceptors.response.use(
  (response: AxiosResponse): AxiosResponse => {
    UserTokenExpiredInterceptor(response)
    if (response.status === 200) {
      return response
    } else {
      throw new Error(response.status.toString())
    }
  },
  (error) => {
    if ([401, 403, 429].includes(error.response?.status)) {
      UserTokenExpiredInterceptor(error.response)
      return error.response
    }
    const message = getHttpErrorMessage(error)
    showHttpErrorMessage(message)
    if (import.meta.env.MODE === 'dev') {
      console.log(error)
    }
    return Promise.reject({ code: error.response?.status || 500, msg: message })
  }
)

export default service
