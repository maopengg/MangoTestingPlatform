import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { useTableColumn } from '@/hooks/table'
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '昵称',
    key: 'nickname',
    dataIndex: 'nickname',
  },
  {
    title: '账号',
    key: 'username',
    dataIndex: 'username',
  },
  {
    title: '来源',
    key: 'source_type',
    dataIndex: 'source_type',
  },
  {
    title: 'IP',
    key: 'ip',
    dataIndex: 'ip',
  },
  {
    title: '登录时间',
    key: 'create_time',
    dataIndex: 'create_time',
  },
])

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'user_id',
    label: '筛选用户',
    value: '',
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
    value: '',
    optionItems: [],
    reset: function () {},
  },
])
