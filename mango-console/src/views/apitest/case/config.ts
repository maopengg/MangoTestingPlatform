import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入用例ID',
    value: ref(''),
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
    placeholder: '请选择模块',
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
    label: '场景层级',
    value: ref(''),
    type: 'select',
    placeholder: '请选择场景层级',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'scenario_type',
    label: '场景类型',
    value: ref(''),
    type: 'select',
    placeholder: '请选择场景类型',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'scenario_tags',
    label: '场景标签',
    value: ref([]),
    type: 'select',
    placeholder: '请选择场景标签',
    optionItems: [],
    reset: function () {
      this.value = []
    },
  },
  {
    key: 'case_people',
    label: '用例负责人',
    value: ref(''),
    type: 'select',
    placeholder: '请选择用例负责人',
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
])
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
    label: '模块名称',
    key: 'module',
    value: ref(''),
    placeholder: '请选择测试模块',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
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
    type: 'input',
    required: true,
    placeholder: '请输入用例名称',
    validator: function () {
      if (!this.value) {
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
    label: '场景层级',
    key: 'scenario_layer',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择场景层级',
    reset: function () {
      this.value = 0
    },
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
    label: '场景类型',
    key: 'scenario_type',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择场景类型',
    reset: function () {
      this.value = 0
    },
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
    label: '场景标签',
    key: 'scenario_tags',
    value: ref([]),
    type: 'select',
    placeholder: '请选择场景标签',
    reset: function () {
      this.value = []
    },
  },
  {
    label: '场景描述',
    key: 'scenario_description',
    value: ref(''),
    type: 'textarea',
    placeholder: 'Given 前置条件\nWhen 用户执行某个行为\nThen 应得到某个结果',
    reset: function () {
      this.value = ''
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
    title: '场景层级',
    key: 'scenario_layer',
    dataIndex: 'scenario_layer',
    align: 'left',
    width: 120,
  },
  {
    title: '场景标签',
    key: 'scenario_tags',
    dataIndex: 'scenario_tags',
    align: 'left',
    width: 110,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '场景类型',
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
    title: '负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    width: 90,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 70,
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
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 170,
  },
])
