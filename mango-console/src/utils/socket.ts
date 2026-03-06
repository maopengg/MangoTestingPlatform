// 简化的 WebSocket 工具函数
import { websocketService } from './websocket'

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
