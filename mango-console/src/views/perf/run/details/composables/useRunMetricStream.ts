
import { reportLoadError, runLoadRequest } from '@/utils/load-error'
import { ref } from 'vue'
import { getPerfRunMetrics } from '@/api/perf'
import type { PollingContext } from '@/hooks/use-page-polling'
import { readRunMetricPage } from '../records'
import { mergeRunMetricPoints } from '../metrics'
import type { RunMetricPage, RunMetricWindow } from '../types'

interface MetricStreamOptions {
  runId: () => string | null
  onPoints: () => void
  onDrained: (page: RunMetricPage, context: PollingContext) => Promise<void>
}

export function useRunMetricStream(options: MetricStreamOptions) {
  const points = ref<RunMetricWindow[]>([])
  const metricsLoading = ref(false)
  const metricsError = ref('')
  let cursor = ''
  let generation = 0
  let disposed = false
  let pending: { isCurrent: () => boolean; promise: Promise<void>; drained: boolean } | null = null

  function invalidate() {
    generation++
    pending = null
    metricsLoading.value = false
  }
  function reset() {
    invalidate()
    cursor = ''
    points.value = []
    metricsError.value = ''
  }

  function load(silent = false, context?: PollingContext): Promise<void> {
    const targetId = options.runId()
    if (disposed || !targetId || (context && !context.isCurrent())) return Promise.resolve()
    if (pending?.isCurrent()) {
      if (!silent && !pending.drained) metricsLoading.value = true
      return pending.promise
    }
    const version = generation
    const isCurrent = () => !disposed && generation === version && options.runId() === targetId && (!context || context.isCurrent())
    const job = { isCurrent, promise: Promise.resolve(), drained: false }
    pending = job
    if (!silent) metricsLoading.value = true
    job.promise = (async () => {
      try {
        let page: RunMetricPage
        do {
          const requestedCursor = cursor
          const response = await runLoadRequest(silent, () => getPerfRunMetrics(targetId, {
            cursor: requestedCursor, max_points: 1000, scope_type: 'global',
          }))
          if (!isCurrent()) return
          page = readRunMetricPage(response, targetId)
          // A non-advancing continuation must not spin forever or commit its batch.
          if (page.has_more && (!page.cursor || page.cursor === requestedCursor)) {
            throw new Error('Invalid metric continuation')
          }
          const merged = mergeRunMetricPoints(points.value, page.points)
          points.value = merged
          cursor = page.cursor || requestedCursor
          metricsError.value = ''
          if (page.points.length) options.onPoints()
        } while (page.has_more && isCurrent())
        job.drained = true
        if (pending === job) metricsLoading.value = false
        if (isCurrent()) await options.onDrained(page, { isCurrent })
      } catch (error) {
        if (isCurrent() && !job.drained) (reportLoadError(error, "加载失败，请重试", silent), metricsError.value = '指标更新失败，请重试')
        throw error
      } finally {
        if (pending === job) {
          pending = null
          metricsLoading.value = false
        }
      }
    })()
    return job.promise
  }

  function dispose() {
    disposed = true
    reset()
  }

  return { points, metricsLoading, metricsError, load, invalidate, reset, dispose, readCursor: () => cursor }
}
