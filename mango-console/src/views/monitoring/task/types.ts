export type ProductSelection = number | string | Array<number | string> | null

export interface TaskSearchItem {
  key: 'name' | 'project_product'
  label: string
  type: 'input' | 'cascader'
  value: ProductSelection
  placeholder: string
  reset(): void
}

export interface TaskEditorDraft {
  project_product: ProductSelection
  name: string
  description: string | null
  test_env: number | '' | null
  is_notice: 0 | 1
  notice_group: number | '' | null
  script_content: string
}

export interface NoticeOption { value: number; label: string }

export interface TaskEditorHandle {
  openCreate(product?: ProductSelection): void
  openEdit(record: unknown): void
  close(): void
}

export interface MonitoringTaskSnapshot {
  id: number
  name: string
  description: string | null
  project_product: { id: number; name: string; project: { id: number; name: string } | null }
  notice_group: { id: number; name: string } | null
  test_env: number | null
  test_env_display: string | null
  is_notice: 0 | 1
  script_content: string
  status: number
  status_display: string
  pid: number | null
  started_at: string | null
  stopped_at: string | null
  create_time: string
  update_time: string
  update_user: { id: number; name: string } | null
}

export interface CodeEditorHandle { scrollToBottom(): void }
export interface TaskWorkspaceVersion { selection: number; version: number }
export interface TaskDemoHandle { open(): void; close(): void }
