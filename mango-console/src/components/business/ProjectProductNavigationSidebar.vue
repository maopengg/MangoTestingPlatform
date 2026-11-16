<template>
  <aside
    class="mango-project-navigation-sidebar mango-section-card"
    :class="{ 'mango-project-navigation-sidebar--collapsed': collapsed }"
  >
    <a-tooltip v-if="collapsed" :content="`展开${resolvedTitle}`" position="right">
      <a-button
        class="mango-project-navigation-sidebar__collapse-button"
        type="text"
        size="small"
        :aria-label="`展开${resolvedTitle}`"
        @click="emit('toggle-collapse')"
      >
        <IconRight />
      </a-button>
    </a-tooltip>

    <header v-else class="mango-project-navigation-sidebar__header">
      <div class="mango-project-navigation-sidebar__heading">
        <h3>{{ resolvedTitle }}</h3>
        <p>{{ resolvedDescription }}</p>
      </div>
      <a-tooltip :content="`收起${resolvedTitle}`">
        <a-button
          class="mango-project-navigation-sidebar__collapse-button"
          type="text"
          size="small"
          :aria-label="`收起${resolvedTitle}`"
          @click="emit('toggle-collapse')"
        >
          <IconLeft />
        </a-button>
      </a-tooltip>
    </header>

    <div v-if="!collapsed" class="mango-project-navigation-sidebar__search-panel">
      <a-input-search
        v-model="keyword"
        allow-clear
        size="small"
        :placeholder="showModules ? '搜索项目、产品或模块' : '搜索项目或产品'"
      />
    </div>

    <div v-if="!collapsed" class="mango-project-navigation-sidebar__section-header">
      <span>{{ keyword ? '搜索结果' : showModules ? '模块列表' : '项目 / 产品' }}</span>
      <div class="mango-project-navigation-sidebar__section-actions">
        <a-button type="text" size="mini" @click="toggleExpansion">
          {{ expandedKeys.length ? '收起' : '展开' }}
        </a-button>
      </div>
    </div>

    <div v-if="!collapsed" class="mango-project-navigation-sidebar__tree">
      <a-spin :loading="loading" class="mango-project-navigation-sidebar__spin">
        <template v-if="loadFailed && !loading"></template>
        <a-tree
          v-else-if="displayTree.length"
          v-model:expanded-keys="expandedKeys"
          :data="displayTree"
          :selected-keys="selectedKeys"
          :action-on-node-click="showModules ? undefined : 'expand'"
          block-node
          disable-select-action-only
          size="small"
          @select="onSelect"
        >
          <template #title="nodeData">
            <a-tooltip :disabled="!nodeData.productDescription" position="right">
              <template #content>
                <div class="mango-project-navigation-sidebar__product-description">{{ nodeData.productDescription }}</div>
              </template>
              <span
                :class="{
                  'mango-project-navigation-sidebar__project-start': nodeData.projectGroupStart,
                }"
              >
                {{ nodeData.title }}
              </span>
            </a-tooltip>
          </template>
          <template #switcher-icon>
            <IconRight class="mango-project-navigation-sidebar__switcher-icon" />
          </template>
        </a-tree>
        <div v-else-if="!loading" class="mango-empty-state">
          {{ emptyText }}
        </div>
      </a-spin>
      <div
        v-if="displayTree.length"
        class="mango-project-navigation-sidebar__bottom-spacer"
        aria-hidden="true"
      ></div>
    </div>
  </aside>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { IconLeft, IconRight } from '@arco-design/web-vue/es/icon'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import {
    buildAllProductModuleFilterTree,
    buildProjectProductFilterTree,
    filterModuleTree,
    filterProjectProductOptions,
    flattenProjectProducts,
    getExpandableTreeKeys,
    getModuleIdsForSelection,
    getSelectedModuleIdFromTreeKey,
    getProductIdFromTreeKey,
    getProductIdForTreeSelection,
    getTreeSelectionPath,
    groupModuleTreeByProjectProduct,
    type ModuleOption,
  } from './project-product-filter'

  const props = defineProps({
    modelValue: { type: [String, Number], default: null },
    moduleValue: { type: [String, Number], default: null },
    resetKey: { type: Number, default: 0 },
    showModules: { type: Boolean, default: false },
    emitInitialFilter: { type: Boolean, default: false },
    title: { type: String, default: '' },
    description: { type: String, default: '' },
    collapsed: { type: Boolean, default: false },
  })

  const emit = defineEmits([
    'update:modelValue',
    'update:moduleValue',
    'change',
    'filter-change',
    'toggle-collapse',
  ])
  const ALL_PROJECT_PRODUCTS_KEY = 'scope:all-project-products'
  const allProjectProductsNode = {
    key: ALL_PROJECT_PRODUCTS_KEY,
    title: '全部项目',
  }
  const projectStore = useProject()
  const userStore = useUserStore()
  const keyword = ref('')
  const loading = ref(false)
  const initialized = ref(false)
  const loadFailed = ref(false)
  const expandedKeys = ref<string[]>([])
  const selectedTreeKey = ref(ALL_PROJECT_PRODUCTS_KEY)
  const moduleOptionsByProduct = ref<Record<string, ModuleOption[]>>({})
  let mounted = false
  let active = true
  let disposed = false
  let loadVersion = 0
  let needsLoad = true
  let pendingLoad: { version: number; promise: Promise<void> } | null = null
  const available = () => mounted && active && !disposed && (typeof document === 'undefined' || !document.hidden)

  const projectOptions = computed(() => projectStore.projectProduct || [])
  const productEntries = computed(() => flattenProjectProducts(projectOptions.value))
  const moduleTree = computed(() =>
    buildAllProductModuleFilterTree(productEntries.value, moduleOptionsByProduct.value)
  )
  const fullProductTree = computed(() => buildProjectProductFilterTree(projectOptions.value))
  const productTree = computed(() =>
    buildProjectProductFilterTree(filterProjectProductOptions(projectOptions.value, keyword.value))
  )
  const displayTree = computed(() => {
    const search = keyword.value.trim().toLocaleLowerCase()
    const tree = props.showModules
      ? search
        ? filterModuleTree(moduleTree.value, search)
        : moduleTree.value
      : productTree.value
    return search ? tree : [allProjectProductsNode, ...tree]
  })
  const selectedKeys = computed(() => {
    if (props.showModules) {
      if (selectedTreeKey.value) return [selectedTreeKey.value]
      return hasValue(props.moduleValue)
        ? [`module:${props.moduleValue}`]
        : [ALL_PROJECT_PRODUCTS_KEY]
    }
    return hasValue(props.modelValue) ? [`product:${props.modelValue}`] : [ALL_PROJECT_PRODUCTS_KEY]
  })
  const resolvedTitle = computed(
    () => props.title || (props.showModules ? '模块导航' : '项目 / 产品导航')
  )
  const resolvedDescription = computed(
    () =>
      props.description ||
      (props.showModules ? '点击名称筛选，左侧区域展开' : '按项目查看并筛选产品')
  )
  const emptyText = computed(() => {
    if (loading.value) return ''
    if (keyword.value) return '未找到匹配结果'
    return props.showModules ? '暂无可用模块' : '暂无可用项目或产品'
  })

  function hasValue(value: unknown) {
    return value !== null && value !== undefined && value !== ''
  }

  function emitFilter(
    projectProduct: string | number | null,
    module: string | number | null,
    moduleIds: Array<string | number> = [],
    selectedModuleId: string | number | null = null
  ) {
    emit('update:modelValue', projectProduct)
    emit('update:moduleValue', module)
    emit('change', projectProduct)
    emit('filter-change', { projectProduct, module, moduleIds, selectedModuleId })
  }

  function onSelect(keys: string[]) {
    if (!available() || !initialized.value || loading.value || loadFailed.value) return
    const key = keys[0]
    if (!key) return
    if (key === ALL_PROJECT_PRODUCTS_KEY) {
      selectAllProjectProducts()
      return
    }
    if (!props.showModules) {
      const projectProduct = getProductIdFromTreeKey(key)
      if (projectProduct !== null) {
        projectStore.setProjectProductNavigationSelection(projectProduct)
        projectStore.clearModuleNavigationSelection()
        emitFilter(projectProduct, null)
      }
      return
    }
    const projectProduct = getProductIdForTreeSelection(moduleTree.value, key)
    if (key.startsWith('product-group:') && projectProduct !== null) {
      selectedTreeKey.value = key
      projectStore.setProjectProductNavigationSelection(projectProduct)
      projectStore.clearModuleNavigationSelection()
      emitFilter(projectProduct, null)
      return
    }
    const moduleIds = getModuleIdsForSelection(moduleTree.value, key)
    if (!moduleIds.length) return
    selectedTreeKey.value = key
    const module = key.startsWith('module:') ? moduleIds[0] : null
    const selectedModuleId = getSelectedModuleIdFromTreeKey(key)
    projectStore.setProjectProductNavigationSelection(projectProduct)
    projectStore.setModuleNavigationSelection(module, key, moduleIds)
    emitFilter(projectProduct, module, moduleIds, selectedModuleId)
  }

  function selectAllProjectProducts() {
    selectedTreeKey.value = ALL_PROJECT_PRODUCTS_KEY
    projectStore.clearAllProjectProductNavigationSelection()
    emitFilter(null, null)
  }

  function validateCurrentSelection() {
    if (!initialized.value) return false

    if (!props.showModules) {
      if (!hasValue(props.modelValue)) return false
      const productKey = `product:${props.modelValue}`
      if (getTreeSelectionPath(fullProductTree.value, productKey).length) {
        projectStore.setProjectProductNavigationSelection(props.modelValue)
        return false
      }
      selectAllProjectProducts()
      return true
    }

    if (hasValue(props.moduleValue)) {
      const moduleKey = `module:${props.moduleValue}`
      const modulePath = getTreeSelectionPath(moduleTree.value, moduleKey)
      const projectProduct = getProductIdForTreeSelection(moduleTree.value, moduleKey)
      const matchesProjectProduct =
        !hasValue(props.modelValue) || String(projectProduct) === String(props.modelValue)
      if (modulePath.length && projectProduct !== null && matchesProjectProduct) {
        selectedTreeKey.value = moduleKey
        expandedKeys.value = modulePath.slice(0, -1)
        projectStore.setProjectProductNavigationSelection(projectProduct)
        projectStore.setModuleNavigationSelection(props.moduleValue, moduleKey, [props.moduleValue])
        return false
      }
      selectAllProjectProducts()
      return true
    }

    if (hasValue(props.modelValue)) {
      const currentKey = selectedTreeKey.value
      const currentProjectProduct = getProductIdForTreeSelection(moduleTree.value, currentKey)
      if (
        currentKey.startsWith('module-group:') &&
        getTreeSelectionPath(moduleTree.value, currentKey).length &&
        String(currentProjectProduct) === String(props.modelValue)
      ) {
        return false
      }
      const productKey = `product-group:${props.modelValue}`
      if (getTreeSelectionPath(moduleTree.value, productKey).length) {
        selectedTreeKey.value = productKey
        projectStore.setProjectProductNavigationSelection(props.modelValue)
        projectStore.clearModuleNavigationSelection()
        return false
      }
      selectAllProjectProducts()
      return true
    }

    selectedTreeKey.value = ALL_PROJECT_PRODUCTS_KEY
    return false
  }

  function collapseAll() {
    expandedKeys.value = []
  }

  function toggleExpansion() {
    if (expandedKeys.value.length) {
      collapseAll()
      return
    }
    expandedKeys.value = getExpandableTreeKeys(displayTree.value)
  }

  function restoreCachedSelection() {
    const cached = projectStore.projectProductNavigationSelection
    if (!props.showModules) {
      if (!hasValue(cached?.projectProduct)) return false
      const projectProduct = cached.projectProduct as string | number
      const hasProjectProduct = productEntries.value.some(
        (entry) => String(entry.projectProductId) === String(projectProduct)
      )
      if (!hasProjectProduct) {
        projectStore.clearProjectProductNavigationSelection()
        projectStore.clearModuleNavigationSelection()
        return false
      }
      const productKey = `product:${projectProduct}`
      const productPath = getTreeSelectionPath(fullProductTree.value, productKey)
      expandedKeys.value = productPath.slice(0, -1)
      emitFilter(projectProduct, null)
      return true
    }
    if (cached.moduleTreeKey?.startsWith('module-group:')) {
      const modulePath = getTreeSelectionPath(moduleTree.value, cached.moduleTreeKey)
      const moduleProjectProduct = getProductIdForTreeSelection(
        moduleTree.value,
        cached.moduleTreeKey
      )
      const moduleIds = getModuleIdsForSelection(moduleTree.value, cached.moduleTreeKey)
      if (modulePath.length && moduleProjectProduct !== null && moduleIds.length) {
        selectedTreeKey.value = cached.moduleTreeKey
        expandedKeys.value = modulePath.slice(0, -1)
        projectStore.setProjectProductNavigationSelection(moduleProjectProduct)
        projectStore.setModuleNavigationSelection(null, cached.moduleTreeKey, moduleIds)
        emitFilter(
          moduleProjectProduct,
          null,
          moduleIds,
          getSelectedModuleIdFromTreeKey(cached.moduleTreeKey)
        )
        return true
      }
      projectStore.clearModuleNavigationSelection()
    }
    if (hasValue(cached.module)) {
      const moduleKey = `module:${cached.module}`
      const modulePath = getTreeSelectionPath(moduleTree.value, moduleKey)
      const moduleProjectProduct = getProductIdForTreeSelection(moduleTree.value, moduleKey)
      if (modulePath.length && moduleProjectProduct !== null) {
        selectedTreeKey.value = moduleKey
        expandedKeys.value = modulePath.slice(0, -1)
        projectStore.setProjectProductNavigationSelection(moduleProjectProduct)
        emitFilter(
          moduleProjectProduct,
          cached.module,
          [cached.module as string | number],
          cached.module as string | number
        )
        return true
      }
      projectStore.clearModuleNavigationSelection()
    }
    if (!hasValue(cached?.projectProduct)) return false
    const projectProduct = cached.projectProduct as string | number
    const productKey = `product-group:${projectProduct}`
    if (getTreeSelectionPath(moduleTree.value, productKey).length) {
      selectedTreeKey.value = productKey
      emitFilter(projectProduct, null)
      return true
    }
    projectStore.clearProjectProductNavigationSelection()
    return false
  }

  watch(
    () => props.resetKey,
    () => {
      keyword.value = ''
      selectedTreeKey.value = ALL_PROJECT_PRODUCTS_KEY
      expandedKeys.value = []
      projectStore.clearAllProjectProductNavigationSelection()
    }
  )
  watch(keyword, (value) => {
    expandedKeys.value = value.trim() ? getExpandableTreeKeys(displayTree.value) : []
  })
  watch([() => props.modelValue, () => props.moduleValue, fullProductTree, moduleTree], () =>
    validateCurrentSelection()
  )
  watch(
    () => props.showModules,
    () => {
      invalidateLoad()
      void loadNavigation()
    },
    { flush: 'sync' }
  )

  function syncSelectionOnActivated() {
    if (!initialized.value) return
    keyword.value = ''
    expandedKeys.value = []
    selectedTreeKey.value = ALL_PROJECT_PRODUCTS_KEY
    const restored = restoreCachedSelection()
    if (!restored) selectAllProjectProducts()
  }

  function invalidateLoad(clear = false) {
    ++loadVersion
    pendingLoad = null
    needsLoad = true
    loading.value = false
    initialized.value = false
    if (clear) {
      keyword.value = ''
      expandedKeys.value = []
      selectedTreeKey.value = ALL_PROJECT_PRODUCTS_KEY
      moduleOptionsByProduct.value = {}
      loadFailed.value = false
    }
  }

  function loadNavigation(): Promise<void> {
    if (!available()) return Promise.resolve()
    if (pendingLoad?.version === loadVersion) return pendingLoad.promise
    const version = loadVersion, showModules = props.showModules
    const current = () => version === loadVersion && available()
    initialized.value = false
    loading.value = true
    loadFailed.value = false
    const promise = (async () => {
      try {
        await projectStore.projectProductName()
        if (!current()) return
        if (projectStore.optionErrors.products) throw new Error('项目加载失败')
        if (showModules) {
          const tree = await projectStore.getAllProductModuleTree()
          if (!current()) return
          if (projectStore.optionErrors.modules) throw new Error('模块加载失败')
          moduleOptionsByProduct.value = groupModuleTreeByProjectProduct(tree)
        }
        expandedKeys.value = []
        initialized.value = true
        needsLoad = false
        const restored = restoreCachedSelection()
        const fellBackToAll = restored ? false : validateCurrentSelection()
        if (!restored && !fellBackToAll && props.emitInitialFilter) emitFilter(null, null)
      } catch (loadFailure0) {
        if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
      } finally {
        if (current()) {
          loading.value = false
          pendingLoad = null
        }
      }
    })()
    pendingLoad = { version, promise }
    return promise
  }

  watch(() => [userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], () => {
    invalidateLoad(true)
    const version = loadVersion
    void Promise.resolve().then(() => {
      if (version !== loadVersion || !available()) return
      emitFilter(null, null)
      void loadNavigation()
    })
  }, { flush: 'sync' })

  function resume() {
    if (needsLoad) void loadNavigation()
    else syncSelectionOnActivated()
  }
  function onVisibilityChange() {
    if (document.hidden) invalidateLoad()
    else if (active) resume()
  }
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; invalidateLoad() })
  onMounted(() => {
    mounted = true
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisibilityChange)
    void loadNavigation()
  })
  onBeforeUnmount(() => {
    disposed = true
    invalidateLoad()
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibilityChange)
  })
