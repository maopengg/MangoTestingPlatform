import { defineStore } from 'pinia'
import WebSocketService from '@/utils/websocket'
import { webSocketURL } from '@/api/axios.config'
// import useUserStore from '@/store/modules/user'

// const userStore = useUserStore()
// 1.定义容器
export const useSocketClient = defineStore('socket-client', {
  state: (): { socket_obj: WebSocketService | null; username: number } => {
    return {
      socket_obj: null,
      username: 0,
    }
  },
  getters: {},
  actions: {
    created() {
      // 在created生命周期钩子函数中创建socket_obj
      this.socket_obj = new WebSocketService(webSocketURL + this.username)
      this.socket_obj.connect()
    },
    socketService(userName: number, close = true): void {
      if (this.socket_obj !== null) {
        if (close) {
          this.socket_obj.connect()
        } else {
          this.socket_obj.disconnect()
        }
      }
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
