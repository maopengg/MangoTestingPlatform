import type { App, ComponentPublicInstance } from 'vue'
import { baseURL } from '@/api/axios.config'
import { isApiBusinessError } from '@/api/errors'
import { useUserStoreContext } from '@/store/modules/user'

const REPORT_INTERVAL = 60_000
const MAX_RECENT_ERRORS = 100
const recentErrors = new Map<string, number>()
let reporting = false

interface NormalizedError {
  exceptionType: string
  message: string
  traceback?: string
}

function currentPage() {
  if (typeof window === 'undefined') return 'unknown-page'
  const hashPath = window.location.hash.split('?')[0]
  return `${window.location.pathname}${hashPath}`.slice(0, 180) || '/'
}

function normalizeError(error: unknown): NormalizedError {
  if (error instanceof Error) {
    return {
      exceptionType: (error.name || 'Error').slice(0, 128),
      message: (error.message || error.name || 'Unknown frontend error').slice(0, 500),
      traceback: error.stack?.slice(0, 50_000),
    }
  }
  const message = typeof error === 'string' ? error : String(error || 'Unknown frontend error')
  return {
    exceptionType: 'FrontendError',
    message: message.slice(0, 500),
    traceback: message.slice(0, 50_000),
  }
}

function shouldReport(key: string) {
  const now = Date.now()
  const lastReportedAt = recentErrors.get(key) || 0
  if (now - lastReportedAt < REPORT_INTERVAL) return false
  if (recentErrors.size >= MAX_RECENT_ERRORS) recentErrors.clear()
  recentErrors.set(key, now)
  return true
}

function reportUrl() {
  const apiBase = String(baseURL || '/api').replace(/\/$/, '')
  return `${apiBase}/system/runtime/frontend-errors`
}

export async function reportFrontendError(error: unknown, operation: string) {
  if (reporting || typeof window === 'undefined' || isApiBusinessError(error)) return
  const userStore = useUserStoreContext()
  if (!userStore.token) return
  const normalized = normalizeError(error)
  const normalizedOperation = `${operation || 'frontend'} @ ${currentPage()}`.slice(0, 255)
  const fingerprint = `${normalizedOperation}|${normalized.exceptionType}|${normalized.message}`
  if (!shouldReport(fingerprint)) return

  reporting = true
  try {
    await fetch(reportUrl(), {
      method: 'POST',
      headers: {
        Authorization: userStore.token,
        'Content-Type': 'application/json',
        'Source-Type': '1',
      },
      body: JSON.stringify({
        operation: normalizedOperation,
        exception_type: normalized.exceptionType,
        message: normalized.message,
        traceback: normalized.traceback,
      }),
      keepalive: true,
    })
  } catch {
    // 异常上报失败不能再次触发异常上报，也不能影响用户当前操作。
  } finally {
    reporting = false
  }
}

function resourceError(event: Event) {
  const target = event.target as (HTMLElement & { src?: string; href?: string }) | null
  const resourceUrl = target?.src || target?.href
  if (!resourceUrl || resourceUrl.startsWith('chrome-extension:')) return
  let safeUrl = resourceUrl
  try {
    const parsed = new URL(resourceUrl, window.location.origin)
    safeUrl = `${parsed.origin}${parsed.pathname}`
  } catch {
    safeUrl = resourceUrl.split('?')[0]
  }
  const error = new Error(`资源加载失败：${safeUrl}`)
  error.name = 'ResourceLoadError'
  reportFrontendError(error, `resource:${target?.tagName?.toLowerCase() || 'unknown'}`)
}

export function setupFrontendErrorReporting(app: App) {
  const previousHandler = app.config.errorHandler
  app.config.errorHandler = (
    error: unknown,
    instance: ComponentPublicInstance | null,
    info: string
  ) => {
    if (isApiBusinessError(error)) return
    reportFrontendError(error, `vue:${info}`)
    if (previousHandler) {
      previousHandler(error, instance, info)
    } else {
      console.error(error)
    }
  }

  window.addEventListener(
    'error',
    (event) => {
      if (event instanceof ErrorEvent && event.error) {
        reportFrontendError(event.error, 'window:error')
        return
      }
      resourceError(event)
    },
    true
  )
}
