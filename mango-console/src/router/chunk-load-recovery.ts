import router from './index'
import { reportFrontendError } from '@/utils/system-error-reporter'

const RELOAD_MARKER_KEY = 'mango:chunk-load-recovery'
const CHUNK_LOAD_ERROR_PATTERNS = [
  /failed to fetch dynamically imported module/i,
  /importing a module script failed/i,
  /chunkloaderror/i,
  /loading chunk [\d]+ failed/i,
]

export function isChunkLoadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error || '')
  return CHUNK_LOAD_ERROR_PATTERNS.some((pattern) => pattern.test(message))
}

function readReloadMarker() {
  try {
    return window.sessionStorage.getItem(RELOAD_MARKER_KEY)
  } catch (_) {
    return null
  }
}

function writeReloadMarker(value: string) {
  try {
    window.sessionStorage.setItem(RELOAD_MARKER_KEY, value)
  } catch (_) {
    // sessionStorage 不可用时仍允许进行一次页面恢复。
  }
}

function clearReloadMarker() {
  try {
    window.sessionStorage.removeItem(RELOAD_MARKER_KEY)
  } catch (_) {
    // 清理失败不影响已成功的路由导航。
  }
}

export default function setupChunkLoadRecovery() {
  router.onError((error, to) => {
    const errorObject = `router:${to?.fullPath || 'unknown'}`
    if (!isChunkLoadError(error)) {
      reportFrontendError(error, errorObject)
      return
    }
    const target = to?.fullPath || window.location.hash || '/'
    if (readReloadMarker() === target) {
      reportFrontendError(error, errorObject)
      console.error('动态资源刷新后仍加载失败', error)
      return
    }
    writeReloadMarker(target)
    window.location.reload()
  })

  router.afterEach((to) => {
    if (readReloadMarker() === to.fullPath) clearReloadMarker()
  })
}
