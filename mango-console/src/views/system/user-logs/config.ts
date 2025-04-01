import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '昵称',
    key: 'user',
    dataIndex: 'user',
    align: 'left',
  },

  {
    title: 'IP',
    key: 'ip',
    dataIndex: 'ip',
    align: 'left',
  },
  {
    title: '来源',
    key: 'source_type',
    dataIndex: 'source_type',
    width: 70,
  },
  {
    title: '登录时间',
    key: 'create_time',
    dataIndex: 'create_time',
  },
])

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'user',
    label: '筛选用户',
    value: ref(''),
    type: 'select',
    placeholder: '请选择用户',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'source_type',
    label: '筛选来源',
    type: 'select',
    placeholder: '请选择来源',
    value: ref(''),
    optionItems: [],
    reset: function () {},
  },
])
