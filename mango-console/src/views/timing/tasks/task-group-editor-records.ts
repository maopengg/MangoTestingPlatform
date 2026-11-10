import { readTaskEditorOptions, taskEditorId, taskEditorResponse, type TaskEditorId, type TaskEditorOption } from './task-editor-records'
import { taskListId, taskListObject } from './task-list-records'

export const DEFAULT_TASK_NAME_TEMPLATE = '【${{任务组名称}}】${{模块名称}}'
export interface TaskGroupDraft {
  name: string
  project_product_id: TaskEditorId | null
  module_ids: TaskEditorId[]
  timing_strategies: TaskEditorId[]
  test_envs: number[]
  case_types: number[]
  execution_scenes: string[]
  new_task_report_retention_policy: string
  case_people: TaskEditorId | null
  status: 0 | 1
  is_notice: 0 | 1
  fail_notice: 0 | 1
  notice_group: TaskEditorId | null
}
export interface TaskGroupPayload extends Omit<TaskGroupDraft, 'new_task_report_retention_policy'> {
  id?: TaskEditorId
  new_task_report_retention_policy?: string
  task_name_template: string
}
export interface TaskModuleNode { key: TaskEditorId; title: string; children: TaskModuleNode[]; disableCheckbox: boolean; disabled: boolean }
export interface TaskGroupPreviewRow { action: 'create' | 'update' | 'remove'; module_id: TaskEditorId; module_full_path: string; task_name: string }
export interface TaskGroupPreview { create_count: number; update_count: number; remove_count: number; rows: TaskGroupPreviewRow[] }
function text(value: unknown, fallback = ''): string {
  if (value == null) return fallback
  if (typeof value !== 'string') throw Error('Invalid task group text')
  return value
}
function array(value: unknown): unknown[] {
  if (value == null) return []
  if (!Array.isArray(value)) throw Error('Invalid task group selection')
  return value
}
function ids(value: unknown): TaskEditorId[] { return array(value).filter(value => value !== '' && value != null).map(taskListId) }
function numbers(value: unknown): number[] {
  return array(value).map(value => {
    if (typeof value !== 'string' && typeof value !== 'number') throw Error('Invalid task group enum')
    const number = Number(value)
    if (!Number.isSafeInteger(number) || number < 0 || value === '' || value == null) throw Error('Invalid task group enum')
    return number
  })
}
function flag(value: unknown): 0 | 1 { if (value == null) return 0; if (value === 0 || value === 1) return value; throw Error('Invalid task group flag') }
export function createTaskGroupDraft(): TaskGroupDraft {
  return { name: '', project_product_id: null, module_ids: [], timing_strategies: [], test_envs: [], case_types: [], execution_scenes: [], new_task_report_retention_policy: 'all', case_people: null, status: 0, is_notice: 0, fail_notice: 0, notice_group: null }
}
export function readTaskGroupDraft(value: unknown): TaskGroupDraft {
  const row = taskListObject(value)
  return {
    name: text(row.name), project_product_id: taskEditorId(row.project_product_id), module_ids: ids(row.module_ids), timing_strategies: ids(row.timing_strategies),
    test_envs: numbers(row.test_envs), case_types: numbers(row.case_types), execution_scenes: array(row.execution_scenes).map(value => text(value)),
    new_task_report_retention_policy: text(row.new_task_report_retention_policy, 'all'), case_people: taskEditorId(row.case_people),
    status: flag(row.status), is_notice: flag(row.is_notice), fail_notice: flag(row.fail_notice), notice_group: taskEditorId(row.notice_group),
  }
}
export function taskGroupPayload(value: TaskGroupDraft, id: TaskEditorId | null): TaskGroupPayload {
  const draft = readTaskGroupDraft(value), { new_task_report_retention_policy, ...fields } = draft
  return { ...fields, task_name_template: DEFAULT_TASK_NAME_TEMPLATE,
    ...(id === null ? { new_task_report_retention_policy } : { id }) }
}
export function readTaskGroupEditorDetail(response: unknown, id: TaskEditorId) {
  const row = taskListObject(taskEditorResponse(response))
  if (String(taskListId(row.id)) !== String(id)) throw Error('Task group detail ID mismatch')
  if (!Array.isArray(row.members)) throw Error('Invalid task group members')
  const members = array(row.members)
  const draft = readTaskGroupDraft({
    name: row.name, project_product_id: row.project_product, module_ids: members.map(member => taskListObject(member).module), timing_strategies: row.timing_strategies,
    test_envs: row.test_envs, case_types: row.case_types, execution_scenes: row.execution_scenes, case_people: row.case_people,
    status: row.status, is_notice: row.is_notice, fail_notice: row.fail_notice, notice_group: row.notice_group,
  })
  const selected = (value: unknown): TaskEditorOption[] => array(value).flatMap(entry => {
    if (entry === null || typeof entry !== 'object') return []
    return readTaskEditorOptions([entry])
  })
  return { draft, users: selected(row.case_people == null ? [] : [row.case_people]), timings: selected(row.timing_strategies), notices: selected(row.notice_group == null ? [] : [row.notice_group]) }
}
export function hasStabilitySceneConflict(scenes: string[]) {
  return scenes.includes('stability_monitoring') && scenes.some(scene => ['production_inspection', 'production_regression'].includes(scene))
}
export function groupSceneOptions(options: TaskEditorOption[], envs: number[], scenes: string[]): TaskEditorOption[] {
  const productionScenes = ['stability_monitoring', 'production_inspection', 'production_regression']
  const eligible = options.filter(item => !['unclassified', 'effectiveness_test', 'temporary_validation', 'performance_test'].includes(String(item.key)))
  const production = envs.includes(2), other = envs.some(env => env !== 2)
  return eligible.filter(item => !envs.length || (production && other) || (production ? productionScenes.includes(String(item.key)) : item.key !== 'stability_monitoring')).map(item => ({ ...item,
    disabled: !scenes.includes(String(item.key)) && hasStabilitySceneConflict([...scenes, String(item.key)]),
  }))
}
export function validateTaskGroupDraft(form: TaskGroupDraft): string {
  if (!form.name.trim()) return '请输入任务组名称'
  if (form.project_product_id === null) return '请选择项目/产品'
  if (!form.timing_strategies.length) return '请选择定时策略'
  if (!form.test_envs.length) return '请选择测试环境'
  if (!form.execution_scenes.length) return '请选择执行场景'
  if (hasStabilitySceneConflict(form.execution_scenes)) return '稳定性监测不能与生产巡检、生产回归同时选择，请分开配置任务组'
  if (form.case_people === null) return '请选择负责人'
  if (!form.module_ids.length) return '请至少选择一个拆分模块'
  return ''
}
export function readTaskModuleTree(value: unknown): TaskModuleNode[] {
  if (!Array.isArray(value)) throw Error('Invalid module tree')
  const seen = new Set<string>()
  const parse = (value: unknown): TaskModuleNode[] => array(value).map(entry => {
    const row = taskListObject(entry), key = taskListId(row.key)
    if (seen.has(String(key))) throw Error('Duplicate module node')
    seen.add(String(key))
    return { key, title: text(row.title), disableCheckbox: row.disableCheckbox === true, disabled: row.disabled === true, children: parse(row.children) }
  })
  return parse(value)
}
export function flattenTaskModuleKeys(tree: TaskModuleNode[]): TaskEditorId[] { return tree.flatMap(node => [node.key, ...flattenTaskModuleKeys(node.children)]) }
export function normalizeTaskGroupModules(values: TaskEditorId[], tree: TaskModuleNode[]): TaskEditorId[] {
  const parents = new Map<string, string | null>(), keys = new Map<string, TaskEditorId>()
  const visit = (nodes: TaskModuleNode[], parent: string | null = null) => { for (const node of nodes) { keys.set(String(node.key), node.key); parents.set(String(node.key), parent); visit(node.children, String(node.key)) } }
  visit(tree)
  const selected = new Set(values.map(String))
  return [...selected].filter(id => {
    let parent = parents.get(id) ?? null
    while (parent !== null) { if (selected.has(parent)) return false; parent = parents.get(parent) ?? null }
    return true
  }).map(id => keys.get(id) ?? values.find(value => String(value) === id) ?? id)
}
export function taskGroupSelectableTree(tree: TaskModuleNode[], selected: TaskEditorId[]): TaskModuleNode[] {
  const keys = new Set(selected.map(String))
  const decorate = (nodes: TaskModuleNode[], ancestor = false): TaskModuleNode[] => nodes.map(node => ({ ...node,
    disableCheckbox: node.disableCheckbox || ancestor, children: decorate(node.children, ancestor || keys.has(String(node.key))),
  }))
  return decorate(tree)
}
export function readTaskGroupPreview(value: unknown): TaskGroupPreview {
  const row = taskListObject(value)
  if (!Array.isArray(row.rows)) throw Error('Invalid task group preview rows')
  const count = (value: unknown) => { if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw Error('Invalid task group preview count'); return value }
  return { create_count: count(row.create_count), update_count: count(row.update_count), remove_count: count(row.remove_count), rows: array(row.rows).map(value => {
    const item = taskListObject(value), action = item.action
    if (action !== 'create' && action !== 'update' && action !== 'remove') throw Error('Invalid task group preview action')
    return { action, module_id: taskListId(item.module_id), module_full_path: text(item.module_full_path), task_name: text(item.task_name) }
  }) }
}
