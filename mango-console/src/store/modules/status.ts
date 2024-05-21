import { defineStore } from 'pinia'
import { getSystemEnumStatus } from '@/api/system'
export const useStatus = defineStore('get-status', {
  state: () => {
    return {
      data: [],
    }
  },
  getters: {},
  actions: {
    refresh() {
      getSystemEnumStatus()
        .then((res) => {
          this.data = res.data
        })
        .catch(console.log)
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
