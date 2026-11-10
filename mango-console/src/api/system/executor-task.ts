import { get, post } from '@/api/http'

export function getExecutorTask(taskId: number | string, silentError = false) {
  return get({
    url: '/system/executor/task',
    data: () => ({ task_id: taskId }),
    silentError,
  })
}

export function getActiveExecutorTasks(
  data: { business_type?: string; business_id?: number | string } = {},
  silentError = false,
) {
  return get({
    url: '/system/executor/task/active',
    data: () => data,
    silentError,
  })
}

export function postCancelExecutorTask(taskId: number | string) {
  return post({
    url: '/system/executor/task/cancel',
    data: () => ({ task_id: taskId }),
  })
}
