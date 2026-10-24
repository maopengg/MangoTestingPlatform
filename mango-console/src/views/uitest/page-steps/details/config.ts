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
  {
    label: '选择元素',
    key: 'ele_name',
    value: ref(''),
    type: 'element-cascader',
    required: true,
    placeholder: '请选择一个元素',
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
    label: '期望值',
    key: 'condition_value',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入期望值',
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
export const formItemsForceWait: any = reactive([
  {
    label: '等待时长',
    key: 'seconds-ope_value',
    field: 'seconds',
    value: ref(1),
    type: 'input-number',
    required: true,
    min: 0,
    max: 3600,
    precision: 1,
    suffix: '秒',
    placeholder: '请输入等待秒数',
    validator: function () {
      const seconds = Number(this.value)
      if (!Number.isFinite(seconds) || seconds < 0 || seconds > 3600) {
        Message.error('等待时长必须在 0 到 3600 秒之间')
        return false
      }
      return true
    },
  },
])
