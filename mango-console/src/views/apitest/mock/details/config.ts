export const methodOptions = [
  { label: 'GET', value: 0 }, { label: 'POST', value: 1 }, { label: 'PUT', value: 2 },
  { label: 'DELETE', value: 3 }, { label: 'OPTIONS', value: 4 }, { label: 'PATCH', value: 6 },
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
