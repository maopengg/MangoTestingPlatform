import { Message } from '@arco-design/web-vue'
import { useUserStoreContext } from '@/store/modules/user'

const AUTH_EXPIRED_MESSAGES = [
  '当前用户登录已过期，请重新登录',
  '登录状态异常，请重新登录',
  '未提供 token',
  'token 无效，请检查后重试',
  'token 非法，请使用有效的 token',
  '用户不存在或已被删除，请重新登录',
]

let isHandlingAuthExpired = false
let lastExpiredMessageTime = 0
const EXPIRED_MESSAGE_INTERVAL = 5000

function getCurrentRoutePath() {
  if (typeof window === 'undefined') return '/'
  const hashPath = window.location.hash.replace(/^#/, '')
  if (!hashPath || hashPath.startsWith('/login')) return '/'
  return hashPath
}

export function isAuthExpiredResponse(status?: number, code?: number, msg?: string) {
  if (status === 401) return true
  if (!msg) return false
  if ([301, 302, 303, 305].includes(Number(code))) return true
  return AUTH_EXPIRED_MESSAGES.some((message) => msg.includes(message))
}

export function handleAuthExpired(message = '当前用户登录已过期，请重新登录') {
  const now = Date.now()
  if (now - lastExpiredMessageTime > EXPIRED_MESSAGE_INTERVAL) {
    Message.error(message)
    lastExpiredMessageTime = now
  }
  if (isHandlingAuthExpired) return
  isHandlingAuthExpired = true

  const redirect = getCurrentRoutePath()
  const loginHash = `#/login?redirect=${encodeURIComponent(redirect)}`
  const loginUrl = `${window.location.origin}${window.location.pathname}${window.location.search}${loginHash}`

  const userStore = useUserStoreContext()
  userStore.logout().finally(() => {
    window.location.replace(loginUrl)
  })
}
