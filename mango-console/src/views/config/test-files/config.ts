import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目名称',
    key: 'project_name',
    dataIndex: 'project_name',
  },
  {
    title: '文件名称',
    key: 'file_name',
    dataIndex: 'file_name',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
