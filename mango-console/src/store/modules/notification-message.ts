import { defineStore } from 'pinia'

export const useNotificationMessage = defineStore('get-notification-message', {
  state: () => {
    return {
      messageContentList: [],
      badgeValue: 0,
    }
  },
  getters: {},
  actions: {
    addBadgeValue(count = false) {
      if (count) {
        this.badgeValue = 0
      } else {
        this.badgeValue += 1
      }
    },
    addMessageContentList(title, description, status, clear = false) {
      if (!clear) {
        this.messageContentList.unshift({
          title: title,
          description: description,
          status: status,
        })
      } else {
        this.messageContentList.splice(0, this.messageContentList.length)
      }
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
