import { useTable, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'
import { reactive } from 'vue'
import type { FormItem } from '@/types/components'
import { createIdSearchValue } from '@/utils/id-search'
import { enableMultiSelectSearch } from '@/utils/search-condition'

const table = useTable()

export const conditionItems: FormItem[] = reactive([
  { key: 'id', label: 'ID', type: 'input', placeholder: '请输入ID', value: createIdSearchValue() },
  { key: 'name', label: '授权名称', type: 'input', placeholder: '请输入授权名称', value: '' },
  { key: 'test_env', label: '被测环境', type: 'select', placeholder: '请选择被测环境', value: [] },
  { key: 'auth_type', label: '授权方式', type: 'select', placeholder: '请选择授权方式', value: [] },
  { key: 'refresh_mode', label: '刷新方式', type: 'select', placeholder: '请选择刷新方式', value: [] },
  { key: 'last_refresh_status', label: '刷新状态', type: 'select', placeholder: '请选择刷新状态', value: [] },
  createUpdateUserCondition(),
])
enableMultiSelectSearch(conditionItems)

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '授权名称',
    key: 'name',
    dataIndex: 'name',
    width: 240,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  { title: '被测环境', key: 'test_env', dataIndex: 'test_env', width: 100 },
  { title: '授权方式', key: 'auth_type', dataIndex: 'auth_type', width: 110 },
  {
    title: '授权配置',
    key: 'auth_config',
    dataIndex: 'auth_config',
    width: 260,
    align: 'left',
  },
  { title: '刷新方式', key: 'refresh_mode', dataIndex: 'refresh_mode', width: 110 },
  {
    title: '刷新策略',
    key: 'refresh_strategy',
    dataIndex: 'refresh_strategy',
    width: 190,
    align: 'left',
  },
  { title: '有效期(分钟)', key: 'token_ttl', dataIndex: 'token_ttl', width: 120 },
  { title: '过期时间', key: 'expires_at', dataIndex: 'expires_at', width: 180 },
  {
    title: '刷新状态',
    key: 'last_refresh_status',
    dataIndex: 'last_refresh_status',
    width: 110,
  },
  {
    title: '最近刷新时间',
    key: 'last_refresh_time',
    dataIndex: 'last_refresh_time',
    width: 180,
  },
  { title: '默认开启', key: 'status', dataIndex: 'status', width: 90 },
  updateUserColumn(110),
  { title: '更新时间', key: 'update_time', dataIndex: 'update_time', width: 180 },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 140,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  { title: '操作', key: 'actions', dataIndex: 'actions', width: 160, fixed: 'right' },
])

export const tableScrollX = tableColumns.reduce(
  (total: number, column: { width?: number }) => total + (column.width || 0),
  0,
)
