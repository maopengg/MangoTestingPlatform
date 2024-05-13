import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '项目名称',
    key: 'project',
    value: '',
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '客户端类型',
    key: 'type',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请选择客户端类型',
    validator: function () {
      if (this.value === null && this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '产品名称',
    key: 'name',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入产品名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入产品ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '产品名称',
    type: 'input',
    placeholder: '请输入产品名称',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
  },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
  },
  {
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
  },
  {
    title: '产品名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '产品类型',
    key: 'type',
    dataIndex: 'type',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
