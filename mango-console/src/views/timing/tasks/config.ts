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
    placeholder: '请输入任务ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '任务名称',
    type: 'input',
    placeholder: '请输入任务名称',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'test_env',
    label: '测试环境',
    value: '',
    type: 'cascader',
    placeholder: '请选择测试环境',
    optionItems: [],
    reset: function () {},
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '项目/产品',
    key: 'project_product',
    value: '',
    placeholder: '请选择项目名称',
    required: true,
    type: 'cascader',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '任务名称',
    key: 'name',
    value: '',
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
    key: 'timing_strategy',
    value: '',
    placeholder: '请输入选择定时器策略',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '自动化类型',
    key: 'type',
    value: 0,
    placeholder: '请选择自动化类型',
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
    label: '测试环境',
    key: 'test_env',
    value: '',
    placeholder: '请选择执行环境',
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
    label: '负责人',
    key: 'case_people',
    value: '',
    placeholder: '请选择定时任务负责人',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== '0') {
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
  },
  {
    title: '任务名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  {
    title: '任务类型',
    key: 'type',
    dataIndex: 'type',
  },
  {
    title: '定时器介绍',
    key: 'timing_strategy',
    dataIndex: 'timing_strategy',
    align: 'left',
  },
  {
    title: '测试环境',
    key: 'test_env',
    dataIndex: 'test_env',
    align: 'left',
  },
  {
    title: '负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    align: 'left',
  },
  {
    title: '任务状态',
    key: 'status',
    dataIndex: 'status',
  },
  {
    title: '通知',
    key: 'is_notice',
    dataIndex: 'is_notice',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
