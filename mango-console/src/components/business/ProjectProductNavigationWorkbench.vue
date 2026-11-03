<template>
  <div
    class="mango-project-navigation-workbench"
    :class="{
      'mango-project-navigation-workbench--contained-body': containedBody,
      'mango-project-navigation-workbench--sticky-horizontal-scroll': stickyHorizontalScroll,
      'mango-project-navigation-workbench--navigation-collapsed': navigationCollapsed && !$slots.navigation,
      'mango-project-navigation-workbench--without-search': !showSearch || !$slots.search,
    }"
  >
    <div
      class="mango-project-navigation-workbench__inner"
      @transitionend="onWorkbenchTransitionEnd"
    >
      <slot name="navigation">
        <ProjectProductNavigationSidebar
        :model-value="modelValue"
        :module-value="moduleValue"
        :reset-key="resetKey"
        :show-modules="showModules"
        :emit-initial-filter="emitInitialFilter"
        :product-source="productSource"
        :title="navigationTitle"
        :description="navigationDescription"
        :collapsed="navigationCollapsed"
        @filter-change="onFilterChange"
        @toggle-collapse="toggleNavigation"
        />
      </slot>

      <section class="mango-project-navigation-workbench__main">
        <TableSearchPanel
          v-if="showSearch && $slots.search"
          class="mango-project-navigation-workbench__search"
          @search="emit('search')"
          @reset-search="emit('reset-search')"
        >
          <slot name="search"></slot>
        </TableSearchPanel>
        <div class="mango-project-navigation-workbench__content">
          <div v-if="$slots.tabs" class="mango-project-navigation-workbench__tabs">
            <slot name="tabs"></slot>
          </div>
          <TableTabs v-if="showToolbar && $slots.toolbar">
            <template #extra>
              <slot name="toolbar"></slot>
            </template>
          </TableTabs>
          <div ref="bodyRef" class="mango-project-navigation-workbench__body">
            <slot></slot>
          </div>
          <div
            v-if="stickyHorizontalScroll"
            v-show="horizontalScrollable"
            ref="bottomScrollRef"
            class="mango-project-navigation-workbench__horizontal-scroll"
            @scroll="onBottomScroll"
          >
            <div
              class="mango-project-navigation-workbench__horizontal-scroll-inner"
              :style="{ width: `${bottomScrollWidth}px` }"
            ></div>
          </div>
          <div v-if="$slots.footer" class="mango-project-navigation-workbench__footer">
            <slot name="footer"></slot>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { nextTick, onBeforeUnmount, onMounted, onUpdated, ref, watch } from 'vue'
  import ProjectProductNavigationSidebar from './ProjectProductNavigationSidebar.vue'
  import type { NavigationCreateSelection } from '@/utils/navigation-create-defaults'

  type NavigationFilter = {
    projectProduct: string | number | null
    module: string | number | null
    moduleIds?: Array<string | number>
    selectedModuleId?: string | number | null
  }

  const props = withDefaults(
    defineProps<{
      modelValue?: string | number | null
      moduleValue?: string | number | null
      resetKey?: number
      showModules?: boolean
      emitInitialFilter?: boolean
      showSearch?: boolean
      showToolbar?: boolean
      productSource?: 'default' | 'pytest'
      navigationTitle?: string
      navigationDescription?: string
      containedBody?: boolean
      stickyHorizontalScroll?: boolean
    }>(),
    {
      modelValue: null,
      moduleValue: null,
      resetKey: 0,
      showModules: false,
      emitInitialFilter: false,
      showSearch: true,
      showToolbar: true,
      productSource: 'default',
      navigationTitle: '',
      navigationDescription: '',
      containedBody: false,
      stickyHorizontalScroll: false,
    }
  )

  const emit = defineEmits<{
    (event: 'filter-change', filter: NavigationFilter): void
    (event: 'search'): void
    (event: 'reset-search'): void
  }>()

  const NAVIGATION_COLLAPSED_STORAGE_KEY = 'mango-project-navigation-collapsed'

  function readNavigationCollapsed() {
    if (typeof window === 'undefined') return false
    return window.sessionStorage.getItem(NAVIGATION_COLLAPSED_STORAGE_KEY) === 'true'
  }

  const bodyRef = ref<HTMLElement | null>(null)
  const bottomScrollRef = ref<HTMLElement | null>(null)
  const bottomScrollWidth = ref(0)
  const horizontalScrollable = ref(false)
  const navigationCollapsed = ref(readNavigationCollapsed())
  const createSelection = ref<NavigationCreateSelection | null>(null)

  defineExpose({
    getCreateDefaults: (): NavigationCreateSelection => ({
      projectProduct: createSelection.value ? createSelection.value.projectProduct : props.modelValue,
      module: props.showModules ? (createSelection.value ? createSelection.value.module : props.moduleValue) : null,
    }),
  })

  let tableScrollTarget: HTMLElement | null = null
  let scrollSyncing = false
  let resizeObserver: ResizeObserver | null = null
  let mutationObserver: MutationObserver | null = null

  function getTableScrollTarget() {
    const body = bodyRef.value
    if (!body || !props.stickyHorizontalScroll) return null
    const candidates = Array.from(
      body.querySelectorAll<HTMLElement>(
        '.arco-scrollbar-container, .arco-table-content, .arco-table-body'
      )
    ).filter(
      (target) =>
        target.scrollWidth > target.clientWidth && !target.closest('.mango-sticky-horizontal-table')
    )
    const scrollableTarget = candidates.find((target) => {
      const overflowX = window.getComputedStyle(target).overflowX
      return ['auto', 'scroll', 'overlay'].includes(overflowX)
    })
    return scrollableTarget || candidates[0] || null
  }

  function refreshBottomScrollState(target: HTMLElement | null) {
    horizontalScrollable.value = Boolean(target && target.scrollWidth > target.clientWidth)
    bottomScrollWidth.value = target?.scrollWidth || 0
  }

  function onTableScroll() {
    const bottomScroll = bottomScrollRef.value
    if (!bottomScroll || !tableScrollTarget || scrollSyncing) return
    scrollSyncing = true
    bottomScroll.scrollLeft = tableScrollTarget.scrollLeft
    scrollSyncing = false
  }

  function bindTableHorizontalScroll() {
    const target = getTableScrollTarget()
    if (target === tableScrollTarget) {
      refreshBottomScrollState(target)
      onTableScroll()
      return
    }
    tableScrollTarget?.removeEventListener('scroll', onTableScroll)
    tableScrollTarget = target
    refreshBottomScrollState(target)
    tableScrollTarget?.addEventListener('scroll', onTableScroll, { passive: true })
    onTableScroll()
  }

  function scheduleBind() {
    nextTick(bindTableHorizontalScroll)
  }

  function onBottomScroll() {
    if (!tableScrollTarget || !bottomScrollRef.value || scrollSyncing) return
    scrollSyncing = true
    tableScrollTarget.scrollLeft = bottomScrollRef.value.scrollLeft
    scrollSyncing = false
  }

  function toggleNavigation() {
    navigationCollapsed.value = !navigationCollapsed.value
    window.sessionStorage.setItem(
      NAVIGATION_COLLAPSED_STORAGE_KEY,
      String(navigationCollapsed.value)
    )
    scheduleBind()
  }

  function onWorkbenchTransitionEnd(event: TransitionEvent) {
    if (event.propertyName !== 'grid-template-columns') return
    scheduleBind()
    window.dispatchEvent(new Event('resize'))
  }

  onMounted(() => {
    scheduleBind()
    if (bodyRef.value) {
      resizeObserver = new ResizeObserver(scheduleBind)
      resizeObserver.observe(bodyRef.value)
      mutationObserver = new MutationObserver(scheduleBind)
      mutationObserver.observe(bodyRef.value, { childList: true, subtree: true })
    }
  })

  onUpdated(scheduleBind)
  watch(() => props.stickyHorizontalScroll, scheduleBind)

  onBeforeUnmount(() => {
    tableScrollTarget?.removeEventListener('scroll', onTableScroll)
    resizeObserver?.disconnect()
    mutationObserver?.disconnect()
  })

  function onFilterChange(filter: NavigationFilter) {
    createSelection.value = { projectProduct: filter.projectProduct, module: filter.module }
    emit('filter-change', filter)
  }
