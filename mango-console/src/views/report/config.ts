import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入测试套ID',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'status',
    label: '测试结果',
    value: ref(''),
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
    width: 220,
  },
  {
    title: '任务名称',
    key: 'tasks',
    dataIndex: 'tasks',
    align: 'left',
  },
  {
    title: '执行环境',
    key: 'test_env',
    dataIndex: 'test_env',
    width: 120,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 170,
  },
  {
    title: '执行人',
    key: 'user',
    dataIndex: 'user',
    width: 139,
  },
  {
    title: '结果',
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
