import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'

export const formItemsElementOpe: any = reactive([
  {
    label: '元素操作',
    key: 'ope_key',
    value: ref(''),
    type: 'cascader',
    required: true,
    placeholder: '请选择对元素的操作',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
export const formItemsElementAss: any = reactive([
  {
    label: '断言操作',
    key: 'ope_key',
    value: ref(''),
    type: 'cascader',
    required: true,
    placeholder: '请选择断言类型',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
export const formItemsElement4: any = reactive([
  {
    label: '判断方法',
    key: 'ope_key',
    value: ref(''),
    type: 'cascader',
    required: true,
    placeholder: '请选择判断方法',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
export const formItemsElementSql: any = reactive([
  {
    label: 'key_list',
    key: 'key_list',
    value: ref(''),
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
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请输入sql',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])

export const formItemsElementKey: any = reactive([
  {
    label: 'key',
    key: 'key',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入key',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: 'value',
    key: 'value',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入value',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])

export const formItemsElementCondition: any = reactive([
  {
    label: '判断值',
    key: 'condition_value',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入判断值',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
export const formItemsElementCode: any = reactive([
  {
    label: 'python',
    key: 'func',
    value: ref(''),
    type: 'code',
    required: true,
    placeholder: '请输入python代码',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
