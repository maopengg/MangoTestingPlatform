import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'

const table = useTable()
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入ID',
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
    key: 'file_path',
    label: '文件路径',
    type: 'input',
    placeholder: '请输入文件路径',
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
    label: '所属模块',
    value: ref(''),
    type: 'select',
    placeholder: '请选择模块名称',
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
    key: 'file_status',
    label: '绑定状态',
    value: ref(''),
    type: 'select',
    placeholder: '请选择绑定状态',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'source_status',
    label: '源码状态',
    value: ref(''),
    type: 'select',
    placeholder: '请选择源码状态',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'asset_status',
    label: '资产状态',
    value: ref(''),
    type: 'select',
    placeholder: '请选择资产状态',
    optionItems: [],
    reset: function () {},
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
    reset: function () {},
  },
  {
    key: 'publication_status', label: '发布状态', value: ref([]), type: 'select',
    multiple: true, searchOperator: 'in', placeholder: '请选择发布状态', optionItems: [],
    reset: function () { this.value = [] },
  },
  {
    key: 'case_people', label: '用例负责人', value: ref([]), type: 'select',
    multiple: true, searchOperator: 'in', placeholder: '请选择负责人', optionItems: [],
    reset: function () { this.value = [] },
  },
  createUpdateUserCondition(),
])
enableMultiSelectSearch(conditionItems)
export const formItems: FormItem[] = reactive([
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
    label: '所属模块',
    key: 'module',
    value: ref(''),
    placeholder: '请选择模块名称',
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
    label: '用例名称',
    key: 'name',
    value: ref(''),
    placeholder: '请输入名称',
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
    label: '资产状态',
    key: 'asset_status',
    value: ref(0),
    placeholder: '请选择资产状态',
    required: true,
    type: 'select',
    validator: function () {
      if (this.value === '' || this.value === null || this.value === undefined) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '优先级',
    key: 'level',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请设置优先级',
    validator: function () {
      // @ts-ignore
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '测试层级',
    key: 'scenario_layer',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择测试层级',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '验证类型',
    key: 'scenario_type',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择验证类型',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '执行场景',
    key: 'scenario_tags',
    value: ref([]),
    type: 'select',
    required: true,
    placeholder: '请选择执行场景',
    validator: function () {
      if (!this.value?.length) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '场景描述',
    key: 'scenario_description',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入场景描述',
    validator: function () {
      return true
    },
  },
  {
    label: '用例负责人',
    key: 'case_people',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请设置用例负责人',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '用例名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 300,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '场景描述',
    key: 'scenario_description',
    dataIndex: 'scenario_description',
    align: 'left',
    width: 260,
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
    title: '资产状态',
    key: 'asset_status',
    dataIndex: 'asset_status',
    width: 90,
  },
  {
    title: '测试层级',
    key: 'scenario_layer',
    dataIndex: 'scenario_layer',
    align: 'left',
    width: 120,
  },
  {
    title: '执行场景',
    key: 'scenario_tags',
    dataIndex: 'scenario_tags',
    align: 'left',
    width: 110,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '验证类型',
    key: 'scenario_type',
    dataIndex: 'scenario_type',
    align: 'left',
    width: 100,
  },
  {
    title: '优先级',
    key: 'level',
    dataIndex: 'level',
    width: 80,
  },
  {
    title: '文件路径',
    key: 'file_path',
    dataIndex: 'file_path',
    align: 'left',
    width: 360,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '绑定状态',
    key: 'file_status',
    dataIndex: 'file_status',
    width: 90,
  },
  {
    title: '源码状态',
    key: 'source_status',
    dataIndex: 'source_status',
    width: 90,
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
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  updateUserColumn(),
  updateTimeColumn(),
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
