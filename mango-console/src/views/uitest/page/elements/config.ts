import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { isValidInteger } from '@/utils/form'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '元素名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 250,
  },
  {
    title: '类型-1',
    key: 'exp',
    dataIndex: 'exp',
    width: 120,
  },
  {
    title: '定位-1',
    key: 'loc',
    dataIndex: 'loc',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '类型-2',
    key: 'exp2',
    dataIndex: 'exp2',
    width: 120,
  },
  {
    title: '定位-2',
    key: 'loc2',
    dataIndex: 'loc2',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '类型-3',
    key: 'exp3',
    dataIndex: 'exp3',
    width: 120,
  },
  {
    title: '定位-3',
    key: 'loc3',
    dataIndex: 'loc3',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '等待时间（秒）',
    key: 'sleep',
    dataIndex: 'sleep',
    width: 130,
  },
  {
    title: '元素下标（1开始）',
    key: 'sub',
    dataIndex: 'sub',
    width: 160,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 190,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '元素名称',
    key: 'name',
    value: ref(''),
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
    label: '类型-1',
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
    label: '定位-1',
    key: 'loc',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入元素表达式',
    validator: function () {
      return true
    },
  },
  {
    label: '类型-2',
    key: 'exp2',
    value: null,
    type: 'select',
    required: false,
    placeholder: '请选择类型-2的元素表达式类型',
    validator: function () {
      return true
    },
  },
  {
    label: '定位-2',
    key: 'loc2',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入定位-2的元素表达式',
    validator: function () {
      return true
    },
  },
  {
    label: '类型-3',
    key: 'exp3',
    value: null,
    type: 'select',
    required: false,
    placeholder: '请选择类型-3的元素表达式类型',
    validator: function () {
      return true
    },
  },
  {
    label: '定位-3',
    key: 'loc3',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入定位-3的元素表达式',
    validator: function () {
      return true
    },
  },
  {
    label: '等待时间',
    key: 'sleep',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入元素等待时间',
    validator: function () {
      if (!this.value && !this.required) {
        return true
      }
      if (!isValidInteger(this.value)) {
        Message.error(`${this.label}请输入正整数！`)
        return false
      }
      return true
    },
  },
  {
    label: '元素下标',
    key: 'sub',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入元素下标',
    validator: function () {
      if (!this.value && !this.required) {
        return true
      }
      if (!isValidInteger(this.value)) {
        Message.error(`${this.label}请输入正整数！`)
        return false
      }
      return true
    },
  },
])

export const opeForm = reactive([
  {
    label: '元素操作',
    key: 'ope_key',
    value: ref(''),
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
    value: ref(''),
    type: 'radio',
    required: true,
    placeholder: '请选择对元素的操作类型',
    validator: function () {
      return true
    },
  },
])
