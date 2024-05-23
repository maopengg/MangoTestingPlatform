import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'

export const columns = reactive([
  {
    title: '接口名称',
    dataIndex: 'name',
  },

  {
    title: '请求方法',
    dataIndex: 'method',
  },
  {
    title: '测试结果',
    dataIndex: 'status',
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 220,
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '模块',
    key: 'module',
    value: '',
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
    value: '',
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
