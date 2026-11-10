import type { TableColumnData } from '@arco-design/web-vue'
import { runStatusTitle, verdictTitle } from '../types'

export const statusOptions = Object.entries(runStatusTitle).map(([value, label]) => ({ value, label }))
export const verdictOptions = Object.entries(verdictTitle).map(([value, label]) => ({ value, label }))
export const runColumns: Array<TableColumnData & { key: string }> = [
  { title: '运行ID', key: 'index', dataIndex: 'index', width: 100, align: 'center' },
  { title: '运行名称', key: 'name', dataIndex: 'name', width: 240, ellipsis: true, tooltip: true },
  { title: '产品名称', key: 'project_product', dataIndex: 'project_product', width: 140, ellipsis: true, tooltip: true },
  { title: '模块', key: 'module', dataIndex: 'module_full_path', width: 220, ellipsis: true, tooltip: true },
  { title: '状态', key: 'status', dataIndex: 'status', width: 120, align: 'center' },
  { title: '结论', key: 'verdict', dataIndex: 'verdict', width: 110, align: 'center' },
  { title: '引擎', key: 'engine', dataIndex: 'engine', width: 90, align: 'center' },
  { title: '目标并发', key: 'peak_target_users', dataIndex: 'peak_target_users', width: 110, align: 'center' },
  { title: '节点', key: 'nodes', dataIndex: 'actual_node_count', width: 100, align: 'center' },
  { title: '创建时间', key: 'create_time', dataIndex: 'create_time', width: 180, align: 'center' },
  { title: '操作', key: 'actions', dataIndex: 'actions', width: 120, align: 'center', fixed: 'right' },
]
export const runScrollX = 1530
