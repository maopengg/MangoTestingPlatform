import { defineStore } from 'pinia'
import {
  getProjectPytestName,
  getUserProjectAll,
  getUserProjectProductName,
} from '@/api/system/project'

let projectRequest: Promise<void> | null = null
let projectProductRequest: Promise<void> | null = null
let projectPytestRequest: Promise<void> | null = null

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
      if (projectRequest) {
        return projectRequest
      }
      projectRequest = getUserProjectAll()
        .then((res) => {
          this.data = Array.isArray(res.data) ? res.data : []
        })
        .catch(console.log)
        .finally(() => {
          projectRequest = null
        })
      return projectRequest
    },
    projectProductName() {
      if (projectProductRequest) {
        return projectProductRequest
      }
      projectProductRequest = getUserProjectProductName()
        .then((res) => {
          this.projectProduct = Array.isArray(res.data) ? res.data : []
        })
        .catch((error) => {
          console.error(error)
        })
        .finally(() => {
          projectProductRequest = null
        })
      return projectProductRequest
    },

    projectPytestName() {
      if (projectPytestRequest) {
        return projectPytestRequest
      }
      projectPytestRequest = getProjectPytestName()
        .then((res) => {
          const data = Array.isArray(res.data) ? res.data : []
          this.projectPytest = JSON.parse(JSON.stringify(data))
          this.projectPytest2 = JSON.parse(JSON.stringify(data))
          this.projectPytest2.forEach((item) => {
            ;(item.children || []).forEach((item1) => {
              delete item1.children
            })
          })
        })
        .catch(console.log)
        .finally(() => {
          projectPytestRequest = null
        })
      return projectPytestRequest
    },
    getProjectPytestModule(productId: any) {
      if (productId === null) {
        return []
      }
      for (const item of this.projectPytest) {
        for (const item1 of item.children || []) {
          if (item1.value === productId) {
            return item1.children || []
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
