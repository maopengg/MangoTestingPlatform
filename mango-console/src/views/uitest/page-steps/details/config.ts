import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'

export const columns: any = reactive([
  {
    title: '元素名称',
    dataIndex: 'ele_name',
    width: 150,
  },
  {
    title: '步骤类型',
    dataIndex: 'type',
    width: 90,
  },
  {
    title: '操作类型/key/sql_key_list',
    dataIndex: 'ope_key',
  },
  {
    title: '操作值/value/sql',
    dataIndex: 'ope_value',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 200,
  },
])

export const formItems: any = reactive([
  {
    label: '步骤类型',
    key: 'type',
    value: ref(''),
    type: 'radio',
    required: true,
    placeholder: '请选择对元素的操作类型',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
