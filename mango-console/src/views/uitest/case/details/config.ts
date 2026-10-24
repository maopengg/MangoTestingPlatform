import { reactive, ref } from 'vue'
import { FormItem } from '@/types/components'
import { Message } from '@arco-design/web-vue'
import { isValidInteger } from '@/utils/form'

export const formItems: FormItem[] = reactive([
  {
    label: '模块名称',
    key: 'module',
    value: ref(''),
    placeholder: '请选择模块名称',
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
    label: '选择页面',
    key: 'page',
    value: ref(''),
    placeholder: '请选择测试页面',
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
    label: '页面步骤',
    key: 'page_step',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择页面步骤',
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
])
