export interface ExecutionHistoryItem {
  id: number | string
  title: string
  statusText?: string
  statusColor?: string
  time?: string
  actor?: string
  latest?: boolean
  sourceText?: string
  sourceColor?: string
}
