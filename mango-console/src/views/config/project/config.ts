import { FormItem } from '@/types/components'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'

const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '项目名称',
    key: 'name',
    value: ref(''),
    placeholder: '请输入项目名称',
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
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入项目ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '项目名称',
    type: 'input',
    placeholder: '请输入项目名称',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  createUpdateUserCondition(),
])

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  updateUserColumn(),
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 70,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
