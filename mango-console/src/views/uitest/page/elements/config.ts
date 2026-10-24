import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { isValidInteger } from '@/utils/form'
import { useTable, useTableColumn } from '@/hooks/table'
import { updateTimeColumn, updateUserColumn } from '@/utils/update-user'

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
    title: '分类',
    key: 'category',
    dataIndex: 'category',
    width: 90,
  },
  {
    title: 'AI自愈',
    key: 'ai_heal_status',
    dataIndex: 'ai_heal_status',
    width: 90,
  },
  {
    title: '等待时间',
    key: 'sleep',
    dataIndex: 'sleep',
    width: 100,
  },
  {
    title: '预期事件/输入',
    key: 'expected_event',
    dataIndex: 'expected_event',
    align: 'left',
    width: 260,
  },
  {
    title: '第一组元素',
    key: 'locator_group_1',
    dataIndex: 'locator_group_1',
    align: 'left',
    width: 360,
  },
  {
    title: '第二组元素',
    key: 'locator_group_2',
    dataIndex: 'locator_group_2',
    align: 'left',
    width: 360,
  },
  {
    title: '第三组元素',
    key: 'locator_group_3',
    dataIndex: 'locator_group_3',
    align: 'left',
    width: 360,
  },
  {
    title: '元素描述',
    key: 'prompt',
    dataIndex: 'prompt',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  updateUserColumn(),
  updateTimeColumn(),
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
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
    label: '定位类型-1',
    key: 'exp',
    value: null,
    type: 'select',
    required: true,
    placeholder: '请选择定位类型',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '定位表达式-1',
    key: 'loc',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入定位表达式',
    validator: function () {
      return true
    },
  },
  {
    label: '元素下标-1',
    key: 'sub',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入元素下标，从1开始数',
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
    label: '定位类型-2',
    key: 'exp2',
    value: null,
    type: 'select',
    required: false,
    placeholder: '请选择第二组定位类型',
    validator: function () {
      return true
    },
  },
  {
    label: '定位表达式-2',
    key: 'loc2',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入第二组定位表达式',
    validator: function () {
      return true
    },
  },
  {
    label: '元素下标-2',
    key: 'sub2',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入元素下标，从1开始数',
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
    label: '定位类型-3',
    key: 'exp3',
    value: null,
    type: 'select',
    required: false,
    placeholder: '请选择第三组定位类型',
    validator: function () {
      return true
    },
  },
  {
    label: '定位表达式-3',
    key: 'loc3',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入第三组定位表达式',
    validator: function () {
      return true
    },
  },
  {
    label: '元素下标-3',
    key: 'sub3',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入元素下标，从1开始数',
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
    label: '元素描述',
    key: 'prompt',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入元素位置、周边文字等正向识别线索',
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
