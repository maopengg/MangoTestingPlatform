<template>
  <component
    :is="plain ? 'div' : 'a-card'"
    :bordered="plain ? undefined : false"
    :class="[
      'mango-table-body',
      { 'mango-table-body--plain': plain },
      {
        'mango-table-body--embedded': embedded,
        'mango-table-body--embedded-page': embedded && showEmbeddedHeader,
      },
    ]"
  >
    <div v-if="!embedded || showEmbeddedHeader" class="mango-table-body__header">
      <slot name="header"></slot>
    </div>
    <slot v-if="embedded && !showEmbeddedHeader" name="default"></slot>
    <div
      v-else
      ref="contentRef"
      :class="[
        'mango-table-body__content',
        { 'mango-table-body__content--flush': contentFlush },
        { 'mango-table-body__content--sticky-horizontal-scroll': stickyHorizontalScroll },
      ]"
    >
      <slot name="default"></slot>
    </div>
    <div
      v-if="!embedded && stickyHorizontalScroll"
      v-show="horizontalScrollable"
      ref="bottomScrollRef"
      class="mango-table-body__horizontal-scroll"
      @scroll="onBottomScroll"
    >
      <div
        class="mango-table-body__horizontal-scroll-inner"
        :style="{ width: `${bottomScrollWidth}px` }"
      ></div>
    </div>
    <div v-if="!embedded" class="mango-table-body__footer">
      <slot name="footer"></slot>
    </div>
  </component>
</template>

<script lang="ts">
  import { defineComponent, nextTick, onBeforeUnmount, onMounted, onUpdated, ref } from 'vue'

  export default defineComponent({
    name: 'TableBody',
    props: {
      embedded: {
        type: Boolean,
        default: false,
      },
      plain: {
        type: Boolean,
        default: false,
      },
      showEmbeddedHeader: {
        type: Boolean,
        default: false,
      },
      stickyHorizontalScroll: {
        type: Boolean,
        default: false,
      },
      contentFlush: {
        type: Boolean,
        default: false,
      },
    },
    setup(props) {
      const contentRef = ref<HTMLElement | null>(null)
      const bottomScrollRef = ref<HTMLElement | null>(null)
      const bottomScrollWidth = ref(0)
      const horizontalScrollable = ref(false)

      let tableScrollTarget: HTMLElement | null = null
      let scrollSyncing = false
      let resizeObserver: ResizeObserver | null = null
      let mutationObserver: MutationObserver | null = null

      function getTableScrollTarget() {
        const content = contentRef.value
        if (!content || props.embedded || !props.stickyHorizontalScroll) return null
        const candidates = Array.from(
          content.querySelectorAll<HTMLElement>(
            '.arco-scrollbar-container, .arco-table-content, .arco-table-body'
          )
        ).filter(
          (target) =>
            target.scrollWidth > target.clientWidth &&
            !target.closest('.mango-sticky-horizontal-table') &&
            !target.closest('.mango-project-navigation-workbench')
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

      onMounted(() => {
        scheduleBind()
        if (contentRef.value) {
          resizeObserver = new ResizeObserver(scheduleBind)
          resizeObserver.observe(contentRef.value)
          mutationObserver = new MutationObserver(scheduleBind)
          mutationObserver.observe(contentRef.value, { childList: true, subtree: true })
        }
      })

      onUpdated(scheduleBind)

      onBeforeUnmount(() => {
        tableScrollTarget?.removeEventListener('scroll', onTableScroll)
        resizeObserver?.disconnect()
        mutationObserver?.disconnect()
      })

      return {
        contentRef,
        bottomScrollRef,
        bottomScrollWidth,
        horizontalScrollable,
        onBottomScroll,
      }
    },
  })
</script>

<style lang="less" scoped>
  .mango-table-body {
    display: flex;
    flex-direction: column;
    position: absolute;
    left: var(--m-page-inset-inline);
    right: var(--m-page-inset-inline);
    top: var(--m-page-inset-block-start);
    bottom: var(--m-page-footer-space);
    background: var(--m-surface);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    box-shadow: var(--m-shadow);
    overflow: hidden;
  }

  .mango-table-body--embedded {
    position: relative;
    inset: auto;
    width: 100%;
    height: 100%;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }

  .mango-table-body--embedded-page {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
  }

  :deep(> .arco-card-body) {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
    padding: 0;
  }

  .mango-table-body__header,
  .mango-table-body__footer {
    flex: none;
  }

  .mango-table-body__horizontal-scroll {
    flex: none;
    z-index: 5;
    overflow-x: auto;
    overflow-y: hidden;
    height: 12px;
    margin: 0 var(--m-space-sm);
    background: var(--m-surface);
    scrollbar-color: var(--m-scrollbar-thumb) transparent;
    scrollbar-width: thin;
  }

  .mango-table-body__horizontal-scroll::-webkit-scrollbar {
    height: 6px;
  }

  .mango-table-body__horizontal-scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .mango-table-body__horizontal-scroll::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: var(--m-scrollbar-thumb);
  }

  .mango-table-body__horizontal-scroll::-webkit-scrollbar-thumb:hover {
    background: var(--m-scrollbar-thumb-hover);
  }

  .mango-table-body__horizontal-scroll-inner {
    height: 1px;
  }

  .mango-table-body__header {
    padding: var(--m-page-inset-block-start) var(--m-space-sm) 0;
    background: var(--m-surface);
  }

  .mango-table-body__content {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    overflow-y: auto;
    padding: 0 var(--m-space-sm) var(--m-space-sm);
    background: var(--m-bg);

    &::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }

    &::-webkit-scrollbar-track {
      border-radius: 3px;
      background: var(--m-scrollbar-track);
    }

    &::-webkit-scrollbar-thumb {
      border-radius: 3px;
      background: var(--m-scrollbar-thumb);
    }
  }

  .mango-table-body__content--flush {
    padding-right: 0;
    padding-left: 0;
  }

  .mango-table-body__content--sticky-horizontal-scroll :deep(.arco-table-content),
  .mango-table-body__content--sticky-horizontal-scroll :deep(.arco-scrollbar-container) {
    scrollbar-width: none;
  }

  .mango-table-body__content--sticky-horizontal-scroll :deep(.arco-table-content)::-webkit-scrollbar,
  .mango-table-body__content--sticky-horizontal-scroll :deep(.arco-scrollbar-container)::-webkit-scrollbar {
    width: 0;
    height: 0;
  }

  .mango-table-body__content--sticky-horizontal-scroll :deep(.arco-scrollbar-track-direction-horizontal),
  .mango-table-body__content--sticky-horizontal-scroll :deep(.arco-scrollbar-thumb-direction-horizontal),
  .mango-table-body__content--sticky-horizontal-scroll :deep(.arco-scrollbar-track-direction-horizontal::after) {
    display: none !important;
    height: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
  }

  .mango-table-body__footer {
    padding: 0;
    background: var(--m-surface);
  }
</style>
