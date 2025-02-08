import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'

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
    width: 220,
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
