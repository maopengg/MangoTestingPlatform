import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
export const columns = reactive([
  {
    title: '元素名称',
    dataIndex: 'name',
  },
  {
    title: '表达式类型',
    dataIndex: 'exp',
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
  },
  {
    title: '等待时间（秒）',
    dataIndex: 'sleep',
  },
  {
    title: '元素下标（1开始）',
    dataIndex: 'sub',
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
    required: false,
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
export const formItems1: FormItem[] = reactive([
  {
    label: '步骤类型',
    key: 'type',
    value: 0,
    type: 'radio',
    required: true,
    placeholder: '请选择对元素的操作类型',
    validator: function () {
      return true
    },
  },

  {
    label: '元素操作',
    key: 'ope_type',
    value: null,
    type: 'cascader',
    required: false,
    placeholder: '请选择对元素的操作',
    validator: function () {
      return true
    },
  },
  {
    label: '元素操作值',
    key: 'ope_value',
    value: '',
    type: 'textarea',
    required: false,
    placeholder: '请输入对元素的操作内容',
    validator: function () {
      if (this.value !== '') {
        try {
          this.value = JSON.parse(this.value)
        } catch (e) {
          Message.error('元素操作值请输入json数据类型')
          return false
        }
      }
      return true
    },
  },
  {
    label: '断言类型',
    key: 'ass_type',
    value: null,
    type: 'cascader',
    required: false,
    placeholder: '请选择断言类型',
  },
  {
    label: '断言值',
    key: 'ass_value',
    value: '',
    type: 'textarea',
    required: false,
    placeholder: '请输入断言内容',
    validator: function () {
      if (this.value !== '') {
        try {
          this.value = JSON.parse(this.value)
        } catch (e) {
          Message.error('断言值请输入json数据类型')
          return false
        }
      }
      return true
    },
  },
])
