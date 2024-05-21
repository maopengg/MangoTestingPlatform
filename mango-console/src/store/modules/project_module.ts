import { defineStore } from 'pinia'
import { getUserModuleName } from '@/api/user'
// 1.定义容器
export const useProductModule = defineStore('product-module', {
  // 类似于data，用来存储全局状态，必须是箭头函数
  state: () => {
    return {
      data: [],
    }
  },
  // 类似于computed，用来封装计算属性
  getters: {},
  // 封装业务逻辑，修改state
  actions: {
    getProjectModule(projectProductId: number | string | null = null) {
      getUserModuleName(projectProductId)
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
