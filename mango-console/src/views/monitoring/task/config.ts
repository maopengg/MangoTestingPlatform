import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

// 搜索条件
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'name',
    label: '任务名称',
    type: 'input',
    placeholder: '请输入任务名称',
    value: ref(''),
    reset() {
      this.value = ''
    },
  },
  {
    key: 'status',
    label: '状态',
    type: 'select',
    placeholder: '请选择状态',
    value: ref(''),
    reset() {
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
])

// 表单项
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
    type: 'input',
    required: true,
    placeholder: '请输入任务名称',
    validator() {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '任务描述',
    key: 'description',
    value: ref(''),
    type: 'input',
    placeholder: '请输入任务描述',
    required: false,
    validator() {
      return true
    },
  },
  {
    label: '是否通知',
    key: 'is_notice',
    value: ref(0),
    type: 'switch',
    placeholder: '请选择是否发送通知',
    required: false,
    validator() {
      if (this.value === null) {
        this.value = 0
      }
      return true
    },
  },
  {
    label: '通知组',
    key: 'notice_group',
    value: ref(''),
    type: 'select',
    placeholder: '请选择通知组',
    required: false,
    validator() {
      return true
    },
  },
  {
    label: '脚本内容',
    key: 'script_content',
    value: ref(''),
    type: 'textarea',
    placeholder: '请粘贴 python 脚本内容',
    required: true,
    validator() {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])

// 表格列
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
    width: 300,
  },
  {
    title: '任务描述',
    key: 'description',
    dataIndex: 'description',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    align: 'center',
    width: 90,
  },
  {
    title: '是否通知',
    key: 'is_notice',
    dataIndex: 'is_notice',
    align: 'center',
    width: 100,
  },
  {
    title: '通知组',
    key: 'notice_group',
    dataIndex: 'notice_group',
    align: 'left',
    width: 150,
  },
  {
    title: 'PID',
    key: 'pid',
    dataIndex: 'pid',
    align: 'center',
    width: 100,
  },
  {
    title: '开始时间',
    key: 'started_at',
    dataIndex: 'started_at',
    align: 'center',
    width: 180,
  },
  {
    title: '结束时间',
    key: 'stopped_at',
    dataIndex: 'stopped_at',
    align: 'center',
    width: 180,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 190,
  },
])
