import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '用例名称',
    key: 'case_id',
    dataIndex: 'case_id',
  },
  {
    title: 'cmd命令',
    key: 'command',
    dataIndex: 'command',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 130,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '模块',
    key: 'module',
    value: '',
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
    key: 'case_id',
    value: '',
    placeholder: '请选择用例名称',
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
])
export const formItemsCmd: FormItem[] = reactive([
  {
    label: 'cmd命令',
    key: 'command',
    value: '',
    placeholder: '请输入cmd命令',
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
])
