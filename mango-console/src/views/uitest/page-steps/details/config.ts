import type { StepField } from '@/components/business/ui-page-step'
import { Message } from '@arco-design/web-vue'

export function isEmptyStepField(value: unknown) {
  return value == null || value === '' || (Array.isArray(value) && value.length === 0)
}

export function createNodeFields() {
const formItemsElementOpe: StepField[] = [
  {
    label: '元素操作',
    key: 'ope_key',
    value: '',
    type: 'cascader',
    required: true,
    placeholder: '请选择对元素的操作',
    validator: function () {
      if (isEmptyStepField(this.value)) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '选择元素',
    key: 'ele_name',
    value: '',
    type: 'element-cascader',
    required: true,
    placeholder: '请选择一个元素',
    validator: function () {
      if (isEmptyStepField(this.value)) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
]
const formItemsElementAss: StepField[] = [
  {
    label: '断言操作',
    key: 'ope_key',
    value: '',
    type: 'cascader',
    required: true,
    placeholder: '请选择断言类型',
    validator: function () {
      if (isEmptyStepField(this.value)) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
]
const formItemsElement4: StepField[] = [
  {
    label: '判断方法',
    key: 'ope_key',
    value: '',
    type: 'cascader',
    required: true,
    placeholder: '请选择判断方法',
    validator: function () {
      if (isEmptyStepField(this.value)) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
]
const formItemsElementKey: StepField[] = [
  {
    label: 'key',
    key: 'key',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入key',
    validator: function () {
      if (isEmptyStepField(this.value)) {
        Message.error(this.placeholder || '')
        return false
      }
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
      if (isEmptyStepField(this.value)) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
]

const formItemsElementCondition: StepField[] = [
  {
    label: '期望值',
    key: 'condition_value',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入期望值',
    validator: function () {
      if (isEmptyStepField(this.value)) {
        Message.error(this.placeholder || '')
        return false
      }

      return true
    },
  },
]
const formItemsElementCode: StepField[] = [
  {
    label: 'python',
    key: 'func',
    value: '',
    type: 'code',
    required: true,
    placeholder: '请输入python代码',
    validator: function () {
      if (isEmptyStepField(this.value)) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
]
const formItemsForceWait: StepField[] = [
  {
    label: '等待时长',
    key: 'seconds-ope_value',
    field: 'seconds',
    value: 1,
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
]

return { formItemsElementOpe, formItemsElementAss, formItemsElement4, formItemsElementKey, formItemsElementCondition, formItemsElementCode, formItemsForceWait }
}
