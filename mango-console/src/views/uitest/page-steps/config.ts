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
    placeholder: '请输入步骤ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '步骤名称',
    type: 'input',
    placeholder: '请输入步骤名称',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'project_product',
    label: '产品',
    value: '',
    type: 'select',
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'module',
    label: '模块',
    value: '',
    type: 'select',
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'page',
    label: '所属页面',
    value: '',
    type: 'select',
    placeholder: '请选择所属页面',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'status',
    label: '状态',
    value: '',
    type: 'select',
    placeholder: '请选择步骤状态',
    optionItems: [],
    reset: function () {},
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '项目/产品',
    key: 'project_product',
    value: '',
    placeholder: '请选择项目名称',
    required: true,
    type: 'cascader',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '模块',
    key: 'module',
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
    label: '所属页面',
    key: 'page',
    value: '',
    placeholder: '请选择步骤所属页面',
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
    label: '步骤名称',
    key: 'name',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入页面步骤名称',
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
    width: 180,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    width: 180,
  },
  {
    title: '所属页面',
    key: 'page',
    dataIndex: 'page',
    width: 150,
  },
  {
    title: '步骤名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 200,
  },
  {
    title: '步骤顺序',
    key: 'run_flow',
    dataIndex: 'run_flow',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 70,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 170,
  },
])
