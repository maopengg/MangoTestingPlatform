import { deleted, get, post } from '@/api/http'

export function createUiLiveStreamSession(
  executionType: string,
  executionId: string | number,
  options: { resourceId?: string | number; readOnly?: boolean; actuatorUsername?: string } = {}
) {
  return post({
    url: '/ui/live-stream/session',
    data: () => {
      const params: Record<string, any> = {
        execution_type: executionType,
        execution_id: executionId,
        resource_id: options.resourceId,
        read_only: Boolean(options.readOnly),
      }
      if (options.actuatorUsername) params.actuator_username = options.actuatorUsername
      return params
    },
    silentError: true,
  })
}

export function startUiLiveStreamSession(streamId: string, readyTicket: string) {
  return post({
    url: `/ui/live-stream/session/${streamId}/start`,
    data: () => ({ ready_ticket: readyTicket }),
    silentError: true,
  })
}

export function closeUiLiveStreamSession(streamId: string, silentError = false) {
  return deleted({
    url: `/ui/live-stream/session/${streamId}`,
    silentError,
  })
}

export function createUiLiveWorkspace(data: {
  workspace_type: 'element_workspace' | 'page_step_workspace'
  resource_id: string | number
  test_env: string | number
  actuator_username?: string
}) {
  return post({
    url: '/ui/live-stream/workspace',
    data: () => data,
    // 工作区面板会根据 silent 参数决定是否提示，避免请求层和组件层重复报错。
    silentError: true,
  })
}

export function closeUiLiveWorkspace(workspaceId: string, force = false) {
  return deleted({
    url: `/ui/live-stream/workspace/${workspaceId}`,
    data: () => ({ force }),
    silentError: true,
  })
}

export function getUiLiveWorkspaceStatus(workspaceId: string) {
  return get({
    url: `/ui/live-stream/workspace/${workspaceId}`,
    silentError: true,
  })
}
