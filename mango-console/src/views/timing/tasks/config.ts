import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { updateTimeColumn, updateUserColumn } from '@/utils/update-user'

const table = useTable()
export const conditionItems: Array<FormItem> = reactive([
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
    optionItems: [
      { key: 1, title: '已开启' },
      { key: 0, title: '已关闭' },
    ],
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
    optionItems: [
      { key: 1, title: '通知' },
      { key: 0, title: '不通知' },
    ],
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
])
enableMultiSelectSearch(conditionItems)
export const formItems: FormItem[] = reactive([
  {
    label: '报告保留策略', key: 'report_retention_policy', value: ref('all'), type: 'select',
    placeholder: '请选择报告保留策略', required: true,
    reset: function () { this.value = 'all' },
  },
  {
    label: '项目/产品',
    key: 'project_product',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'cascader',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '模块名称',
    key: 'module',
    value: ref(''),
    placeholder: '请选择模块名称，留空则为全部模块名称',
    required: false,
    type: 'select',
    validator: function () {
      return true
    },
  },
  {
    label: '任务名称',
    key: 'name',
    value: ref(''),
    placeholder: '请输入任务名称',
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
  {
    label: '定时策略',
    key: 'timing_strategies',
    value: ref([]),
    placeholder: '请输入选择定时器策略',
    required: true,
    type: 'select',
    multiple: true,
    validator: function () {
      if (!Array.isArray(this.value) || this.value.length === 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
    reset: function () {
      this.value = []
    },
  },
  {
    label: '测试环境',
    key: 'test_envs',
    value: ref([]),
    placeholder: '请选择执行环境',
    required: true,
    type: 'select',
    multiple: true,
    validator: function () {
      if (!Array.isArray(this.value) || this.value.length === 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
    reset: function () {
      this.value = []
    },
  },
  {
    label: '用例类型',
    key: 'case_types',
    value: ref([]),
    placeholder: '留空表示全部类型',
    required: false,
    type: 'select',
    multiple: true,
    validator: function () {
      return true
    },
    reset: function () {
      this.value = []
    },
  },
  {
    label: '执行场景',
    key: 'execution_scenes',
    value: ref([]),
    placeholder: '请选择执行场景',
    required: true,
    type: 'select',
    multiple: true,
    validator: function () {
      if (!Array.isArray(this.value) || this.value.length === 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
    reset: function () {
      this.value = []
    },
  },
  {
    label: '执行范围',
    key: 'execution_scope',
    value: ref(''),
    placeholder: '请选择执行范围',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value || this.value === 'unclassified') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '负责人',
    key: 'case_people',
    value: ref(''),
    placeholder: '请选择定时任务负责人',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: 'API 并发',
    key: 'api_concurrency_limit',
    value: ref(null),
    placeholder: '留空则使用平台最大执行容量',
    required: false,
    type: 'number',
    validator: function () {
      return true
    },
    reset: function () {
      this.value = null
    },
  },
  {
    label: '通知组',
    key: 'notice_group',
    value: ref(''),
    placeholder: '请选择通知组',
    required: false,
    type: 'select',
    validator: function () {
      return true
    },
  },
])

export const tableColumns = useTableColumn([
  table.indexColumn,
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
  updateUserColumn(),
  updateTimeColumn(),
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
