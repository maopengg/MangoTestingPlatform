import { reactive } from 'vue'
import { FormItem } from '@/types/components'
import { Message } from '@arco-design/web-vue'

export const columns = reactive([
  {
    title: '步骤名称',
    dataIndex: 'page_step_name',
  },
  {
    title: '测试结果',
    dataIndex: 'status',
  },
  {
    title: '错误提示',
    dataIndex: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },

  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 230,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '选择模块',
    key: 'module',
    value: '',
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
    value: '',
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
    value: '',
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
])
