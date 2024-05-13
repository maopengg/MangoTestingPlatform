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
    label: '定时器类型',
    key: 'trigger_type',
    value: 'cron',
    placeholder: 'cron',
    required: true,
    type: 'input',
  },
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
    label: '每年某月',
    key: 'month',
    value: '',
    type: 'input',
    required: false,
    placeholder: '月份请输入1-12之间的数字',
    validator: function () {
      if (this.value) {
        // 判断value是否为1-12之间的数字
        const value = parseInt(this.value)
        if (isNaN(value) || value < 1 || value > 12) {
          Message.error(this.placeholder || '')
          return false
        }
      }
      return true
    },
  },
  {
    label: '每月某天',
    key: 'day',
    value: '',
    type: 'input',
    required: false,
    placeholder: '天数请输入1-31之间的数字',
    validator: function () {
      if (this.value) {
        // 判断value是否为1-12之间的数字
        const value = parseInt(this.value)
        if (isNaN(value) || value < 1 || value > 31) {
          Message.error(this.placeholder || '')
          return false
        }
      }
      return true
    },
  },
  {
    label: '每周几',
    key: 'day_of_week',
    value: '',
    type: 'input',
    required: false,
    placeholder: '请输1-7的数字代表周几',
    validator: function () {
      if (this.value) {
        // 判断value是否为1-12之间的数字
        const value = parseInt(this.value)
        if (isNaN(value) || value < 1 || value > 7) {
          Message.error(this.placeholder || '')
          return false
        }
      }
      return true
    },
  },
  {
    label: '每天某小时',
    key: 'hour',
    value: '',
    type: 'input',
    required: false,
    placeholder: '小时请输入1-24之间的数字',
    validator: function () {
      if (this.value) {
        // 判断value是否为1-12之间的数字
        const value = parseInt(this.value)
        if (isNaN(value) || value < 1 || value > 23) {
          Message.error(this.placeholder || '')
          return false
        }
      }
      return true
    },
  },
  {
    label: '某分钟',
    key: 'minute',
    value: '',
    type: 'input',
    required: false,
    placeholder: '分钟请输入1-60之间的数字',
    validator: function () {
      if (this.value) {
        // 判断value是否为1-12之间的数字
        const value = parseInt(this.value)
        if (isNaN(value) || value < 1 || value > 60) {
          Message.error(this.placeholder || '')
          return false
        }
      }
      return true
    },
  },
])

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '定时器类型',
    key: 'trigger_type',
    dataIndex: 'trigger_type',
  },
  {
    title: '定时器介绍',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  {
    title: '每年某月',
    key: 'month',
    dataIndex: 'month',
  },
  {
    title: '每月某天',
    key: 'day',
    dataIndex: 'day',
  },
  {
    title: '每周几',
    key: 'day_of_week',
    dataIndex: 'day_of_week',
  },
  {
    title: '每天某小时',
    key: 'hour',
    dataIndex: 'hour',
  },
  {
    title: '每小时的某分钟',
    key: 'minute',
    dataIndex: 'minute',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
