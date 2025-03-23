import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '角色名称',
    key: 'name',
    value: ref(''),
    placeholder: '请输入角色名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '角色描述',
    key: 'description',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请输入角色描述',
    validator: function () {
      if (!this.value && this.value !== 0) {
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
    title: '角色名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '角色描述',
    key: 'description',
    dataIndex: 'description',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
