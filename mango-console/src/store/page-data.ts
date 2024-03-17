import { defineStore } from 'pinia'

export const usePageData = defineStore({
  id: 'page-data',
  state: () => ({
    record: null, // 在 store 中存储对象的属性
  }),
  actions: {
    setRecord(record: any) {
      this.record = record // 设置 store 中对象的值
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
