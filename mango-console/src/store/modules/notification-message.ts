import { defineStore } from 'pinia'

export interface NotificationMessageItem {
  title: string
  description: string
  status: number
  code?: number
  read: boolean
  kind?: 'message' | 'task_result'
  taskId?: number | string
  taskType?: string
  businessType?: string
  businessId?: number | string
  resultName?: string
  statusText?: string
  errorMessage?: string
  durationSeconds?: number | null
}

export const useNotificationMessage = defineStore('get-notification-message', {
  state: () => {
    return {
      messageContentList: [] as NotificationMessageItem[],
      messageUnreadCount: 0,
      todoPendingCount: 0,
    }
  },
  getters: {
    totalBadgeValue: (state) => state.messageUnreadCount + state.todoPendingCount,
  },
  actions: {
    setTodoPendingCount(count: number) {
      this.todoPendingCount = Math.max(0, Number(count) || 0)
    },
    addMessage(
      title: string,
      description: string,
      code: number,
      detail: Partial<NotificationMessageItem> = {}
    ) {
      const failed = Number(code) !== 200
      const isTaskResult = detail.kind === 'task_result'
      this.messageContentList.unshift({
        title,
        description,
        status: failed ? 0 : 1,
        code,
        read: !(failed || isTaskResult),
        ...detail,
      })
      if (this.messageContentList.length > 200) {
        const removedItems = this.messageContentList.splice(200)
        const removedUnreadItems = removedItems.filter((item) => item.read === false).length
        this.messageUnreadCount = Math.max(0, this.messageUnreadCount - removedUnreadItems)
      }
      if (failed || isTaskResult) this.messageUnreadCount += 1
    },
    markAllMessagesRead() {
      this.messageUnreadCount = 0
      this.messageContentList.forEach((item) => {
        item.read = true
      })
    },
    clearMessages() {
      this.messageUnreadCount = 0
      this.messageContentList.splice(0, this.messageContentList.length)
    },
  },
  presist: {
    enable: true,
    resetToState: true,
    option: {
      exclude: ['todoPendingCount'],
    },
  },
})
