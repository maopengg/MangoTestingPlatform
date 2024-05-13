import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '驱动类型',
    key: 'type',
    value: '',
    type: 'radio',
    required: true,
    placeholder: '请选择驱动类型',
    validator: function () {
      return true
    },
  },
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '驱动类型',
    key: 'type',
    dataIndex: 'type',
  },
  {
    title: '浏览器',
    key: 'browser_type',
    dataIndex: 'browser_type',
  },
  {
    title: '浏览器端口',
    key: 'browser_port',
    dataIndex: 'browser_port',
  },
  {
    title: '浏览器地址',
    key: 'browser_path',
    dataIndex: 'browser_path',
    align: 'left',
  },
  {
    title: '安卓设备号',
    key: 'equipment',
    dataIndex: 'equipment',
    align: 'left',
  },
  {
    title: '所属用户',
    key: 'user_id',
    dataIndex: 'user_id',
  },
  {
    title: '是否开启无头',
    key: 'is_headless',
    dataIndex: 'is_headless',
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
