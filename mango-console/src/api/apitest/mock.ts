import { deleted, get, post, put } from '@/api/http'
import request, { baseURL } from '@/api/axios.config'

export interface MockResponseConfig {
  status_code: number
  content_type: string
  headers: Record<string, string>
  body_type: 'json' | 'text' | 'html' | 'xml' | 'empty'
  body: string
  delay_ms: number
}

export interface MockCondition {
  key: string
  name?: string
  enabled?: boolean
  source: 'path' | 'query' | 'header' | 'json_body' | 'text_body'
  field: string
  operator: string
  expected?: unknown
}

export interface MockAssertionMethodOption {
  label: string
  value: string
  requires_expected?: boolean
  children?: MockAssertionMethodOption[]
}

export interface MockRule {
  key: string
  name: string
  enabled: boolean
  matchers: MockCondition[]
  response: MockResponseConfig
}

export interface MockRequestDecryptionConfig {
  type: 'none' | 'lark_event'
  encrypt_key: string
  verification_token: string
  configuration_error?: string
}

export interface MockConfigPayload {
  id?: number
  project_product: number | string
  name: string
  mock_key: string
  description: string
  method: number
  path: string
  enabled: boolean
  record_call_log: boolean
  update_time?: string
  config: {
    methods: number[]
    assertions: MockCondition[]
    rules: MockRule[]
    default_response: MockResponseConfig
    request_decryption: MockRequestDecryptionConfig
  }
}

export function getMockConfigs(data: Record<string, unknown>) {
  return get({ url: '/api/mock/config', data: () => data })
}

export function getMockConfigDetail(id: number | string) {
  return get<MockConfigPayload>({ url: '/api/mock/config/detail', data: () => ({ id }) })
}

export function getMockAssertionMethods() {
  return get<MockAssertionMethodOption[]>({
    url: '/api/mock/config/assertion/methods',
    data: () => ({}),
  })
}

export function createMockConfig(data: MockConfigPayload) {
  return post({ url: '/api/mock/config', data: () => data, losslessJson: true })
}

export function updateMockConfig(data: MockConfigPayload) {
  return put({ url: '/api/mock/config', data: () => data, losslessJson: true })
}

export function deleteMockConfig(id: number | string) {
  return deleted({ url: '/api/mock/config', data: () => ({ id }) })
}

export function updateMockConfigState(
  id: number,
  data: { enabled?: boolean; record_call_log?: boolean }
) {
  return put({ url: '/api/mock/config/state', data: () => ({ id, ...data }) })
}

export interface MockInvokeResult {
  request_url: string
  request_method: string
  request_query: Record<string, unknown>
  request_headers: Record<string, string>
  request_body: string
  status: number
  status_text: string
  ok: boolean
  duration_ms: number
  trace_id: string
  response_headers: Record<string, string>
  response_body: unknown
}

export function getMockEndpointUrl(requestPath: string): string {
  const backendBase = new URL(baseURL || '/api', window.location.origin)
  const normalizedPath = requestPath.startsWith('/') ? requestPath : `/${requestPath}`
  const apiPrefix = backendBase.pathname.replace(/\/+$/, '')
  return new URL(`${apiPrefix}/mock${normalizedPath}`, backendBase.origin).toString()
}

export async function invokeMockEndpoint(data: {
  method: string
  requestPath: string
  query: Record<string, unknown>
  headers: Record<string, unknown>
  body?: string
}): Promise<MockInvokeResult> {
  const url = new URL(getMockEndpointUrl(data.requestPath))
  Object.entries(data.query).forEach(([key, value]) => {
    const values = Array.isArray(value) ? value : [value]
    values.forEach((item) => {
      if (item !== undefined && item !== null) url.searchParams.append(key, String(item))
    })
  })
  url.searchParams.set('__mango_mock_debug', '1')
  const headers = Object.fromEntries(
    Object.entries(data.headers).map(([key, value]) => [key, String(value)])
  )
  const started = performance.now()
  const response = await fetch(url.toString(), {
    method: data.method,
    headers,
    body: ['GET', 'HEAD'].includes(data.method) ? undefined : data.body || undefined,
  })
  const duration = Math.max(Math.round(performance.now() - started), 1)
  const responseText = await response.text()
  let responseBody: unknown = responseText
  try {
    responseBody = responseText ? JSON.parse(responseText) : ''
  } catch {
    responseBody = responseText
  }
  const responseHeaders: Record<string, string> = {}
  response.headers.forEach((value, key) => { responseHeaders[key] = value })
  const displayUrl = new URL(url.toString())
  displayUrl.searchParams.delete('__mango_mock_debug')
  const bodyTraceId = typeof responseBody === 'object' && responseBody !== null && 'trace_id' in responseBody
    ? String((responseBody as Record<string, unknown>).trace_id || '')
    : ''
  return {
    request_url: displayUrl.toString(),
    request_method: data.method,
    request_query: data.query,
    request_headers: headers,
    request_body: data.body || '',
    status: response.status,
    status_text: response.statusText,
    ok: response.ok,
    duration_ms: duration,
    trace_id: response.headers.get('x-mock-trace-id') || bodyTraceId,
    response_headers: responseHeaders,
    response_body: responseBody,
  }
}

export function getMockLogs(data: Record<string, unknown>) {
  return get({ url: '/api/mock/config/logs', data: () => data, losslessJson: true })
}

export function exportMockLogs(data: Record<string, unknown>) {
  return request.get('/api/mock/config/logs/export', {
    params: data,
    responseType: 'blob',
  })
}

export function clearMockLogs(id: number | string) {
  return deleted<{ deleted_count: number }>({
    url: '/api/mock/config/logs',
    data: () => ({ id }),
  })
}

export function clearAllMockLogs() {
  return deleted<{ deleted_count: number }>({
    url: '/api/mock/config/logs/all',
    data: () => ({}),
  })
}

export function getMockLogDetail(id: number | string) {
  return get({ url: '/api/mock/log/detail', data: () => ({ id }), losslessJson: true })
}