</script>

<style lang="less" scoped>
  .mango-project-navigation-workbench {
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    padding-top: var(--m-page-gap);
    box-sizing: border-box;
  }

  .mango-project-navigation-workbench__inner {
    display: grid;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    grid-template-columns: 240px minmax(0, 1fr);
    gap: var(--m-page-gap);
    transition: grid-template-columns 0.18s ease;
  }

  .mango-project-navigation-workbench--navigation-collapsed
    .mango-project-navigation-workbench__inner {
    grid-template-columns: 44px minmax(0, 1fr);
  }

  .mango-project-navigation-workbench__main {
    display: grid;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    border: 1px solid var(--m-border-strong);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    grid-template-rows: auto minmax(0, 1fr);
  }

  .mango-project-navigation-workbench--without-search .mango-project-navigation-workbench__main {
    grid-template-rows: minmax(0, 1fr);
  }

  .mango-project-navigation-workbench__search {
    align-self: start;
    width: 100%;
    min-width: 0;
    padding: 4px 6px;
    box-sizing: border-box;
  }

  .mango-project-navigation-workbench__content {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-project-navigation-workbench__footer {
    flex: none;
  }

  .mango-project-navigation-workbench__horizontal-scroll {
    flex: none;
    z-index: 5;
    overflow-x: auto;
    overflow-y: hidden;
    height: 12px;
    background: var(--m-surface);
    scrollbar-color: var(--m-scrollbar-thumb) transparent;
    scrollbar-width: thin;
  }

  .mango-project-navigation-workbench__horizontal-scroll::-webkit-scrollbar {
    height: 6px;
  }

  .mango-project-navigation-workbench__horizontal-scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .mango-project-navigation-workbench__horizontal-scroll::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: var(--m-scrollbar-thumb);
  }

  .mango-project-navigation-workbench__horizontal-scroll::-webkit-scrollbar-thumb:hover {
    background: var(--m-scrollbar-thumb-hover);
  }

  .mango-project-navigation-workbench__horizontal-scroll-inner {
    height: 1px;
  }

  .mango-project-navigation-workbench__tabs {
    flex: none;
    width: 100%;
    min-width: 0;
    overflow: hidden;
  }

  .mango-project-navigation-workbench__body {
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior-y: contain;
    scrollbar-color: var(--m-scrollbar-thumb) transparent;
    scrollbar-width: thin;
  }

  .mango-project-navigation-workbench--contained-body .mango-project-navigation-workbench__body {
    display: flex;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-project-navigation-workbench--sticky-horizontal-scroll
    .mango-project-navigation-workbench__body
    :deep(.arco-table-content),
  .mango-project-navigation-workbench--sticky-horizontal-scroll
    .mango-project-navigation-workbench__body
    :deep(.arco-scrollbar-container) {
    scrollbar-width: none;
  }

  .mango-project-navigation-workbench--sticky-horizontal-scroll
    .mango-project-navigation-workbench__body
    :deep(.arco-table-content)::-webkit-scrollbar,
  .mango-project-navigation-workbench--sticky-horizontal-scroll
    .mango-project-navigation-workbench__body
    :deep(.arco-scrollbar-container)::-webkit-scrollbar {
    width: 0;
    height: 0;
  }

  .mango-project-navigation-workbench--sticky-horizontal-scroll
    .mango-project-navigation-workbench__body
    :deep(.arco-scrollbar-track-direction-horizontal),
  .mango-project-navigation-workbench--sticky-horizontal-scroll
    .mango-project-navigation-workbench__body
    :deep(.arco-scrollbar-thumb-direction-horizontal),
  .mango-project-navigation-workbench--sticky-horizontal-scroll
    .mango-project-navigation-workbench__body
    :deep(.arco-scrollbar-track-direction-horizontal::after) {
    display: none !important;
    height: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
  }

  .mango-project-navigation-workbench__body::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  .mango-project-navigation-workbench__body::-webkit-scrollbar-track {
    background: transparent;
  }

  .mango-project-navigation-workbench__body::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: var(--m-scrollbar-thumb);
  }

  .mango-project-navigation-workbench__footer {
    border-top: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .mango-project-navigation-workbench :deep(.mango-project-navigation-sidebar) {
    height: 100%;
    max-height: 100%;
  }
</style>
