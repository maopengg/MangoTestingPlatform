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
    placeholder: '请输入页面ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '页面名称',
    type: 'input',
    placeholder: '请输入页面名称',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'url',
    label: '页面地址',
    type: 'input',
    placeholder: '请输入页面地址',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'module',
    label: '模块',
    value: '',
    type: 'select',
    placeholder: '请先选择模块',
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
    label: '页面名称',
    key: 'name',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入页面名称',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '页面地址',
    key: 'url',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入页面名称',
    validator: function () {
      if (!this.value && this.value !== '0') {
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
    dataIndex: 'module',
    width: 160,
  },
  {
    title: '页面名称',
    key: 'name',
    dataIndex: 'name',
    width: 250,
  },
  {
    title: '页面地址',
    key: 'url',
    dataIndex: 'url',
    align: 'left',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 250,
  },
])
