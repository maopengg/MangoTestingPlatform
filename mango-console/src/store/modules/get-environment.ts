import { defineStore } from 'pinia'
import { getSystemEnumEnvironment } from '@/api/system'
// 1.定义容器
export const useEnvironment = defineStore('get-environment', {
  // 类似于data，用来存储全局状态，必须是箭头函数
  state: () => {
    return {
      data: [],
      selectTitle: '选择测试环境',
      selectValue: null as number | null,
    }
  },
  // 类似于computed，用来封装计算属性
  getters: {},
  // 封装业务逻辑，修改state
  actions: {
    getEnvironment() {
      getSystemEnumEnvironment()
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
