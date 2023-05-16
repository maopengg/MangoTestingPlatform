import { defineStore } from 'pinia'
import { get } from '@/api/http'
import { getTestObjName } from '@/api/url'
// 1.定义容器
export const useTestObj = defineStore('get-test-obj', {
  // 类似于data，用来存储全局状态，必须是箭头函数
  state: () => {
    return {
      data: [],
      te: null as number | null
    }
  },
  // 类似于computed，用来封装计算属性
  getters: {},
  // 封装业务逻辑，修改state
  actions: {
    getEnvironment() {
      get({
        url: getTestObjName
      })
        .then((res) => {
          this.data = res.data
          console.log(this.data)
        })
        .catch(console.log)
    }
  }
})