</script>

<style lang="less" scoped>
  .mango-project-navigation-sidebar__product-description {
    max-width: min(360px, 70vw);
    max-height: 320px;
    overflow: auto;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.6;
  }

  .mango-project-navigation-sidebar {
    display: flex;
    width: 100%;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
    border-color: var(--m-border-strong);
    background: var(--m-surface);
  }

  .mango-project-navigation-sidebar--collapsed {
    align-items: center;
    padding: 8px 4px;
  }

  .mango-project-navigation-sidebar__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 10px;
    padding-bottom: 2px;
  }

  .mango-project-navigation-sidebar__heading {
    min-width: 0;
  }

  .mango-project-navigation-sidebar__collapse-button {
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
    padding: 0;
    color: var(--m-text-2);
  }

  .mango-project-navigation-sidebar__collapse-button:hover {
    color: var(--m-primary);
    background: var(--m-fill-2);
  }

  .mango-project-navigation-sidebar__heading h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-project-navigation-sidebar__heading p {
    margin: 2px 0 0;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 16px;
  }

  .mango-project-navigation-sidebar__search-panel {
    display: grid;
    gap: 7px;
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-project-navigation-sidebar__section-header {
    display: flex;
    min-height: 30px;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 7px 6px 4px;
    color: var(--m-muted);
    font-size: 11px;
    font-weight: 600;
    line-height: 18px;
  }

  .mango-project-navigation-sidebar__section-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 2px;
    white-space: nowrap;
  }

  .mango-project-navigation-sidebar__tree {
    flex: 1;
    min-height: 0;
    overflow: auto;
    scroll-padding-bottom: 24px;
    scrollbar-gutter: stable;
    scrollbar-color: var(--m-scrollbar-thumb) transparent;
    scrollbar-width: thin;
  }

  .mango-project-navigation-sidebar__tree::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  .mango-project-navigation-sidebar__tree::-webkit-scrollbar-track {
    background: transparent;
  }

  .mango-project-navigation-sidebar__tree::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: var(--m-scrollbar-thumb);
  }

  .mango-project-navigation-sidebar__tree::-webkit-scrollbar-thumb:hover {
    background: var(--m-scrollbar-thumb-hover);
  }

  .mango-project-navigation-sidebar__spin {
    width: 100%;
    min-width: 100%;
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree) {
    min-width: 100%;
    width: max-content;
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node-title) {
    min-height: 26px;
    display: flex;
    align-items: center;
    padding-top: 0;
    padding-right: 6px;
    padding-bottom: 0;
    padding-left: 6px;
    border-radius: var(--m-radius-sm);
    line-height: 20px;
    transition: color 0.16s ease, background-color 0.16s ease;
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node-title:hover) {
    color: var(--m-text);
    background: var(--m-surface-soft);
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node-selected .arco-tree-node-title),
  .mango-project-navigation-sidebar__tree
    :deep(.arco-tree-node-selected .arco-tree-node-title:hover) {
    color: var(--m-primary);
    background: transparent;
    box-shadow: none;
    font-weight: 500;
  }

  .mango-project-navigation-sidebar__tree
    :deep(.arco-tree-node-selected .mango-project-navigation-sidebar__switcher-icon) {
    color: var(--m-primary);
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node) {
    padding-top: 1px;
    padding-bottom: 1px;
  }

  .mango-project-navigation-sidebar__tree
    :deep(.arco-tree-node:has(.mango-project-navigation-sidebar__project-start)) {
    margin-top: 4px;
    padding-top: 5px;
    border-top: 1px dashed var(--m-border-strong);
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node-switcher) {
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-right: 2px;
    border-radius: var(--m-radius-sm);
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node-switcher:hover) {
    background: var(--m-fill-2);
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node-icon-hover),
  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node-switcher-icon) {
    width: 28px;
    height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .mango-project-navigation-sidebar__tree
    :deep(.arco-icon-hover.arco-tree-node-icon-hover::before) {
    width: 24px;
    height: 24px;
  }

  .mango-project-navigation-sidebar__tree
    :deep(.arco-tree-node-switcher-icon .mango-project-navigation-sidebar__switcher-icon) {
    color: var(--m-text-2);
    font-size: 13px;
    transform: rotate(0);
    transition: transform 0.16s ease;
  }

  .mango-project-navigation-sidebar__tree
    :deep(
      .arco-tree-node-expanded
        .arco-tree-node-switcher-icon
        .mango-project-navigation-sidebar__switcher-icon
    ) {
    transform: rotate(90deg);
  }

  .mango-project-navigation-sidebar__tree :deep(.arco-tree-node-title-text) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-project-navigation-sidebar__tree
    :deep(.arco-tree-node-disabled-selectable .arco-tree-node-title),
  .mango-project-navigation-sidebar__tree
    :deep(.arco-tree-node-disabled-selectable .arco-tree-node-title:hover) {
    color: var(--m-text-2);
    cursor: pointer;
  }

  .mango-project-navigation-sidebar__bottom-spacer {
    width: 1px;
    height: 32px;
  }
</style>
