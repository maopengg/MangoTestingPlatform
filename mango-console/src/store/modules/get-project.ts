import { defineStore } from 'pinia'
import { getUserProductName, getUserProjectAll, getUserProjectProductName } from '@/api/user'
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
      projectProductList: [],
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
    projectProductNameList(projectId: number | null = null) {
      getUserProductName(projectId)
        .then((res) => {
          this.projectProductList = res.data
        })
        .catch(console.log)
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
