import { defineStore } from 'pinia'
import {
  getProjectPytestName,
  getUserProjectAll,
  getUserProjectProductName,
} from '@/api/system/project'

export const useProject = defineStore('get-project', {
  state: () => {
    return {
      data: [],
      selectTitle: '选择项目',
      selectValue: null as number | null,
      projectProduct: [],
      projectPytest2: [],
      projectPytest: [],
    }
  },
  getters: {},
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

    projectPytestName() {
      getProjectPytestName()
        .then((res) => {
          this.projectPytest = JSON.parse(JSON.stringify(res.data))
          this.projectPytest2 = JSON.parse(JSON.stringify(res.data))
          this.projectPytest2.forEach((item) => {
            item.children.forEach((item1) => {
              delete item1.children
            })
          })
        })
        .catch(console.log)
    },
    getProjectPytestModule(productId: any) {
      if (productId === null) {
        return []
      }
      for (const item of this.projectPytest) {
        for (const item1 of item.children) {
          if (item1.value === productId) {
            return item1.children
          }
        }
      }
      return []
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
