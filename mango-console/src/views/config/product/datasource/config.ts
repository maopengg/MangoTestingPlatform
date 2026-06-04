import { useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { Message } from '@arco-design/web-vue'
import { reactive, ref } from 'vue'

const table = useTable()

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 180,
  },
  {
    title: '数据库类型',
    key: 'db_type',
    dataIndex: 'db_type',
    width: 130,
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 100,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 170,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入逻辑数据源名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '编码',
    key: 'code',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入唯一编码，例如 contract_mysql',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '数据库类型',
    key: 'db_type',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择数据库类型',
    validator: function () {
      if (this.value === null || this.value === undefined || this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '描述',
    key: 'description',
    value: ref(''),
    type: 'textarea',
    required: false,
    placeholder: '请输入描述',
  },
])
