import type { TableColumnData } from '@arco-design/web-vue/es/table/interface'

export type DefectColumn = TableColumnData & { title: string; visible?: boolean }
export const DEFECT_COLUMN_STORAGE_KEY = 'mango-functional-defect-columns'
export const defectColumnKey = (column: DefectColumn) => String(column.dataIndex || column.slotName)
export const fixedDefectColumn = (column: DefectColumn) =>
  ['project_product', 'module', 'actions'].includes(defectColumnKey(column))

export const defectColumns: DefectColumn[] = [
  { title: '缺陷编号', dataIndex: 'defect_no', slotName: 'defect_no', width: 180 },
  { title: '缺陷标题', dataIndex: 'title', width: 280, ellipsis: true, tooltip: true },
  { title: '状态', dataIndex: 'status', slotName: 'status', width: 110, align: 'center' },
  { title: '严重程度', dataIndex: 'severity', slotName: 'severity', width: 110, align: 'center' },
  { title: '优先级', dataIndex: 'priority', slotName: 'priority', width: 90, align: 'center' },
  {
    title: '缺陷类型',
    dataIndex: 'defect_type',
    slotName: 'defect_type',
    width: 110,
    align: 'center',
  },
  { title: '来源', dataIndex: 'source_type', slotName: 'source_type', width: 110, align: 'center' },
  { title: '经办人', dataIndex: 'assignee', slotName: 'assignee', width: 110 },
  { title: '报告人', dataIndex: 'reporter', slotName: 'reporter', width: 110 },
  { title: '关联用例', dataIndex: 'relations', slotName: 'relations', width: 100, align: 'center' },
  { title: '更新时间', dataIndex: 'update_time', width: 165 },
  {
    title: '项目/产品',
    dataIndex: 'project_product',
    slotName: 'project_product',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块',
    dataIndex: 'module',
    slotName: 'module',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  { title: '操作', slotName: 'actions', fixed: 'right', width: 140, align: 'center' },
]

export function normalizeDefectColumns(columns: DefectColumn[]): DefectColumn[] {
  return [
    ...columns.filter((column) => !fixedDefectColumn(column)),
    ...['project_product', 'module', 'actions'].flatMap((key) => {
      const column =
        columns.find((item) => defectColumnKey(item) === key) ??
        defectColumns.find((item) => defectColumnKey(item) === key)
      return column ? [{ ...column, visible: true }] : []
    }),
  ]
}
export function restoreDefectColumns(value: unknown): DefectColumn[] {
  const available = new Map(defectColumns.map((column) => [defectColumnKey(column), { ...column }]))
  const restored: DefectColumn[] = []
  for (const entry of Array.isArray(value) ? value : []) {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) continue
    const key: unknown = Reflect.get(entry, 'key')
    if (typeof key !== 'string') continue
    const column = available.get(key)
    if (!column) continue
    available.delete(key)
    restored.push({ ...column, visible: Reflect.get(entry, 'visible') !== false })
  }
  return normalizeDefectColumns([...restored, ...available.values()])
}

export const defectStatusTransitions: Record<number, number[]> = {
  0: [1],
  1: [2],
  2: [3],
  3: [4, 5],
  4: [5],
  5: [2, 3],
}
