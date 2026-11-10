import { FormItem } from '@/types/components'
import { ref } from 'vue'
import type { TableColumnData } from '@arco-design/web-vue'
import { Message } from '@arco-design/web-vue'
import { isValidInteger } from '@/utils/form'

export const columns: TableColumnData[] = [
  {
    title: '接口名称',
    dataIndex: 'api_name',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '结果',
    dataIndex: 'status',
    align: 'center',
    width: 80,
  },
  {
    title: '失败提示',
    dataIndex: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 160,
    fixed: 'right',
  },
]
export function createStepFormItems(): FormItem[] {
  return [
    {
      label: '模块名称',
      key: 'module',
      value: ref(''),
      placeholder: '请选择测试模块名称',
      required: true,
      type: 'cascader',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '接口名称',
      key: 'api_info',
      value: ref(''),
      placeholder: '请选择接口名称',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '接口版本',
      key: 'pinned_api_info_revision',
      value: ref(''),
      placeholder: '请选择接口版本',
      required: true,
      type: 'select',
      hidden: true,
      validator: function () {
        if (!this.value) {
          Message.error('请选择已发布的接口')
          return false
        }
        return true
      },
    },
  ]
}
export function createScenarioFormItems(): FormItem[] {
  const formParameterItems: FormItem[] = [
    {
      label: '场景名称',
      key: 'name',
      value: ref(''),
      placeholder: '请输入场景名称',
      required: true,
      type: 'input',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '失败重试',
      key: 'error_retry',
      value: ref(''),
      type: 'input',
      required: false,
      placeholder: '请输入重试次数，整数类型',
      validator: function () {
        if (!this.value && !this.required) {
          return true
        }
        if (!isValidInteger(this.value)) {
          Message.error(`${this.label}请输入正整数！`)
          return false
        }
        return true
      },
    },
    {
      label: '重试间隔',
      key: 'retry_interval',
      value: ref(''),
      type: 'input',
      required: false,
      placeholder: '请输入重试间隔，每次失败会等待N秒后再试',
      validator: function () {
        if (!this.value && !this.required) {
          return true
        }
        if (!isValidInteger(this.value)) {
          Message.error(`${this.label}请输入正整数！`)
          return false
        }
        return true
      },
    },
    {
      label: '允许失败',
      key: 'allow_failure',
      value: ref(false),
      type: 'switch',
      required: false,
      placeholder: '请勿轻易开启；仅用于已确认可忽略的场景，失败将只记警告并继续执行。',
      reset: function () {
        this.value = false
      },
    },
  ]
  return formParameterItems
}

export const FRONT_FUNC_TEMPLATE = `def func(self, request):
    # self 是当前执行上下文，常用能力：
    # self.test_setup.test_data：变量/缓存工具，支持 get_cache、set_cache、replace 等
    # self.case_parameter：当前场景参数对象，可查看当前场景配置
    test_data = self.test_setup.test_data
    try:
        username = test_data.get_cache('username')
    except Exception:
        username = None

    # request 是本次即将发送的请求模型，常用字段：
    method = request.method  # 请求方法：GET/POST/PUT/PATCH/DELETE...
    url = request.url  # 请求地址，通常已拼接环境域名
    headers = request.headers or {}  # 请求头
    params = request.params  # Query 参数，支持 dict/list/str
    protocol_type = request.protocol_type  # 协议类型：http/sse
    body_type = request.body_type  # 请求体类型：none/json/form/raw/multipart
    body_config = request.body_config or {}  # 请求体配置
    sse_config = request.sse_config  # SSE 停止条件配置
    posterior_file = request.posterior_file  # 响应文件保存到缓存的 key

    # 修改请求示例：追加请求头
    headers['X-Debug-User'] = username or 'anonymous'
    request.headers = headers

    # 修改 JSON 请求体示例
    if body_type == 'json':
        body = body_config.get('body_text') if body_config.get('source_type') == 'template' else body_config.get('body')
        if isinstance(body, dict):
            body['operator'] = username
            request.body_config = {'source_type': 'value', 'body': body}

    return request`

export const POSTERIOR_FUNC_TEMPLATE = `def func(self, response):
    # self 是当前执行上下文，常用能力：
    # self.test_setup.test_data：变量/缓存工具，支持 get_cache、set_cache、replace 等
    # self.case_parameter：当前场景参数对象，可查看当前场景配置
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
