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
    key: 'project_product',
    label: '项目/产品',
    value: ref(''),
    type: 'cascader',
    placeholder: '请选择项目/产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'module',
    label: '模块名称',
    value: ref(''),
    type: 'select',
    placeholder: '请选择模块名称',
    optionItems: [],
    reset: function () {},
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
  {
    key: 'tasks_id',
    label: '定时任务',
    value: ref(''),
    type: 'select',
    placeholder: '请选择定时任务',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'user',
    label: '执行人',
    value: ref(''),
    type: 'select',
    placeholder: '请选择执行人',
    optionItems: [],
    reset: function () {},
  },
])
export const tableColumns = useTableColumn([
  {
    ...table.indexColumn,
    width: 150,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块名称',
    key: 'module',
    dataIndex: 'module',
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '任务名称',
    key: 'tasks',
    dataIndex: 'tasks',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试环境',
    key: 'test_env',
    dataIndex: 'test_env',
    width: 100,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '执行人',
    key: 'user',
    dataIndex: 'user',
    width: 110,
  },
  {
    title: '测试结果',
    key: 'status',
    dataIndex: 'status',
    width: 90,
  },
  {
    title: '通知结果',
    key: 'is_notice',
    dataIndex: 'is_notice',
    width: 90,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 170,
  },
])
