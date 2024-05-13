import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '项目名称',
    key: 'name',
    value: '',
    placeholder: '请输入项目名称',
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
])
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入项目ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '项目名称',
    type: 'input',
    placeholder: '请输入项目名称',
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
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '状态',
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
