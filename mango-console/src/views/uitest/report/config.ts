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
    placeholder: '请输入测试套ID',
    value: '',
    reset: function () {
      this.value = ''
    },
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
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 200,
  },
  {
    title: '执行环境',
    key: 'test_object',
    dataIndex: 'test_object',
    width: 200,
  },
  {
    title: '执行时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 200,
  },
  {
    title: '执行人',
    key: 'user',
    dataIndex: 'user',
  },
  {
    title: '执行状态',
    key: 'run_status',
    dataIndex: 'run_status',
  },
  {
    title: '结果',
    key: 'status',
    dataIndex: 'status',
  },
  {
    title: '失败原因',
    key: 'error_message',
    dataIndex: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 400,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
