export const methodOptions = [
  { label: 'GET', value: 0 },
  { label: 'POST', value: 1 },
  { label: 'PUT', value: 2 },
  { label: 'DELETE', value: 3 },
  { label: 'OPTIONS', value: 4 },
  { label: 'PATCH', value: 6 },
]

export const debugMethodOptions = methodOptions.map((item) => ({
  label: item.label,
  value: item.label,
}))

export const emptyResponse = () => ({
  status_code: 200,
  content_type: 'application/json',
  headers: {},
  body_type: 'json' as const,
  body: '{}',
  delay_ms: 0,
})

export const configSections = [
  { key: 'basic', title: '基础配置', description: '地址、方法、解密和记录策略' },
  { key: 'assertions', title: '请求断言', description: '校验请求参数是否合法' },
  { key: 'rules', title: '响应规则', description: '按条件匹配返回内容' },
  { key: 'default', title: '默认响应', description: '没有规则命中时返回' },
]
export const requestDecryptionOptions = [
  { label: '不解密', value: 'none' },
  { label: '飞书事件订阅', value: 'lark_event' },
]
export const sourceOptions = [
  { label: 'Path参数', value: 'path' },
  { label: 'Query参数', value: 'query' },
  { label: '请求头', value: 'header' },
  { label: 'JSON请求体', value: 'json_body' },
  { label: '文本请求体', value: 'text_body' },
]
export const bodyTypeOptions = [
  { label: 'JSON', value: 'json' },
  { label: '文本', value: 'text' },
  { label: 'HTML', value: 'html' },
  { label: 'XML', value: 'xml' },
  { label: '空响应', value: 'empty' },
]
