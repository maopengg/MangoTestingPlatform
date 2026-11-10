import type { MonitoringTaskConfiguration, MonitoringTaskCreate, MonitoringTaskUpdate } from '@/api/monitoring/task'
import type { NoticeOption, ProductSelection, TaskEditorDraft } from './types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid task configuration')
  return value as Record<string, unknown>
}
function identifier(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid task identifier')
  return value
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid task text')
  return value
}

export function productId(value: ProductSelection): number | null {
  const leaf = Array.isArray(value) ? value[value.length - 1] : value
  if (leaf === null || leaf === undefined || (typeof leaf === 'string' && leaf.trim() === '')) return null
  const parsed = Number(leaf)
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : null
}

export function createTaskEditorDraft(product: ProductSelection = null): TaskEditorDraft {
  return { project_product: productId(product), name: '', description: '', test_env: null, is_notice: 0, notice_group: null, script_content: '' }
}

export function readTaskEditorRecord(value: unknown) {
  const row = object(value)
  const product = typeof row.project_product === 'number' ? row.project_product : object(row.project_product).id
  const group = row.notice_group == null ? null : typeof row.notice_group === 'number'
    ? { value: identifier(row.notice_group), label: String(row.notice_group) }
    : { value: identifier(object(row.notice_group).id), label: text(object(row.notice_group).name) }
  if (row.is_notice !== 0 && row.is_notice !== 1) throw new Error('Invalid notification switch')
  const draft: TaskEditorDraft = {
    project_product: identifier(product), name: text(row.name),
    description: row.description === null ? null : text(row.description),
    test_env: row.test_env === null ? null : identifier(row.test_env),
    is_notice: row.is_notice, notice_group: group?.value ?? null, script_content: '',
  }
  return { id: identifier(row.id), draft, group }
}

export function readNoticeOptions(response: unknown): NoticeOption[] {
  const row = object(response)
  if (row.code !== 200 || !Array.isArray(row.data)) throw new Error('Invalid notice options')
  return row.data.map(value => { const item = object(value); return { value: identifier(item.value), label: text(item.label) } })
}

export function taskEditorPayload(draft: TaskEditorDraft, id: number | null): MonitoringTaskCreate | MonitoringTaskUpdate {
  const product = productId(draft.project_product)
  if (product === null) throw new Error('请选择项目名称')
  if (!draft.name) throw new Error('请输入任务名称')
  if (id === null && !draft.script_content) throw new Error('请粘贴 python 脚本内容')
  const fields: MonitoringTaskConfiguration = {
    project_product: product, name: draft.name, description: draft.description,
    test_env: draft.test_env === '' ? null : draft.test_env,
    is_notice: draft.is_notice, notice_group: draft.notice_group === '' ? null : draft.notice_group,
  }
  return id === null ? { ...fields, script_content: draft.script_content } : { ...fields, id }
}
