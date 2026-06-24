import { deleted, get, post, put } from '@/api/http'
import { baseURL } from '@/api/axios.config'
import { useProject } from '@/store/modules/get-project'
import { useUserStoreContext } from '@/store/modules/user'

export function getAiSkill(data: Record<string, unknown>) {
  return get({ url: '/ai/skill', data: () => data })
}

export function postAiSkill(data: Record<string, unknown>) {
  return post({ url: '/ai/skill', data: () => data })
}

export function putAiSkill(data: Record<string, unknown>) {
  return put({ url: '/ai/skill', data: () => data })
}

export function deleteAiSkill(id: number) {
  return deleted({ url: '/ai/skill', data: () => ({ id }) })
}

export function postAiSkillPublish(id: number) {
  return post({ url: '/ai/skill/publish', data: () => ({ id }) })
}

export function postAiSkillDisable(id: number) {
  return post({ url: '/ai/skill/disable', data: () => ({ id }) })
}

export function postAiSkillArchive(id: number) {
  return post({ url: '/ai/skill/archive', data: () => ({ id }) })
}

export function getAiMcpServer(data: Record<string, unknown>) {
  return get({ url: '/ai/mcp/server', data: () => data })
}

export function postAiMcpServer(data: Record<string, unknown>) {
  return post({ url: '/ai/mcp/server', data: () => data })
}

export function putAiMcpServer(data: Record<string, unknown>) {
  return put({ url: '/ai/mcp/server', data: () => data })
}

export function deleteAiMcpServer(id: number) {
  return deleted({ url: '/ai/mcp/server', data: () => ({ id }) })
}

export function postAiMcpServerTest(id: number) {
  return post({ url: '/ai/mcp/server/test', data: () => ({ id }) })
}

export function postAiMcpServerRefreshStatus() {
  return post({ url: '/ai/mcp/server/refresh-status', data: () => ({}) })
}

export function postAiMcpServerBuiltin(data: Record<string, unknown>) {
  return post({ url: '/ai/mcp/server/builtin', data: () => data })
}

export function postAiMcpServerSyncTools(id: number) {
  return post({ url: '/ai/mcp/server/sync-tools', data: () => ({ id }) })
}

export function getAiMcpTool(data: Record<string, unknown>) {
  return get({ url: '/ai/mcp/tool', data: () => data })
}

export function putAiMcpToolStatus(data: Record<string, unknown>) {
  return put({ url: '/ai/mcp/tool/status', data: () => data })
}

export function postAiMcpToolCall(data: Record<string, unknown>) {
  return post({ url: '/ai/mcp/tool/call', data: () => data })
}

export function getAiTask(data: Record<string, unknown>) {
  return get({ url: '/ai/task', data: () => data })
}

export function deleteAiTask(id: number) {
  return deleted({ url: '/ai/task', data: () => ({ id }) })
}

export function getAiTaskDetail(id: number) {
  return get({ url: '/ai/task/detail', data: () => ({ id }) })
}

export function postAiTaskRetry(id: number) {
  return post({ url: '/ai/task/retry', data: () => ({ id }) })
}

export function getAiAgentContext(data: Record<string, unknown>) {
  return get({ url: '/ai/agent/context', data: () => data })
}

export function deleteAiAgentContext(id: number) {
  return deleted({ url: '/ai/agent/context', data: () => ({ id }) })
}

export function postAiFunctionalCaseAgentStart(data: Record<string, unknown>) {
  return post({ url: '/ai/agent/functional-case/start', data: () => data })
}

export function getAiFunctionalCaseAgentStatus(data: Record<string, unknown>) {
  return get({ url: '/ai/agent/functional-case/status', data: () => data })
}

export function getAiFunctionalCaseAgentSteps(data: Record<string, unknown>) {
  return get({ url: '/ai/agent/functional-case/steps', data: () => data })
}

export function postAiFunctionalCaseAgentRetry(data: Record<string, unknown>) {
  return post({ url: '/ai/agent/functional-case/retry', data: () => data })
}

export function postAiApiAutomationAgentStart(data: Record<string, unknown>) {
  return post({ url: '/ai/agent/api-automation/start', data: () => data })
}

export function getAiApiAutomationAgentStatus(data: Record<string, unknown>) {
  return get({ url: '/ai/agent/api-automation/status', data: () => data })
}

export function getAiApiAutomationAgentSteps(data: Record<string, unknown>) {
  return get({ url: '/ai/agent/api-automation/steps', data: () => data })
}

export function postAiApiAutomationAgentRetry(data: Record<string, unknown>) {
  return post({ url: '/ai/agent/api-automation/retry', data: () => data })
}

export function getAiAssistantStatus(data: Record<string, unknown> = {}) {
  return get({ url: '/ai/assistant/status', data: () => data })
}

export function getAiAssistantSession(data: Record<string, unknown>) {
  return get({ url: '/ai/assistant/session', data: () => data })
}

export function getAiAssistantSessionList() {
  return get({ url: '/ai/assistant/session/list', data: () => ({}) })
}

export function postAiAssistantSession(data: Record<string, unknown>) {
  return post({ url: '/ai/assistant/session/create', data: () => data })
}

export function getAiAssistantMessage(data: Record<string, unknown>) {
  return get({ url: '/ai/assistant/message', data: () => data })
}

export function postAiAssistantMessage(data: Record<string, unknown>) {
  return post({ url: '/ai/assistant/message', data: () => data })
}

export async function fetchAiAssistantMessageStream(
  data: Record<string, unknown>,
  onEvent: (event: { event: string; data: any }) => void,
  signal?: AbortSignal
) {
  const userStore = useUserStoreContext()
  const project = useProject()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json;charset=UTF-8',
    'Source-Type': '1',
  }
  if (userStore.token) {
    headers.Authorization = userStore.token
  }
  if (project.scopeType === 'project' && project.scopeId) {
    headers['X-Project-Id'] = project.scopeId.toString()
  }
  if (project.scopeType === 'project_product' && project.scopeId) {
    headers['X-Project-Product-Id'] = project.scopeId.toString()
  }
  const response = await fetch(`${baseURL}/ai/assistant/message/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
    signal,
  })
  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`)
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    chunks.forEach((chunk) => {
      const lines = chunk.split('\n')
      const event = lines.find((line) => line.startsWith('event:'))?.replace('event:', '').trim() || 'message'
      const dataText = lines
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.replace('data:', '').trim())
        .join('\n')
      if (!dataText) return
      onEvent({ event, data: JSON.parse(dataText) })
    })
  }
}

export function postAiAssistantToolConfirm(data: Record<string, unknown>) {
  return post({ url: '/ai/assistant/tool-confirm', data: () => data })
}

export function postAiAssistantClear(data: Record<string, unknown>) {
  return post({ url: '/ai/assistant/clear', data: () => data })
}
