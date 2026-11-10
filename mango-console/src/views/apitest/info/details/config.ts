export const configNavItems: Array<{
  key: string
  title: string
  description: string
  disabled?: boolean
}> = [
  { key: '0', title: '请求头', description: '维护接口请求 Headers' },
  { key: '1', title: '参数', description: '维护查询参数' },
  { key: '2', title: '请求体', description: '维护 Body 配置' },
  {
    key: '5',
    title: '后置 JSONPath 提取',
    description: '从响应 JSON 提取值写入缓存，未匹配时执行失败',
  },
  {
    key: '6',
    title: '后置正则提取',
    description: '从响应文本提取首个匹配值写入缓存，未匹配时执行失败',
  },
  {
    key: '7',
    title: '后置自定义函数',
    description: '请求完成后执行自定义函数，可处理响应并操作运行缓存',
  },
]
export const POSTERIOR_FUNC_TEMPLATE = `def func(self, response):
    # self 是当前执行上下文，常用能力：
    # self.test_setup.test_data：变量/缓存工具，支持 get_cache、set_cache、replace 等
    test_data = self.test_setup.test_data

    # response 是本次接口响应模型，常用字段：
    code = response.code  # HTTP 状态码
    time = response.time  # 响应耗时，单位秒
    url = response.url  # 实际请求 URL
    headers = response.headers or {}  # 响应头
    json_body = response.json  # 解析后的 JSON，可能是 dict/list/str/number/bool/null
    text = response.text  # 原始响应文本，非 JSON 或文本断言可使用
    response_mode = response.response_mode  # 响应模式：http/sse/grpc/websocket
    sse_events = response.sse_events  # SSE 事件列表，仅 SSE 场景有值
    sse_stop_reason = response.sse_stop_reason  # SSE 停止原因
    request_body = response.request_body  # 实际发送的请求体
    request_headers = response.request_headers  # 实际发送的请求头

    # 提取响应数据到缓存示例
    if isinstance(json_body, dict):
        data = json_body.get('data') or {}
        if isinstance(data, dict) and data.get('id'):
            test_data.set_cache('response_id', data.get('id'))

    # 修改响应示例：追加自定义错误信息
    if code >= 400 and not response.error_msg:
        response.error_msg = text

    return response`

export const textareaAutoSize = { minRows: 16, maxRows: 22 }
export const fallbackMethodOptions = [
  { label: 'GET', value: 0 },
  { label: 'POST', value: 1 },
  { label: 'PUT', value: 2 },
  { label: 'DELETE', value: 3 },
  { label: 'OPTIONS', value: 4 },
  { label: 'PATCH', value: 6 },
]
export const apiInfoEditableFields = [
  'url',
  'method',
  'protocol_type',
  'headers',
  'params',
  'is_text_params',
  'body_type',
  'body_config',
  'sse_config',
  'mcp_config',
  'posterior_json_path',
  'posterior_re',
  'posterior_func',
  'status',
]
