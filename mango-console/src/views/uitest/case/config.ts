import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入用例ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '用例名称',
    type: 'input',
    placeholder: '请输入用例名称',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'module_name',
    label: '模块',
    value: '',
    type: 'select',
    placeholder: '请先选择项目',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'case_people',
    label: '用例负责人',
    value: '',
    type: 'select',
    placeholder: '请选择用例负责人',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'status',
    label: '测试结果',
    value: '',
    type: 'select',
    placeholder: '请选择测试结果',
    optionItems: [],
    reset: function () {},
  },
])
export const formItems = reactive([
  {
    label: '项目',
    key: 'project',
    value: '',
    placeholder: '请选择项目',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '模块',
    key: 'module_name',
    value: '',
    placeholder: '请选择测试模块',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '用例名称',
    key: 'name',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入用例名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '用例级别',
    key: 'level',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请设置用例级别',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '用例负责人',
    key: 'case_people',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请设置用例负责人',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 130,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'modul',
    width: 160,
  },
  {
    title: '用例名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 200,
  },
  {
    title: '步骤顺序',
    key: 'case_flow',
    dataIndex: 'case_flow',
    align: 'left',
  },
  {
    title: '级别',
    key: 'level',
    dataIndex: 'level',
  },
  {
    title: '负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    width: 80,
  },

  {
    title: '结果',
    key: 'status',
    dataIndex: 'status',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
