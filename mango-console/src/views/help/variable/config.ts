import type { TableColumnData } from '@arco-design/web-vue'

export const methodMenuSections = [
  { title: '测试数据', value: 'data' },
  { title: '性能测试', value: 'performance' },
  { title: '工具', value: 'tools' },
]

export const exampleParameterValues: Readonly<Record<string, string>> = {
  length: '8', left: '1', right: '100', digits: '3', count: '3',
  days: '0', day: '0', hours: '0', hour: '0', minutes: '0', minute: '0',
  seconds: '0', second: '0', extension: 'txt', file_name: '文件名称',
  time_parts: '12:30:00', demo1: 'demo1', demo2: 'demo2',
}

export const methodColumns: TableColumnData[] = [
  { title: '方法', dataIndex: 'value', width: 220, ellipsis: true, tooltip: true },
  { title: '说明', dataIndex: 'label', width: 300, ellipsis: true, tooltip: true },
  { title: '参数', slotName: 'parameter', width: 220 },
]
export const exampleColumns: TableColumnData[] = [
  { title: '示例', slotName: 'example', width: 260 },
  { title: '操作', slotName: 'actions', width: 120, align: 'center', fixed: 'right' },
]
