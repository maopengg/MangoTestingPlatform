import { defineStore } from 'pinia'
import { getUserProjectAll, getUserProjectProductName } from '@/api/user'
// 1.定义容器
export const useProject = defineStore('get-project', {
  // 类似于data，用来存储全局状态，必须是箭头函数
  state: () => {
    return {
      data: [],
      selectTitle: '选择项目',
      selectValue: null as number | null,
      projectList: [],
      projectProduct: [],
    }
  },
  // 类似于computed，用来封装计算属性
  getters: {},
  // 封装业务逻辑，修改state
  actions: {
    getProject() {
      getUserProjectAll()
        .then((res) => {
          this.data = res.data
          this.initialization()
        })
        .catch(console.log)
    },
    projectProductName() {
      getUserProjectProductName()
        .then((res) => {
          this.projectProduct = res.data
        })
        .catch((error) => {
          console.error(error)
        })
    },
    initialization() {
      if (this.data) {
        this.projectList.splice(0, this.projectList.length)
        this.projectList.push({ key: null, title: '选择项目' })
        this.data.forEach((item) => {
          this.projectList.push(item)
        })
      }
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
