import { Message } from '@arco-design/web-vue'

function parseJson(value: any) {
  if (typeof value !== 'string') return value
  const text = value.trim()
  if (!text || (!text.startsWith('{') && !text.startsWith('['))) return value
  try {
    return JSON.parse(text)
  } catch {
    return value
  }
}

function entries(value: any): Array<[string, any]> {
  const parsed = parseJson(value)
  if (!parsed) return []
  if (!Array.isArray(parsed)) return typeof parsed === 'object' ? Object.entries(parsed) : []
  return parsed
    .map((item) => {
      if (Array.isArray(item)) return [item[0], item[1]] as [string, any]
      if (!item || typeof item !== 'object') return null
      const key = item.key ?? item.name
      return key ? ([key, item.value ?? item.val] as [string, any]) : null
    })
    .filter(Boolean) as Array<[string, any]>
}

function quote(value: any) {
  return `'${String(value ?? '').replace(/'/g, `'\\''`)}'`
}

function getRequestData(item: any) {
  const result = item?.result_data || {}
  const request = result.request || {}
  const response = result.response || {}
  return {
    request,
    response,
    params: response.request_params ?? request.params,
    body: response.request_body ?? request.request_body ?? request.data ?? request.json,
    files: response.request_file ?? request.request_files ?? request.file,
  }
}

function buildCurl(item: any) {
  const { request, response, params, body, files } = getRequestData(item)
  const method = String(
    request.method || response.request_method || item?.method || 'GET'
  ).toUpperCase()
  const rawUrl = request.url || response.url || response.request_url || item?.url
  if (!rawUrl) throw new Error('暂无实际请求 URL，请先执行该场景后再复制 cURL')
  const query = entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  const url = query && !String(rawUrl).includes('?') ? `${rawUrl}?${query}` : String(rawUrl)
  const headers = entries(response.request_headers ?? request.headers ?? item?.headers).filter(
    ([key, value]) => key && value !== undefined && value !== null && value !== ''
  )
  const parts = [`curl --location --request ${quote(method)} ${quote(url)}`]
  headers.forEach(([key, value]) => parts.push(`  --header ${quote(`${key}: ${value}`)}`))
  const fileEntries = entries(files)
  const multipart =
    fileEntries.length > 0 ||
    headers.some(
      ([key, value]) =>
        String(key).toLowerCase() === 'content-type' &&
        String(value).toLowerCase().includes('multipart/form-data')
    )
  if (multipart) {
    fileEntries.forEach(([key, value]) => parts.push(`  --form ${quote(`${key}=@${value}`)}`))
    entries(body).forEach(([key, value]) => parts.push(`  --form ${quote(`${key}=${value}`)}`))
  } else if (body !== undefined && body !== null && body !== '') {
    const parsedBody = parseJson(body)
    parts.push(
      `  --data-raw ${quote(
        typeof parsedBody === 'string' ? parsedBody : JSON.stringify(parsedBody)
      )}`
    )
  }
  return parts.join(' \\\n')
}

async function copyText(text: string) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'readonly')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  document.body.removeChild(textarea)
  if (!copied) throw new Error('copy failed')
}

export function useScenarioCurl() {
  async function copyScenarioCurl(item: any) {
    try {
      await copyText(buildCurl(item))
      Message.success('复制 cURL 成功')
    } catch (error: any) {
      Message.error(error?.message || '复制 cURL 失败')
    }
  }
  return { copyScenarioCurl }
}
