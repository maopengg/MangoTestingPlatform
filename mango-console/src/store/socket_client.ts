import { defineStore } from 'pinia'
import WebSocketService from '@/utils/websocket'
import { webSocketURL } from '@/api/axios.config'

export const useSocketClient = defineStore('socket-client', {
  state: (): { socket_obj: WebSocketService | null; username: number; password: string } => {
    return {
      socket_obj: null,
      username: 0,
      password: '',
    }
  },
  getters: {},
  actions: {
    created() {
      this.socket_obj = new WebSocketService(
        `${webSocketURL}username=${this.userName}&password=${this.password}`
      )
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
