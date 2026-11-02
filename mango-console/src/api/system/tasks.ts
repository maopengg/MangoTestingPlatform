import { deleted, get, post, put } from '@/api/http'

export interface DiagnosticMarkdownResult {
  target_type: 'scheduled_task' | 'test_report'
  target_id: number
  file_path: string
  file_name: string | null
  download_url: string | null
  update_time: string
  content: string
}

export function getSystemTasks(data: object) {
  return get({
    url: 'system/tasks',
    data: () => {
      return data
    },
  })
}

export function getSystemIndexPendingTasks(data: { page: number; pageSize: number }) {
  return get({
    url: 'system/index/pending/tasks',
    data: () => data,
  })
}

export function postSystemTasks(data: object) {
  return post({
    url: 'system/tasks',
    data: () => {
      return data
    },
  })
}

export function putSystemTasks(data: object) {
  return put({ url: 'system/tasks',
    data: () => {
      return data
    },
  })
}

export function deleteSystemTasks(id: number | string[] | number[]) {
  return deleted({
    url: 'system/tasks',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getSystemTriggerTiming(id: number) {
  return get({
    url: 'system/tasks/trigger/timing',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getSystemTaskExecutionOptions() {
  return get({
    url: 'system/tasks/execution/options',
    data: () => ({}),
  })
}

export function getSystemTaskModuleConfig(projectProductId: number) {
  return get({
    url: 'system/tasks/module-config',
    data: () => ({ project_product_id: projectProductId }),
  })
}

export function putSystemTaskModuleConfig(projectProductId: number, rows: Record<string, any>[]) {
  return put({
    url: 'system/tasks/module-config',
    data: () => ({ project_product_id: projectProductId, rows }),
  })
}

export function postSystemTaskGroups(projectProductId: number, rows: Record<string, any>[]) {
  return post({
    url: 'system/tasks/task-group',
    data: () => ({ project_product_id: projectProductId, rows }),
  })
}

export function putSystemTaskGroup(taskId: number, row: Record<string, any>) {
  return put({
    url: 'system/tasks/task-group',
    data: () => ({ task_id: taskId, row }),
  })
}

export function deleteSystemTaskGroup(taskId: number) {
  return deleted({
    url: 'system/tasks/task-group',
    data: () => ({ task_id: taskId }),
  })
}

export function getScheduledTaskGroups(data: Record<string, any>) {
  return get({
    url: 'system/tasks/groups',
    data: () => data,
  })
}

export function getScheduledTaskGroupOptions(projectProductId?: number | null) {
  return get({
    url: 'system/tasks/groups/options',
    data: () => ({
      ...(projectProductId ? { project_product_id: projectProductId } : {}),
    }),
  })
}

export function getScheduledTaskGroupDetail(id: number) {
  return get({
    url: 'system/tasks/groups/detail',
    data: () => ({ id }),
  })
}

export function triggerScheduledTaskGroup(id: number) {
  return get({
    url: 'system/tasks/groups/trigger',
    data: () => ({ id }),
  })
}

export function getLatestTaskGroupExecutions(id: number) {
  return get({ url: 'system/tasks/groups/executions/latest', data: () => ({ id }) })
}

export function resendTaskGroupNotice(id: number, executionId: number) {
  return post({
    url: 'system/tasks/groups/notice/resend',
    data: () => ({ id, execution_id: executionId }),
  })
}

export function previewScheduledTaskGroup(data: Record<string, any>) {
  return post({
    url: 'system/tasks/groups/preview',
    data: () => data,
  })
}

export function createScheduledTaskGroup(data: Record<string, any>) {
  return post({
    url: 'system/tasks/groups',
    data: () => data,
  })
}

export function updateScheduledTaskGroup(data: Record<string, any>) {
  return put({ url: 'system/tasks/groups',
    data: () => data,
  })
}

export function deleteScheduledTaskGroup(id: number) {
  return deleted({
    url: 'system/tasks/groups',
    data: () => ({ id }),
  })
}

export function updateScheduledTaskGroupMemberStatus(
  groupId: number,
  memberId: number,
  enabled: boolean
) {
  return put({
    url: 'system/tasks/groups/member/status',
    data: () => ({ group_id: groupId, member_id: memberId, enabled }),
  })
}

export function getSystemTaskDiagnosticMarkdown(id: number | string) {
  return get<DiagnosticMarkdownResult>({
    url: 'system/tasks/diagnostic/markdown',
    data: () => ({ id }),
  })
}

export interface TaskRecentResult {
  test_suite_id: number | null
  report_retained?: boolean
  status: number
  status_key: 'success' | 'fail' | 'warning' | 'proceed' | 'stay_begin' | 'stopped'
  status_text: string
  test_env: number
  test_env_text: string
  create_time: string | null
  update_time: string | null
  duration_ms: number
  total: number
  success: number
  fail: number
  warning: number
  proceed: number
  stay_begin: number
  stopped: number
  pass_rate: number | null
  excluded_count?: number
}

export type ExecutionQualityResult = Omit<TaskRecentResult, 'test_suite_id'>
export type TaskGroupRecentResult = ExecutionQualityResult & { group_execution_id: number }

export interface ScheduledTaskRuleCase {
  case_id: number
  case_name: string
  case_type: number
  project_product_id: number
  module_id: number | null
  module_full_path: string
  scenario_tags: string[]
  publication_status: string
}

export interface ScheduledTaskRuleCaseResult {
  items: ScheduledTaskRuleCase[]
  count: number
  page: number
  pageSize: number
  summary: Record<string, any>
}

export function getSystemTaskSelectionCases(data: Record<string, any>) {
  return get<ScheduledTaskRuleCaseResult>({
    url: 'system/tasks/selection/cases',
    data: () => data,
  })
}

export const RECENT_EXECUTION_LIMIT = 7

export function getSystemTaskRecentResults(taskIds: Array<number | string>, limit = RECENT_EXECUTION_LIMIT) {
  return get<Record<string, TaskRecentResult[]>>({
    url: 'system/tasks/recent/results',
    data: () => ({
      task_ids: taskIds.join(','),
      limit,
    }),
  })
}

export function postSystemTriggerManual(
  taskId: number,
  apiConcurrencyLimit?: number | null,
  testEnvs?: number[]
) {
  return post({
    url: 'system/tasks/trigger/manual',
    data: () => {
      return {
        task_id: taskId,
        api_concurrency_limit: apiConcurrencyLimit,
        test_envs: testEnvs,
      }
    },
  })
}

export function getSystemTasksName(
  projectProductId?: number | string | null,
  moduleId?: number | string | null,
  caseType?: number | string | null,
  executionScope?: string | null
) {
  return get({
    url: 'system/tasks/name',
    data: () => {
      return {
        ...(projectProductId ? { project_product_id: projectProductId } : {}),
        ...(moduleId ? { module_id: moduleId } : {}),
        ...(caseType !== null && caseType !== undefined && caseType !== ''
          ? { case_type: caseType }
          : {}),
        ...(executionScope ? { execution_scope: executionScope } : {}),
      }
    },
  })
}

export function getSystemTaskFireRecord(data: object) {
  return get({
    url: 'system/tasks/fire-record',
    data: () => {
      return data
    },
  })
}

export function getSystemTaskSystemJobs(data: object = {}) {
  return get({
    url: 'system/tasks/system/jobs',
    data: () => {
      return data
    },
  })
}

export function postSystemTaskSystemJobTrigger(jobKey: string) {
  return post({
    url: 'system/tasks/system/jobs/trigger',
    data: () => {
      return {
        job_key: jobKey,
      }
    },
  })
}
