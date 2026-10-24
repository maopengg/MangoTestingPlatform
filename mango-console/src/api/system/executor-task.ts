import { get, post } from '@/api/http'

export function getExecutorTask(taskId: number | string) {
  return get({
    url: '/system/executor/task',
    data: () => ({ task_id: taskId }),
  })
}

export function getActiveExecutorTasks(
  data: { business_type?: string; business_id?: number | string } = {}
) {
  return get({
    url: '/system/executor/task/active',
    data: () => data,
  })
}

export function postCancelExecutorTask(taskId: number | string) {
  return post({
    url: '/system/executor/task/cancel',
    data: () => ({ task_id: taskId }),
  })
}
