// WebSocketService.ts
import { reactive } from 'vue'
import { Notification } from '@arco-design/web-vue'

interface WebSocketServiceState {
  url: string
  socket: WebSocket | null
}
export default class WebSocketService {
  private state: WebSocketServiceState

  constructor(url: string) {
    this.state = reactive({
      url,
      socket: null
    })
  }

  connect() {
    this.state.socket = new WebSocket(this.state.url)

    this.state.socket.onopen = () => {
      Notification.success('WebSocket服务已启动，开始接收服务器消息和发送指令给执行端！')
      // 发送消息
      const message = {
        code: 200,
        func: null,
        user_info: null,
        msg: 'Hello WebSocket!',
        data: null
      }
      this.state.socket?.send(JSON.stringify(message))
    }

    this.state.socket.onmessage = (event) => {
      const res = JSON.parse(event.data)
      console.log(res.msg)
      Notification.info('WebSocket接收到消息：' + res.msg)
    }

    this.state.socket.onclose = () => {
      Notification.error('WebSocket连接已关闭！')
    }

    this.state.socket.onerror = (error) => {
      console.log('WebSocket发生错误：', error)
    }
  }
  // 关闭函数
  disconnect() {
    if (this.state.socket) {
      this.state.socket.close()
      this.state.socket = null
    }
  }
  // 发送消息函数
  sendMessage(code: number, func: string, user_info: number, msg: string, data: object) {
    const message = {
      code: code,
      func: func,
      user_info: user_info,
      msg: msg,
      data: data
    }

    if (this.state.socket) {
      this.state.socket.send(JSON.stringify(message))
    }
  }
}
