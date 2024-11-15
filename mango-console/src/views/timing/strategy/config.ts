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
    placeholder: '请输入定时策略ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '定时器介绍',
    type: 'input',
    placeholder: '请输入定时器介绍',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '定时器介绍',
    key: 'name',
    value: '',
    placeholder: '请输入定时器的介绍',
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
    label: 'cron',
    key: 'cron',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入正确的cron表达式',
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
    title: '定时器介绍',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  {
    title: '每年某月',
    key: 'cron',
    dataIndex: 'cron',
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
  },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
