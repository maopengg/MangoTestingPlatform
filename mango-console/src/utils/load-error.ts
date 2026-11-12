import { Message } from '@arco-design/web-vue'

const handled = new WeakSet<object>()
const messages = new Map<string, number>()
let silentRequest = false

/** 只包住请求创建这一同步阶段；HTTP 层立即把标记复制到独立请求配置中。 */
export function runLoadRequest<T>(silent: boolean, request: () => T): T {
  const previous = silentRequest
  silentRequest = silent
  try { return request() } finally { silentRequest = previous }
}

export function isSilentLoadRequest() { return silentRequest }

export function markErrorReported(error: unknown) {
  if (error && typeof error === 'object') handled.add(error)
}

export function isErrorReported(error: unknown) {
  return Boolean(error && typeof error === 'object' && handled.has(error))
}

/** 请求层和加载边界复用同一个标记，解析异常也通过公共消息显示。 */
export function reportLoadError(error?: unknown, message = '加载失败，请重试', silent = false) {
  if (isErrorReported(error)) {
    messages.set(message, Date.now())
    return
  }
  markErrorReported(error)
  if (silent) return
  const now = Date.now()
  if (now - (messages.get(message) ?? -Infinity) < 3000) return
  messages.set(message, now)
  Message.error(message)
  if (messages.size > 100) {
    for (const [key, time] of messages) if (now - time > 3000) messages.delete(key)
  }
}

/** 保留调用方失败状态，同时复用请求层对同一次异常的提示去重。 */
export function requestFailureMessage<T>(error: unknown, message: T, fallback?: string): T {
  const feedback = typeof message === 'string' ? message : fallback
  if (feedback?.trim()) reportLoadError(error, feedback)
  return message
}
