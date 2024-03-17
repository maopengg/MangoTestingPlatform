// WebSocketService.ts
import { reactive } from 'vue'
import { Notification } from '@arco-design/web-vue'
import { SERVER } from '@/setting'

interface WebSocketServiceState {
  url: string
  socket: WebSocket | null
}

export default class WebSocketService {
  state: WebSocketServiceState

  constructor(url: string) {
    this.state = reactive({
      url,
      socket: null,
    })
  }

  connect() {
    this.state.socket = new WebSocket(this.state.url)

    this.state.socket.onopen = () => {
      // Notification.success(`Socket服务已启动，开始接收${SERVER}消息和发送指令给${DRIVER}！`)
      // 发送消息
      const message = {
        code: 200,
        func: null,
        user: null,
        msg: `Hi, ${SERVER}, mango-console Request Connection!`,
        data: null,
        end: null,
      }
      this.state.socket?.send(JSON.stringify(message))
    }

    this.state.socket.onmessage = (event) => {
      const res = JSON.parse(event.data)
      if (res.code == 200) {
        Notification.success('消息：' + res.msg)
      } else {
        Notification.error('消息:' + res.msg)
      }
    }

    this.state.socket.onclose = () => {
      Notification.error('与服务器连接中断，正在尝试重连！')
      this.state.socket = null
      // 尝试重连
      while (this.state.socket !== null) {
        setTimeout(() => {
          this.connect()
          Notification.info('重连中...')
        }, 5000)
      }
    }

    this.state.socket.onerror = (error) => {
      console.log('socket发生错误：', error)
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
  sendMessage(code: number, func: string, user: number, msg: string, data: object, end: boolean) {
    const message = {
      code: code,
      func: func,
      user: user,
      msg: msg,
      data: data,
      end: end,
    }

    if (this.state.socket) {
      this.state.socket.send(JSON.stringify(message))
    }
  }
}
