import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getApiInfo } from '@/api/apitest/info'
import { getApiHeaders } from '@/api/apitest/headers'
import { getUserTestObject } from '@/api/system/test_object'
import { stringifyLosslessJson } from '@/utils/lossless-json'

const httpMethods: Record<number, string> = {
  0: 'GET',
  1: 'POST',
  2: 'PUT',
  3: 'DELETE',
  4: 'OPTIONS',
  6: 'PATCH',
}

export function canCopyApiInfoCurl(record: any) {
  return record?.method !== null && record?.method !== undefined && record?.method !== '' &&
    ['http', 'sse'].includes(String(record?.protocol_type || 'http').toLowerCase()) &&
    Boolean(httpMethods[Number(record?.method)])
}

function quote(value: unknown) {
  return `'${String(value ?? '').replace(/'/g, `'\\''`)}'`
}

function parseObject(value: any, label: string): Record<string, any> {
  if (value === null || value === undefined || value === '') return {}
  let parsed = value
  if (typeof value === 'string') {
    try {
      parsed = JSON.parse(value)
    } catch {
      throw new Error(`${label}不是合法 JSON，无法生成 cURL`)
    }
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`${label}必须是 JSON 对象`)
  }
  return parsed
}

function projectProductId(record: any) {
  return record?.project_product?.id ?? record?.project_product
}

async function loadApiInfo(recordOrId: any) {
  const id = typeof recordOrId === 'object' ? recordOrId?.id : recordOrId
  if (!id) throw new Error('未找到接口 ID')
  if (typeof recordOrId === 'object') return recordOrId
  const response = await getApiInfo({ id })
  const record = Array.isArray(response.data) ? response.data[0] : null
  if (!record) throw new Error('未找到接口配置')
  return record
}

async function loadHeaders(record: any): Promise<Record<string, any>> {
  if (record.headers !== null && record.headers !== undefined) {
    return parseObject(record.headers, '接口请求头')
  }
  const productId = projectProductId(record)
  if (!productId) throw new Error('接口未绑定产品，无法查询默认请求头')
  const response = await getApiHeaders({ project_product: productId, status: 1 })
  if (!Array.isArray(response.data)) throw new Error('默认请求头查询失败')
  return response.data.reduce((headers: Record<string, any>, item: any) => {
    if (item.key) headers[item.key] = item.value
    return headers
  }, {})
}

async function loadUrl(record: any, environment: number | string | null) {
  const path = String(record.url || '').trim()
  if (!path) throw new Error('接口未配置请求路径')
  if (/^https?:\/\//i.test(path)) return new URL(path)
  if (environment === null || environment === undefined || environment === '') {
    throw new Error('请先选择测试环境，再复制 cURL')
  }
  const productId = projectProductId(record)
  if (!productId) throw new Error('接口未绑定产品，无法查询测试环境地址')
  const response = await getUserTestObject({ project_product: productId, environment })
  const objects = Array.isArray(response.data) ? response.data : []
  const matches = objects.filter((item: any) => [0, 2].includes(Number(item.auto_type)))
  if (matches.length !== 1 || !matches[0].value) {
    throw new Error('当前产品和测试环境没有唯一的 API 服务地址')
  }
  return new URL(path, matches[0].value)
}

function appendParams(url: URL, value: any) {
  if (value === null || value === undefined || value === '') return
  let params = value
  if (typeof value === 'string') {
    try {
      params = JSON.parse(value)
    } catch {
      if (value.trim().startsWith('{') || value.trim().startsWith('[')) {
        throw new Error('接口参数不是合法 JSON，无法生成 cURL')
      }
      params = Array.from(new URLSearchParams(value).entries())
    }
  }
  const entries: Array<[string, any]> = Array.isArray(params)
    ? params.map((item: any) => [String(item[0]), item[1]])
    : Object.entries(parseObject(params, '接口参数'))
  for (const [key, entryValue] of entries) {
    if (entryValue === null || entryValue === undefined) continue
    const placeholder = `{${key}}`
    const encodedPlaceholder = encodeURIComponent(placeholder)
    if (url.pathname.includes(encodedPlaceholder) && typeof entryValue !== 'object') {
      url.pathname = url.pathname.replaceAll(encodedPlaceholder, encodeURIComponent(String(entryValue)))
      continue
    }
    if (Array.isArray(entryValue)) {
      entryValue.forEach((item) => url.searchParams.append(key, String(item)))
    } else {
      url.searchParams.append(key, String(entryValue))
    }
  }
}

function appendBody(parts: string[], record: any, headers: Record<string, any>) {
  const type = String(record.body_type || 'none')
  const config = record.body_config || {}
  if (type === 'none') return
  if (type === 'json') {
    const body = config.source_type === 'template'
      ? String(config.body_text || '')
      : stringifyLosslessJson(config.body ?? {})
    parts.push(`  --data-raw ${quote(body)}`)
    if (!Object.keys(headers).some((key) => key.toLowerCase() === 'content-type')) {
      headers['Content-Type'] = 'application/json'
    }
  } else if (type === 'raw') {
    parts.push(`  --data-raw ${quote(config.body_text || '')}`)
    if (!Object.keys(headers).some((key) => key.toLowerCase() === 'content-type')) {
      headers['Content-Type'] = config.content_type || 'application/json'
    }
  } else if (type === 'form' || type === 'multipart') {
    for (const field of config.fields || []) {
      if (!field.key) continue
      const option = type === 'form' ? '--data-urlencode' : '--form'
      parts.push(`  ${option} ${quote(`${field.key}=${field.value ?? ''}`)}`)
    }
    if (type === 'form' && !Object.keys(headers).some((key) => key.toLowerCase() === 'content-type')) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded'
    }
    if (type === 'multipart') {
      for (const file of config.files || []) {
        if (file.key) parts.push(`  --form ${quote(`${file.key}=@/path/to/${file.file_name || 'file'}`)}`)
      }
      for (const key of Object.keys(headers)) {
        if (key.toLowerCase() === 'content-type') delete headers[key]
      }
    }
  }
}

export async function buildApiInfoCurl(record: any, environment: number | string | null) {
  if (!canCopyApiInfoCurl(record)) {
    throw new Error('当前协议不支持生成 HTTP cURL')
  }
  const method = httpMethods[Number(record.method)]
  if (!method) throw new Error('当前请求方法不支持生成 cURL')
  const [url, headers] = await Promise.all([loadUrl(record, environment), loadHeaders(record)])
  appendParams(url, record.params)
  const parts = [`curl --location ${record.protocol_type === 'sse' ? '--no-buffer ' : ''}--request ${quote(method)} ${quote(url.toString())}`]
  const bodyParts: string[] = []
  appendBody(bodyParts, record, headers)
  if (record.protocol_type === 'sse' && !Object.keys(headers).some((key) => key.toLowerCase() === 'accept')) {
    headers.Accept = 'text/event-stream'
  }
  Object.entries(headers).forEach(([key, value]) => {
    if (value !== null && value !== undefined) parts.push(`  --header ${quote(`${key}: ${value}`)}`)
  })
  parts.push(...bodyParts)
  return parts.join(' \\\n')
}

async function copyText(value: string) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(value)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = value
  textarea.setAttribute('readonly', 'readonly')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  textarea.remove()
  if (!copied) throw new Error('浏览器未允许复制到剪贴板')
}

export function useApiInfoCurl() {
  const copyingId = ref<string | null>(null)

  async function copyApiInfoCurl(recordOrId: any, environment: number | string | null) {
    const id = String(typeof recordOrId === 'object' ? recordOrId?.id : recordOrId)
    if (copyingId.value) return
    copyingId.value = id
    try {
      const record = await loadApiInfo(recordOrId)
      const command = await buildApiInfoCurl(record, environment)
      await copyText(command)
      Message.success('复制 cURL 成功')
      const configuredValues = stringifyLosslessJson({
        url: record.url,
        headers: record.headers,
        params: record.params,
        body_config: record.body_config,
      })
      if (/\$\{\{[^}]+\}\}/.test(configuredValues) || /\$\{\{[^}]+\}\}/.test(command)) {
        Message.warning('cURL 中有运行时变量，请填入实际值后再执行')
      }
      if (record.body_type === 'multipart' && record.body_config?.files?.length) {
        Message.warning('文件字段使用本地路径占位符，请替换后再执行')
      }
    } catch (error: any) {
      Message.error(error?.message || '复制 cURL 失败')
    } finally {
      copyingId.value = null
    }
  }

  return { copyingId, copyApiInfoCurl }
}
