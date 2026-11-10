
import { reportLoadError } from '@/utils/load-error'
import { defineStore } from 'pinia'
import { effectScope, toRaw, watch } from 'vue'
import useUserStore from './user'
import {
  moduleOptions, optionResponse, productOptions, projectOptions,
  type ProductModuleOption, type ProjectOption, type ProjectProductOption,
} from './project-options'
import {
  getProjectPytestName,
  getUserProjectAll,
  getUserProjectProductName,
} from '@/api/system/project'
import { getUserModuleTree } from '@/api/system/module'
import { invalidateModuleDirectoryCache, moduleDirectoryExpiresAt } from '@/api/system/module-directory-cache'

const ALL_PRODUCT_MODULE_TREE_CACHE_TIMEOUT = 60 * 5 * 1000
const PROJECT_OPTIONS_CACHE_TIMEOUT = 60 * 5 * 1000
type OptionRead = 'projects' | 'products' | 'pytest' | 'modules'
interface RequestScope {
  version: number
  moduleVersion: number
  optionsVersion: number
  expiresAt: Map<Exclude<OptionRead, 'modules'>, { time: number; version: number; moduleVersion: number }>
  disposed: boolean
  pending: Map<OptionRead, Promise<unknown>>
}
// Non-state metadata survives action replacement without entering persistence or devtools state.
const REQUEST_SCOPE_KEY = Symbol.for('mango.project-options.request-scope')

