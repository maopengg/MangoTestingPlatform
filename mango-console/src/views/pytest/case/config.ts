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
    placeholder: '请输入ID',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '用例名称',
    type: 'input',
    placeholder: '请输入页面名称',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'file_path',
    label: '文件路径',
    type: 'input',
    placeholder: '请输入页面地址',
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
    key: 'file_status',
    label: '文件状态',
    value: ref(''),
    type: 'select',
    placeholder: '请选择文件状态',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'status',
    label: '测试结果',
    value: ref(''),
    type: 'select',
    placeholder: '请选择文件状态',
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
    label: '绑定状态',
    key: 'file_status',
    value: ref(''),
    placeholder: '请选择绑定状态',
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
    validator: function () {
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
    validator: function () {
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
    required: true,
    placeholder: '请选择场景标签',
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
    title: '文件路径',
    key: 'file_path',
    dataIndex: 'file_path',
    align: 'left',
    width: 360,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '文件状态',
    key: 'file_status',
    dataIndex: 'file_status',
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
