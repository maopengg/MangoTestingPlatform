import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { isValidInteger } from '@/utils/form'

export const columns: any = reactive([
  {
    title: '接口名称',
    dataIndex: 'api_name',
  },
  {
    title: '测试结果',
    dataIndex: 'status',
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 180,
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '模块',
    key: 'module',
    value: ref(''),
    placeholder: '请选择测试模块',
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
    label: '接口',
    key: 'api_info',
    value: ref(''),
    placeholder: '请选择测试模块',
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
    label: '失败间隔',
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
])
