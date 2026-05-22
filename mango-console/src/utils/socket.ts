// 简化的 WebSocket 工具函数
import { websocketService } from './websocket'

const WEB_SOCKET_LOGIN_SESSION_KEY = 'mango:websocket-login-session'

/**
 * 标记当前浏览器会话已经完成登录，允许路由刷新后自动恢复 WebSocket。
 */
export function markWebSocketLoginSession(): void {
  sessionStorage.setItem(WEB_SOCKET_LOGIN_SESSION_KEY, '1')
}

/**
 * 当前浏览器会话是否允许自动连接 WebSocket。
 */
export function hasWebSocketLoginSession(): boolean {
  return sessionStorage.getItem(WEB_SOCKET_LOGIN_SESSION_KEY) === '1'
}

/**
 * 清理当前浏览器会话的 WebSocket 自动连接标记。
 */
export function clearWebSocketLoginSession(): void {
  sessionStorage.removeItem(WEB_SOCKET_LOGIN_SESSION_KEY)
}

/**
 * 连接 WebSocket
 * @param username 用户名
 * @param password 密码
 */
export function connectWebSocket(username: string, password: string): void {
  websocketService.connect(username, password)
}

/**
 * 断开 WebSocket
 */
export function disconnectWebSocket(): void {
  clearWebSocketLoginSession()
  websocketService.disconnect()
}

/**
 * 发送消息
 * @param message 消息对象
 */
export function sendWebSocketMessage(message: any): void {
  websocketService.send(message)
}

/**
 * 获取连接状态
 */
export function getWebSocketState(): string {
  return websocketService.getState()
}

/**
 * 检查是否已连接
 */
export function isWebSocketConnected(): boolean {
  return websocketService.isConnected()
}
