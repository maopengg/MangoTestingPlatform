const NOTIFICATION_DEDUPLICATION_WINDOW_MS = 60_000
const notifiedTaskIds = new Map<string, number>()

export function claimExecutorTaskNotification(taskId: unknown): boolean {
  const normalizedTaskId = String(taskId || '').trim()
  if (!normalizedTaskId) return true

  const now = Date.now()
  notifiedTaskIds.forEach((notifiedAt, savedTaskId) => {
    if (now - notifiedAt > NOTIFICATION_DEDUPLICATION_WINDOW_MS) {
      notifiedTaskIds.delete(savedTaskId)
    }
  })
  if (notifiedTaskIds.has(normalizedTaskId)) return false

  notifiedTaskIds.set(normalizedTaskId, now)
  return true
}
