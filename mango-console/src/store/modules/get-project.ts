import { defineStore } from 'pinia'
import {
  getProjectPytestName,
  getUserProjectAll,
  getUserProjectProductName,
} from '@/api/system/project'
import { getUserModuleTree } from '@/api/system/module'

let projectRequest: Promise<void> | null = null
let projectProductRequest: Promise<void> | null = null
let projectPytestRequest: Promise<void> | null = null
let allProductModuleTreeRequest: Promise<any[]> | null = null
let allProductModuleTreeCacheVersion = 0
const ALL_PRODUCT_MODULE_TREE_CACHE_TIMEOUT = 60 * 5 * 1000

export const useProject = defineStore('get-project', {
  state: () => {
    return {
      data: [],
      projectProduct: [],
      projectPytest2: [],
      projectPytest: [],
      projectProductNavigationSelection: {
        projectProduct: null as string | number | null,
        module: null as string | number | null,
        moduleTreeKey: null as string | null,
        moduleIds: [] as Array<string | number>,
      },
      allProductModuleTreeCache: {
        data: [] as any[],
        expiresAt: 0,
      },
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
    getPytestProjectProductId(pytestProductId: any) {
      const value = Array.isArray(pytestProductId)
        ? pytestProductId[pytestProductId.length - 1]
        : pytestProductId
      if (value === null || value === undefined || value === '') {
        return null
      }
      for (const project of this.projectPytest) {
        const pytestProduct = (project.children || []).find(
          (item) => String(item.value) === String(value)
        )
        if (pytestProduct) {
          return pytestProduct.project_product_id ?? null
        }
      }
      return null
    },
    setProjectProductNavigationSelection(projectProduct: string | number | null) {
      this.projectProductNavigationSelection.projectProduct = projectProduct
    },
    clearProjectProductNavigationSelection() {
      this.projectProductNavigationSelection.projectProduct = null
    },
    setModuleNavigationSelection(
      module: string | number | null,
      moduleTreeKey: string | null = null,
      moduleIds: Array<string | number> = []
    ) {
      this.projectProductNavigationSelection.module = module
      this.projectProductNavigationSelection.moduleTreeKey = moduleTreeKey
      this.projectProductNavigationSelection.moduleIds = moduleIds
    },
    clearModuleNavigationSelection() {
      this.projectProductNavigationSelection.module = null
      this.projectProductNavigationSelection.moduleTreeKey = null
      this.projectProductNavigationSelection.moduleIds = []
    },
    clearAllProjectProductNavigationSelection() {
      this.projectProductNavigationSelection = {
        projectProduct: null,
        module: null,
        moduleTreeKey: null,
        moduleIds: [],
      }
    },
    getAllProductModuleTree(force = false): Promise<any[]> {
      const cached = this.allProductModuleTreeCache
      if (!force && cached.expiresAt > Date.now()) {
        return Promise.resolve(cached.data)
      }
      if (allProductModuleTreeRequest) return allProductModuleTreeRequest
      const requestVersion = allProductModuleTreeCacheVersion
      const request = getUserModuleTree()
        .then((res) => {
          const data = Array.isArray(res.data) ? res.data : []
          if (requestVersion === allProductModuleTreeCacheVersion) {
            this.allProductModuleTreeCache = {
              data,
              expiresAt: Date.now() + ALL_PRODUCT_MODULE_TREE_CACHE_TIMEOUT,
            }
          }
          return data
        })
        .catch((error) => {
          console.error(error)
          return cached.data
        })
        .finally(() => {
          if (allProductModuleTreeRequest === request) {
            allProductModuleTreeRequest = null
          }
        })
      allProductModuleTreeRequest = request
      return request
    },
    invalidateAllProductModuleTreeCache() {
      allProductModuleTreeCacheVersion += 1
      allProductModuleTreeRequest = null
      this.allProductModuleTreeCache = { data: [], expiresAt: 0 }
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
