import { reactive, ref } from 'vue'
import { FormItem } from '@/types/components'
import { Message } from '@arco-design/web-vue'

export const columns: any = reactive([
  {
    title: '步骤名称',
    dataIndex: 'page_step_name',
    ellipsis: true,
    tooltip: true,
    width: 300,
  },
  {
    title: '切换URL',
    key: 'switch_step_open_url',
    dataIndex: 'switch_step_open_url',
    width: 90,
  },
  {
    title: '重试',
    key: 'error_retry',
    dataIndex: 'error_retry',
    width: 70,
  },
  {
    title: '状态',
    dataIndex: 'status',
    width: 70,
  },
  {
    title: '提示',
    dataIndex: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },

  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 140,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '选择模块',
    key: 'module',
    value: ref(''),
    placeholder: '请选择模块',
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
      if (!this.value) {
        return true
      }
      const num = Number(this.value)
      if (isNaN(num) || !Number.isInteger(num)) {
        Message.error('请输入有效的整数')
        return false
      }
      if (num <= 0) {
        Message.error('请输入大于0的整数')
        return false
      }
      return true
    },
  },
])
