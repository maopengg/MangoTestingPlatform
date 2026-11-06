export const PAGE_POLL_INTERVAL = 5000

export interface PollingContext {
  isCurrent: () => boolean
}

export function isPendingExecution(record: { status?: unknown } | null | undefined) {
  return [2, 3].includes(Number(record?.status))
}

export function createPagePolling(
  refresh: (context: PollingContext) => unknown | Promise<unknown>,
  available: () => boolean,
  clock = {
    setTimeout: (callback: () => void, delay: number) => setTimeout(callback, delay),
    clearTimeout: (timer: ReturnType<typeof setTimeout>) => clearTimeout(timer),
  },
) {
  let enabled = false, disposed = false, running = false, generation = 0
  let timer: ReturnType<typeof setTimeout> | undefined
  let resumePending = false
  function clear() {
    if (timer !== undefined) clock.clearTimeout(timer)
    timer = undefined
  }
  function schedule(delay = PAGE_POLL_INTERVAL) {
    if (disposed || !enabled || !available() || running || timer !== undefined) return
    timer = clock.setTimeout(() => { timer = undefined; void run() }, delay)
  }
  async function run() {
    if (disposed || !enabled || !available() || running) return
    running = true
    const current = generation
    try {
      await refresh({ isCurrent: () => !disposed && available() && current === generation })
    } catch {
      // 后台同步失败保留已有数据，并在下一周期重试。
    } finally {
      running = false
      const delay = resumePending ? 0 : PAGE_POLL_INTERVAL
      resumePending = false
      schedule(delay)
    }
  }
  return {
    start() { enabled = true; schedule() },
    stop() { enabled = false; clear() },
    pause() { generation++; clear() },
    resume() { if (running) resumePending = true; else schedule(0) },
    dispose() { disposed = true; generation++; enabled = false; clear() },
    isRunning: () => running,
  }
}
