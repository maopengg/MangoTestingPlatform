import { useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { Message } from '@arco-design/web-vue'
import { reactive, ref } from 'vue'

const table = useTable()

export function sortLogicalDatasources<T extends { db_type?: number | string | null }>(rows: T[]): T[] {
  const typeOrder = [0, 1, 2, 3, 4, 10, 20]
  const rank = (value: T['db_type']) => {
    const index = value == null ? -1 : typeOrder.indexOf(Number(value))
    return index < 0 ? typeOrder.length : index
  }
  return [...rows].sort((left, right) => rank(left.db_type) - rank(right.db_type))
}

export const discoveryColumns = [
  { title: '表名 / 索引', dataIndex: 'name', width: 260, ellipsis: true, tooltip: true },
  { title: '说明', dataIndex: 'comment', ellipsis: true, tooltip: true },
  {
    title: '操作',
    slotName: 'actions',
    width: 160,
    fixed: 'right' as const,
    align: 'center' as const,
  },
]
export const schemaColumns = [
  { title: '字段', dataIndex: 'name', width: 220, ellipsis: true, tooltip: true },
  { title: '类型', dataIndex: 'db_type', width: 160 },
  { title: '说明', dataIndex: 'label', width: 200, ellipsis: true, tooltip: true },
  { title: '可空', slotName: 'nullable', width: 70, align: 'center' as const },
  { title: '主键', slotName: 'primary_key', width: 70, align: 'center' as const },
  { title: '自增', slotName: 'autoincrement', width: 70, align: 'center' as const },
]

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 180,
  },
  {
    title: '分类',
    key: 'source_category',
    dataIndex: 'source_category',
    width: 130,
  },
  {
    title: '数据库类型',
    key: 'db_type',
    dataIndex: 'db_type',
    width: 130,
  },
  {
    title: '描述',
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
    width: 100,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入逻辑数据库名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '数据库分类',
    key: 'source_category',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择数据库分类',
  },
  {
    label: '数据库类型',
    key: 'db_type',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择数据库类型',
    validator: function () {
      if (this.value === null || this.value === undefined || this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '描述',
    key: 'description',
    value: ref(''),
    type: 'textarea',
    required: false,
    placeholder: '请输入描述',
  },
])
