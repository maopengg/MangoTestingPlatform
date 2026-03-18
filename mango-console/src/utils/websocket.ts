// WebSocket 管理服务
import { Notification } from '@arco-design/web-vue'
import { useNotificationMessage } from '@/store/modules/notification-message'
import { webSocketURL } from '@/api/axios.config'
import { SERVER } from '@/setting'

// 连接状态枚举
enum ConnectionState {
  DISCONNECTED = 'DISCONNECTED',
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  AUTHENTICATED = 'AUTHENTICATED',
}

// 消息接口（与后端保持一致）
interface WebSocketMessage {
  code: number
  msg: string
  user: string | null
  is_notice?: string
  data?: {
    func_name?: string
    func_args?: any
  } | null
}

class WebSocketService {
  private static instance: WebSocketService | null = null
  private socket: WebSocket | null = null
  private connectionState: ConnectionState = ConnectionState.DISCONNECTED
  private reconnectTimer: number | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = Infinity // 无限重连
  private reconnectInterval = 5000 // 5秒
  private heartbeatTimer: number | null = null
  private heartbeatInterval = 30000 // 30秒心跳
  private url = ''
  private username = ''
  private password = ''
  private notificationMessage: any = null
  private isManualClose = false // 是否手动关闭

  private constructor() {
    // 私有构造函数，确保单例
  }

  // 获取单例
  public static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService()
    }
    return WebSocketService.instance
  }

  // 初始化并连接
  public connect(username: string, password: string): void {
    if (this.connectionState !== ConnectionState.DISCONNECTED) {
      console.warn('WebSocket 已连接或正在连接中')
      return
    }

    this.username = username
    this.password = password
    this.url = `${webSocketURL}username=${username}&password=${password}`
    this.isManualClose = false
    this.notificationMessage = useNotificationMessage()

    this._connect()
  }

  // 内部连接方法
  private _connect(): void {
    if (this.isManualClose) {
      return
    }

    this.connectionState = ConnectionState.CONNECTING

    try {
      this.socket = new WebSocket(this.url)
      this.socket.binaryType = 'arraybuffer'

      this.socket.onopen = this._onOpen.bind(this)
      this.socket.onmessage = this._onMessage.bind(this)
      this.socket.onclose = this._onClose.bind(this)
      this.socket.onerror = this._onError.bind(this)
    } catch (error) {
      console.error('WebSocket 连接失败:', error)
      this._scheduleReconnect()
    }
  }

  // 连接成功
  private _onOpen(): void {
    this.connectionState = ConnectionState.CONNECTED
    this.reconnectAttempts = 0

    // 发送握手消息
    const message: WebSocketMessage = {
      code: 200,
      msg: `Hi, ${SERVER}, mango-console Request Connection!`,
      user: this.username,
      data: null,
    }
    this.send(message)

    // 标记为已认证（前端简化处理）
    this.connectionState = ConnectionState.AUTHENTICATED

    // 启动心跳
    this._startHeartbeat()
  }

  // 接收消息
  private _onMessage(event: MessageEvent): void {
    try {
      const res: WebSocketMessage = JSON.parse(event.data)
      const currentTime = this._formatDateTime(new Date())

      // 更新消息中心
      if (this.notificationMessage) {
        this.notificationMessage.addBadgeValue()
        this.notificationMessage.addMessageContentList(
          currentTime,
          res.msg,
          res.code === 200 ? 1 : 0
        )
      }

      // 显示通知
      if (res.code === 200) {
        Notification.success({
          title: '消息',
          content: res.msg,
          duration: 3000,
        })
      } else {
        Notification.error({
          title: '错误',
          content: res.msg,
          duration: 5000,
        })
      }
    } catch (error) {
      console.error('消息解析失败:', error)
    }
  }

  // 连接关闭
  private _onClose(event: CloseEvent): void {
    this.connectionState = ConnectionState.DISCONNECTED
    this._stopHeartbeat()

    if (!this.isManualClose) {
      Notification.warning({
        title: 'WebSocket 连接断开',
        content: '正在尝试重新连接...',
        duration: 3000,
      })
      this._scheduleReconnect()
    }
  }

  // 连接错误
  private _onError(error: Event): void {
    console.error('WebSocket 错误:', error)
    this.connectionState = ConnectionState.DISCONNECTED
  }

  // 安排重连
  private _scheduleReconnect(): void {
    if (this.isManualClose) {
      return
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('达到最大重连次数，停止重连')
      Notification.error({
        title: 'WebSocket 连接失败',
        content: '无法连接到服务器，请检查网络或稍后重试',
        duration: 0,
      })
      return
    }

    // 清除之前的定时器
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    this.reconnectAttempts++
    this.reconnectTimer = window.setTimeout(() => {
      this._connect()
    }, this.reconnectInterval)
  }

  // 启动心跳
  private _startHeartbeat(): void {
    this._stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      if (this.connectionState === ConnectionState.AUTHENTICATED) {
        this.send({
          code: 200,
          msg: 'ping',
          user: this.username,
          data: null,
        })
      }
    }, this.heartbeatInterval)
  }

  // 停止心跳
  private _stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  // 发送消息
  public send(message: WebSocketMessage): void {
    if (
      this.connectionState !== ConnectionState.AUTHENTICATED &&
      this.connectionState !== ConnectionState.CONNECTED
    ) {
      console.warn('WebSocket 未连接，消息未发送:', message)
      Notification.warning({
        title: '发送失败',
        content: 'WebSocket 未连接',
        duration: 2000,
      })
      return
    }

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify(message))
      } catch (error) {
        console.error('消息发送失败:', error)
      }
    }
  }

  // 断开连接
  public disconnect(): void {
    this.isManualClose = true
    this.connectionState = ConnectionState.DISCONNECTED

    // 清理定时器
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this._stopHeartbeat()

    // 关闭连接
    if (this.socket) {
      this.socket.close(1000, 'Manual disconnect')
      this.socket = null
    }

    this.reconnectAttempts = 0
  }

  // 获取连接状态
  public getState(): ConnectionState {
    return this.connectionState
  }

  // 是否已连接
  public isConnected(): boolean {
    return this.connectionState === ConnectionState.AUTHENTICATED
  }

  // 格式化时间
  private _formatDateTime(date: Date): string {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  }
}

// 导出单例实例
export const websocketService = WebSocketService.getInstance()

// 导出类型
export type { WebSocketMessage }
export { ConnectionState }