const useProjectStore = defineStore('get-project', {
  state: () => {
    return {
      data: [] as ProjectOption[],
      projectProduct: [] as ProjectProductOption[],
      projectPytest2: [] as ProjectProductOption[],
      projectPytest: [] as ProjectProductOption[],
      optionErrors: { projects: false, products: false, pytest: false, modules: false },
      navigationOwner: '',
      projectProductNavigationSelection: {
        projectProduct: null as string | number | null,
        module: null as string | number | null,
        moduleTreeKey: null as string | null,
        moduleIds: [] as Array<string | number>,
      },
      allProductModuleTreeCache: {
        data: [] as ProductModuleOption[],
        expiresAt: 0,
      },
    }
  },
  getters: {},
  actions: {
    getProject(force = false) {
      return readOptions(this, 'projects', getUserProjectAll, projectOptions, value => { this.data = value }, force)
    },
    projectProductName(force = false) {
      return readOptions(this, 'products', getUserProjectProductName, productOptions, value => { this.projectProduct = value }, force)
    },

    projectPytestName(force = false) {
      return readOptions(this, 'pytest', getProjectPytestName, productOptions, value => {
        this.projectPytest = value
        this.projectPytest2 = value.map(project => ({ ...project, children: project.children?.map(product => {
          const { children, ...option } = product
          return option
        }) }))
      }, force)
    },
    getProjectPytestModule(productId: string | number | null) {
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
    getPytestProjectProductId(pytestProductId: string | number | Array<string | number> | null) {
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
      this.projectProductNavigationSelection.moduleIds = [...moduleIds]
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
    getAllProductModuleTree(force = false): Promise<ProductModuleOption[]> {
      const scope = ensureRequestScope(this)
      const cached = this.allProductModuleTreeCache
      if (!force && cached.expiresAt > Date.now()) {
        return Promise.resolve(cached.data)
      }
      const pending = scope.pending.get('modules') as Promise<ProductModuleOption[]> | undefined
      if (pending) return pending
      const version = scope.version, moduleVersion = scope.moduleVersion
      const current = () => !scope.disposed && scope.version === version && scope.moduleVersion === moduleVersion
      this.optionErrors.modules = false
      const request = Promise.resolve().then(() => current() ? getUserModuleTree(undefined, force) : null)
        .then(response => {
          if (!current()) return []
          const data = moduleOptions(optionResponse(response))
          this.allProductModuleTreeCache = { data, expiresAt: moduleDirectoryExpiresAt('tree') || Date.now() + ALL_PRODUCT_MODULE_TREE_CACHE_TIMEOUT }
          return data
        }).catch((loadFailure0) => {
          if (!current()) return []
          void (reportLoadError(loadFailure0, "加载失败，请重试", false), this.optionErrors.modules = true)
          return cached.data
        }).finally(() => {
          if (scope.pending.get('modules') === request) scope.pending.delete('modules')
        })
      scope.pending.set('modules', request)
      return request
    },
    invalidateProjectOptionsCache() {
      const scope = ensureRequestScope(this)
      scope.optionsVersion++
      scope.expiresAt.clear()
      for (const kind of ['projects', 'products', 'pytest'] as const) {
        scope.pending.delete(kind)
        this.optionErrors[kind] = false
      }
      this.invalidateAllProductModuleTreeCache()
    },
    invalidateAllProductModuleTreeCache() {
      const scope = ensureRequestScope(this)
      invalidateModuleDirectoryCache()
      scope.moduleVersion++
      scope.pending.delete('modules')
      scope.pending.delete('pytest')
      scope.expiresAt.delete('pytest')
      this.optionErrors.pytest = false
      this.optionErrors.modules = false
      this.allProductModuleTreeCache = { data: [], expiresAt: 0 }
    },
  },
  presist: {
    enable: true,
    resetToState: true,
    option: { exclude: ['data', 'projectProduct', 'projectPytest', 'projectPytest2', 'allProductModuleTreeCache', 'optionErrors'] },
  },
})

type ProjectStore = ReturnType<typeof useProjectStore>
type ScopedProjectStore = ProjectStore & { [REQUEST_SCOPE_KEY]?: RequestScope }
function readOptions<T>(store: ProjectStore, kind: Exclude<OptionRead, 'modules'>,
  fetch: () => Promise<unknown>, parse: (value: unknown) => T, publish: (value: T) => void, force = false): Promise<void> {
  const scope = ensureRequestScope(store)
  const pending = scope.pending.get(kind) as Promise<void> | undefined
  if (pending) return pending
  const cached = scope.expiresAt.get(kind)
  if (!force && cached && cached.version === scope.version && cached.time > Date.now() &&
    (kind !== 'pytest' || cached.moduleVersion === scope.moduleVersion)) return Promise.resolve()
  const version = scope.version, optionsVersion = scope.optionsVersion, moduleVersion = scope.moduleVersion
  const current = () => !scope.disposed && scope.version === version && scope.optionsVersion === optionsVersion &&
    (kind !== 'pytest' || scope.moduleVersion === moduleVersion)
  scope.expiresAt.delete(kind)
  store.optionErrors[kind] = false
  const request = Promise.resolve().then(() => current() ? fetch() : null).then(response => {
    if (current()) {
      publish(parse(optionResponse(response)))
      scope.expiresAt.set(kind, { time: Date.now() + PROJECT_OPTIONS_CACHE_TIMEOUT, version, moduleVersion })
    }
  }).catch(() => {
    if (current()) store.optionErrors[kind] = true
  }).finally(() => {
    if (scope.pending.get(kind) === request) scope.pending.delete(kind)
  })
  scope.pending.set(kind, request)
  return request
}

// Every action can initialize its own scope; setup wrappers are not a lifecycle guarantee.
function ensureRequestScope(store: ProjectStore, ownerStore?: ReturnType<typeof useUserStore>): RequestScope {
  const raw = toRaw(store) as ScopedProjectStore
  const existing = raw[REQUEST_SCOPE_KEY]
  if (existing) {
    existing.optionsVersion ??= 0
    existing.expiresAt ??= new Map()
    return existing
  }
  const user = ownerStore ?? useUserStore()
  const scope: RequestScope = { version: 0, moduleVersion: 0, optionsVersion: 0, expiresAt: new Map(), disposed: false, pending: new Map() }
  Object.defineProperty(raw, REQUEST_SCOPE_KEY, { value: scope, configurable: true })
  const owner = () => JSON.stringify([user.userId, user.roleId, user.selected_environment])
  const clear = () => {
    scope.version++
    scope.moduleVersion++
    scope.pending.clear()
    scope.expiresAt.clear()
    store.data = []
    store.projectProduct = []
    store.projectPytest = []
    store.projectPytest2 = []
    store.allProductModuleTreeCache = { data: [], expiresAt: 0 }
    store.clearAllProjectProductNavigationSelection()
    store.optionErrors = { projects: false, products: false, pytest: false, modules: false }
    store.navigationOwner = owner()
  }
  // 同身份只保留导航意图，仍须由侧栏用新目录验证；不持久化响应或凭据。
  const cachedSelection = store.navigationOwner === owner() ? store.projectProductNavigationSelection : null
  clear()
  const selectionId = (value: unknown) => value === null || typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value))
  if (cachedSelection && selectionId(cachedSelection.projectProduct) && selectionId(cachedSelection.module) &&
    (cachedSelection.moduleTreeKey === null || typeof cachedSelection.moduleTreeKey === 'string') &&
    Array.isArray(cachedSelection.moduleIds) && cachedSelection.moduleIds.every(value => value !== null && selectionId(value))) {
    store.projectProductNavigationSelection = {
      projectProduct: cachedSelection.projectProduct, module: cachedSelection.module,
      moduleTreeKey: cachedSelection.moduleTreeKey, moduleIds: [...cachedSelection.moduleIds],
    }
  }
  const observer = effectScope(true)
  observer.run(() => watch(() => [user.userId, user.roleId, user.token, user.selected_environment], clear, { flush: 'sync' }))
  const dispose = store.$dispose.bind(store)
  store.$dispose = () => {
    scope.disposed = true
    clear()
    observer.stop()
    dispose()
  }
  return scope
}

export const useProject = Object.assign((...args: Parameters<typeof useProjectStore>) => {
  const store = useProjectStore(...args)
  ensureRequestScope(store, useUserStore(args[0]))
  return store
}, useProjectStore)
