import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { isValidInteger } from '@/utils/form'

export const columns: any = reactive([
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
])
export const formItems: FormItem[] = reactive([
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
])
export const formParameterItems: FormItem[] = reactive([
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
    label: '预期调用结果',
    key: 'protocol_expectation_mode',
    value: ref('auto'),
    type: 'select',
    required: true,
    placeholder: '自动模式：有场景断言时由断言判定，否则要求 HTTP 2xx。',
    optionItems: [
      { label: '自动判断（推荐）', value: 'auto' },
      { label: '正常成功（HTTP 2xx）', value: 'success' },
      { label: '指定 HTTP 状态码', value: 'codes' },
      { label: '任意状态（不推荐）', value: 'any' },
    ],
    reset: function () {
      this.value = 'auto'
    },
  },
  {
    label: '预期状态码',
    key: 'protocol_expectation_codes',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '多个状态码用英文逗号分隔，例如：400,422',
    reset: function () {
      this.value = ''
    },
    validator: function () {
      const mode = formParameterItems.find((item) => item.key === 'protocol_expectation_mode')?.value
      if (mode !== 'codes') return true
      const parts = String(this.value || '')
        .split(',')
        .map((code) => code.trim())
        .filter(Boolean)
      const valid = parts.length > 0 && parts.every((code) => {
        const statusCode = Number(code)
        return Number.isInteger(statusCode) && statusCode >= 100 && statusCode <= 599
      })
      if (!valid) {
        Message.error('请输入100到599之间的HTTP状态码，多个状态码用英文逗号分隔')
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
])
