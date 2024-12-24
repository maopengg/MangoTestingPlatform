import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
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
    width: 180,
  },
])

export const customForm = reactive([
  {
    label: 'key',
    key: 'key',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入key',
    validator: function () {
      return true
    },
  },
  {
    label: 'value',
    key: 'value',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入value',
    validator: function () {
      return true
    },
  },
])
export const sqlForm = reactive([
  {
    label: 'key_list',
    key: 'key_list',
    value: '',
    type: 'textarea',
    required: true,
    placeholder: '请输入sql查询结果的key_list',
    validator: function () {
      if (this.value !== '') {
        try {
          this.value = JSON.parse(this.value)
        } catch (e) {
          Message.error('key_list值请输入json数据类型')
          return false
        }
      }
      return true
    },
  },
  {
    label: 'sql语句',
    key: 'sql',
    value: '',
    type: 'textarea',
    required: true,
    placeholder: '请输入sql',
    validator: function () {
      return true
    },
  },
])
export const assForm = reactive([
  {
    label: '断言操作',
    key: 'ope_key',
    value: '',
    type: 'cascader',
    required: true,
    placeholder: '请选择断言类型',
    validator: function () {
      return true
    },
  },
  {
    label: '选择元素',
    key: 'ele_name',
    value: '',
    placeholder: '请选择locating',
    required: false,
    type: 'select',
    validator: function () {
      return true
    },
  },
])
export const eleForm = reactive([
  {
    label: '元素操作',
    key: 'ope_key',
    value: '',
    type: 'cascader',
    required: true,
    placeholder: '请选择对元素的操作',
    validator: function () {
      return true
    },
  },
  {
    label: '选择元素',
    key: 'ele_name',
    value: '',
    placeholder: '请选择locating',
    required: false,
    type: 'select',
    validator: function () {
      return true
    },
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
