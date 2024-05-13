import { reactive } from 'vue'
export interface Item {
  value: string
  label: string
  parameter?: {
    [key: string]: any
  }
  children?: Item[]
}

export const columns = reactive([
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
    title: '元素操作类型',
    dataIndex: 'ope_type',
    width: 150,
  },
  {
    title: '元素操作值',
    dataIndex: 'ope_value',
    ellipsis: true,
    tooltip: true,
  },

  {
    title: '断言类型',
    dataIndex: 'ass_type',
    width: 150,
  },
  {
    title: '断言操作值',
    dataIndex: 'ass_value',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'key_list',
    dataIndex: 'key_list',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'sql',
    dataIndex: 'sql',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'key',
    dataIndex: 'key',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'value',
    dataIndex: 'value',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 130,
  },
])

export const formItems = reactive([
  {
    label: '步骤类型',
    key: 'type',
    value: '',
    type: 'radio',
    required: true,
    placeholder: '请选择对元素的操作类型',
    validator: function () {
      return true
    },
  },
])
