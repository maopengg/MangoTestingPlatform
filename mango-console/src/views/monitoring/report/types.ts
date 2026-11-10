import type { FormItem } from '@/types/components'

interface ReportSearchBase extends Omit<FormItem, 'key' | 'type' | 'value' | 'reset'> {
  reset(this: ReportSearchItem): void
}

export type ReportSearchItem = ReportSearchBase & (
  { key: 'task_name'; type: 'input'; value: string } |
  { key: 'status'; type: 'select'; value: Array<number | string> }
)
