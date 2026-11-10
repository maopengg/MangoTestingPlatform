import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { updateTimeColumn, updateUserColumn } from '@/utils/update-user'

type TaskField = Omit<FormItem, 'key'> & { key: string }
export const binaryStatusOptions = [{ label: '已开启', value: 1 }, { label: '已关闭', value: 0 }]
export const noticeStatusOptions = [{ label: '通知', value: 1 }, { label: '不通知', value: 0 }]
export const taskGroupSyncStatusOptions = [{ label: '已同步', value: 'synced' }, { label: '待同步', value: 'pending' }, { label: '同步失败', value: 'failed' }]
export function taskStatusOptions(notice = false) {
  return [
    { key: 1, title: notice ? '通知' : '已开启', value: 1, label: notice ? '通知' : '已开启' },
    { key: 0, title: notice ? '不通知' : '已关闭', value: 0, label: notice ? '不通知' : '已关闭' },
  ]
}
export function taskGroupFilterOption(id: string | number, name: string) {
  return { key: id, title: name, value: id, label: name }
}
export function createConditionItems(): TaskField[] {
const fields: Array<Omit<TaskField, 'disabled'>> = [
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入任务ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '任务名称',
    type: 'input',
    placeholder: '请输入任务名称',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'task_group',
    label: '任务组',
    value: ref(''),
    type: 'select',
    placeholder: '请选择任务组',
    optionItems: [],
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
    key: 'test_envs',
    label: '测试环境',
    value: ref([]),
    type: 'select',
    multiple: true,
    searchOperator: 'in',
    placeholder: '请选择测试环境',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'case_types',
    label: '用例类型',
    value: ref([]),
    type: 'select',
    multiple: true,
    searchOperator: 'in',
    placeholder: '请选择用例类型',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'execution_scenes',
    label: '执行场景',
    value: ref([]),
    type: 'select',
    multiple: true,
    searchOperator: 'in',
    placeholder: '请选择执行场景',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'execution_scope',
    label: '执行范围',
    value: ref(''),
    type: 'select',
    placeholder: '请选择执行范围',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'status',
    label: '是否开启',
    value: ref(''),
    type: 'select',
    placeholder: '请选择是否开启',
    optionItems: taskStatusOptions(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'is_notice',
    label: '是否通知',
    value: ref(''),
    type: 'select',
    placeholder: '请选择是否通知',
    optionItems: taskStatusOptions(true),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'case_people',
    label: '负责人',
    value: ref([]),
    type: 'select',
    multiple: true,
    searchOperator: 'in',
    placeholder: '请选择负责人',
    optionItems: [],
    reset: function () {},
  },
]
const items = reactive(fields)
enableMultiSelectSearch(items)
for (const item of items) item.reset = function () { this.value = this.multiple ? [] : '' }
return items
}
export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '任务名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 270,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '最近执行质量',
    key: 'recent_results',
    dataIndex: 'recent_results',
    align: 'left',
    width: 240,
  },
  {
    title: '定时器',
    key: 'timing_strategies',
    dataIndex: 'timing_strategies',
    align: 'left',
    width: 120,
    ellipsis: true,
  },
  {
    title: '测试环境',
    key: 'test_envs',
    dataIndex: 'test_envs',
    align: 'left',
    width: 80,
  },
  {
    title: '用例类型',
    key: 'case_types',
    dataIndex: 'case_types',
    width: 180,
  },
  {
    title: '执行场景',
    key: 'execution_scenes',
    dataIndex: 'execution_scenes',
    width: 180,
  },
  {
    title: '执行范围',
    key: 'execution_scope',
    dataIndex: 'execution_scope',
    width: 80,
  },
  {
    title: '负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    width: 90,
  },
  {
    title: '是否开启',
    key: 'status',
    dataIndex: 'status',
    width: 90,
  },
  {
    title: '是否通知',
    key: 'is_notice',
    dataIndex: 'is_notice',
    width: 90,
  },
  {
    title: '失败通知',
    key: 'fail_notice',
    dataIndex: 'fail_notice',
    width: 90,
  },
  {
    title: '通知组',
    key: 'notice_group',
    dataIndex: 'notice_group',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  { ...updateUserColumn(), key: 'update_user' },
  { ...updateTimeColumn(), key: 'update_time' },
  {
    title: '来源任务组',
    key: 'task_group_name',
    dataIndex: 'task_group_name',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '报告保留策略',
    key: 'report_retention_policy',
    dataIndex: 'report_retention_policy',
    width: 180,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    align: 'left',
    width: 230,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
