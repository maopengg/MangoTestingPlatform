import { defineStore } from 'pinia'
import { getUserProjectAll, getUserProjectProductName } from '@/api/system/project'
import { getUserProductName } from '@/api/system/product'
export const useProject = defineStore('get-project', {
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
