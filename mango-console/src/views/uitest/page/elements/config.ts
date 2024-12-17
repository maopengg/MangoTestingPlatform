import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
export const columns = reactive([
  {
    title: '元素名称',
    dataIndex: 'name',
    width: 250,
  },
  {
    title: '表达式类型',
    dataIndex: 'exp',
    width: 110,
  },
  {
    title: '定位表达式',
    dataIndex: 'loc',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '是否在iframe中',
    dataIndex: 'is_iframe',
    width: 140,
  },
  {
    title: '等待时间（秒）',
    dataIndex: 'sleep',
    width: 130,
  },
  {
    title: '元素下标（1开始）',
    dataIndex: 'sub',
    width: 160,
  },

  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 200,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '元素名称',
    key: 'name',
    value: '',
    placeholder: '请输入元素名称',
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
    label: '表达式类型',
    key: 'exp',
    value: null,
    type: 'select',
    required: true,
    placeholder: '请选择元素表达式类型',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '元素表达式',
    key: 'loc',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入元素表达式',
    validator: function () {
      return true
    },
  },
  {
    label: '等待时间',
    key: 'sleep',
    value: '',
    type: 'input',
    required: false,
    placeholder: '请输入元素等待时间',
  },
  {
    label: '元素下标',
    key: 'sub',
    value: '',
    type: 'input',
    required: false,
    placeholder: '请输入元素下标',
  },
])

export const assForm = reactive([
  {
    label: '断言类型',
    key: 'ope_key',
    value: '',
    type: 'cascader',
    required: true,
    placeholder: '请选择断言类型',
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
])

export const formItems1 = reactive([
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
