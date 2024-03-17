import WebSocketService from '@/utils/websocket'
import { webSocketURL } from '@/api/axios.config'

// let webSocketService: WebSocketService | null = null

export function websocket(userName: number, close = true) {
  let webSocketService
  if (!webSocketService) {
    webSocketService = new WebSocketService(webSocketURL + userName)
  }
  if (close) {
    webSocketService.connect()
  } else if (!close) {
    webSocketService.disconnect()
  }
}
