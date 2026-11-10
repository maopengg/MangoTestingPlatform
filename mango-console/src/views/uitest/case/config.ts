import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'

export const publicationTabs = [
  { key: 'all', title: '全部' },
  { key: 'published', title: '已发布' },
  { key: 'prepublished', title: '预发布' },
  { key: 'unpublished', title: '未发布' },
]
export function createSearchItems() {
  const items: Omit<FormItem, 'disabled'>[] = [
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入用例ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '用例名称',
    type: 'input',
    placeholder: '请输入用例名称',
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
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'module',
    label: '模块名称',
    value: ref(''),
    type: 'select',
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'level',
    label: '优先级',
    value: ref(''),
    type: 'select',
    placeholder: '请选择优先级',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'scenario_layer',
    label: '测试层级',
    value: ref(''),
    type: 'select',
    placeholder: '请选择测试层级',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'scenario_type',
    label: '验证类型',
    value: ref(''),
    type: 'select',
    placeholder: '请选择验证类型',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'scenario_tags',
    label: '执行场景',
    value: ref([]),
    type: 'select',
    placeholder: '请选择执行场景',
    optionItems: [],
    reset: function () {
      this.value = []
    },
  },
  {
    key: 'case_people',
    label: '用例负责人',
    value: ref([]),
    type: 'select',
    multiple: true,
    searchOperator: 'in',
    placeholder: '请选择用例负责人',
    optionItems: [],
    reset: function () {
      this.value = []
    },
  },
  {
    key: 'status',
    label: '测试结果',
    value: ref([]),
    type: 'select',
    multiple: true,
    searchOperator: 'in',
    placeholder: '请选择测试结果',
    optionItems: [],
    reset: function () {
      this.value = []
    },
  },
  createUpdateUserCondition(),
]
  enableMultiSelectSearch(items)
  return reactive(items)
}
export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' as const },
  {
    title: '用例名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '场景描述',
    key: 'scenario_description',
    dataIndex: 'scenario_description',
    align: 'left',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    width: 90,
  },
  {
    title: '结果',
    key: 'status',
    dataIndex: 'status',
    width: 70,
  },
  {
    title: '测试层级',
    key: 'scenario_layer',
    dataIndex: 'scenario_layer',
    align: 'center',
    width: 120,
  },
  {
    title: '执行场景',
    key: 'scenario_tags',
    dataIndex: 'scenario_tags',
    align: 'left',
    width: 180,
  },
  {
    title: '验证类型',
    key: 'scenario_type',
    dataIndex: 'scenario_type',
    align: 'center',
    width: 100,
  },
  {
    title: '发布状态',
    key: 'publication_status',
    dataIndex: 'publication_status',
    width: 90,
  },
  {
    title: '优先级',
    key: 'level',
    dataIndex: 'level',
    width: 80,
  },
  {
    title: '调用顺序',
    key: 'case_flow',
    dataIndex: 'case_flow',
    align: 'left',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  { ...updateUserColumn(), key: 'update_user' },
  { ...updateTimeColumn(), key: 'update_time' },
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
    width: 240,
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
