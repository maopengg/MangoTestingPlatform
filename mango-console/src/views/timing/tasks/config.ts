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
    placeholder: '请输入任务ID',
    value: ref(''),
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
    key: 'test_env',
    label: '测试环境',
    value: ref(''),
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
    key: 'timing_strategy',
    value: ref(''),
    placeholder: '请输入选择定时器策略',
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
    value: ref(''),
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
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 200,
  },
  {
    title: '任务名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '定时器',
    key: 'timing_strategy',
    dataIndex: 'timing_strategy',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试环境',
    key: 'test_env',
    dataIndex: 'test_env',
    align: 'left',
    width: 100,
  },
  {
    title: '负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    width: 120,
  },
  {
    title: '通知组',
    key: 'notice_group',
    dataIndex: 'notice_group',
    align: 'left',
    ellipsis: true,
    tooltip: true,
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
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
