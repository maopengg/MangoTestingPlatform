import WebSocketService from '@/utils/websocket'
import { webSocketURL } from '@/api/axios.config'

// let webSocketService: WebSocketService | null = null

export function websocket(userName: number, password: string, close = true) {
  let webSocketService
  if (!webSocketService) {
    webSocketService = new WebSocketService(
      `${webSocketURL}username=${userName}&password=${password}`
    )
  }
  if (close) {
    webSocketService.connect()
  } else if (!close) {
    webSocketService.disconnect()
  }
}
