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
    key: 'test_obj',
    label: '测试环境',
    value: ref(''),
    type: 'select',
    placeholder: '请选择测试环境',
    optionItems: [],
    reset: function () {},
  },
])
export const formItems: FormItem[] = reactive([
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
    key: 'test_obj',
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
    label: '执行器',
    key: 'case_executor',
    value: ref(''),
    placeholder: '请选择定执行器',
    required: true,
    type: 'select',
    validator: function () {
      if (this.value.length === 0) {
        Message.error(this.placeholder || '')
        return false
      }
      this.value = this.value.filter(
        (item: any) => item !== null && item !== undefined && item !== ''
      )
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
    key: 'test_obj',
    dataIndex: 'test_obj',
    align: 'left',
  },
  {
    title: '负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    align: 'left',
  },
  {
    title: '执行器',
    key: 'case_executor',
    dataIndex: 'case_executor',
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
