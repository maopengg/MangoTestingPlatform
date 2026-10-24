<template>
  <TableHeader class="mango-table-search-panel" :show-search-actions="false">
    <template #search-content>
      <div ref="contentRef" class="mango-table-search-panel__content" :style="gridStyle">
        <slot></slot>
        <TableSearchActions @search="emit('search')" @reset="emit('reset-search')" />
      </div>
    </template>
  </TableHeader>
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import TableSearchActions from './TableSearchActions.vue'
  import { displayDensityScale, scaleDensityPixels } from '@/hooks/useDisplayDensity'

  const MIN_CELL_WIDTH = 210
  const MAX_CELL_WIDTH = 250
  const LABEL_WIDTH = 70
  const BASE_GAP = 8

  const contentRef = ref<HTMLElement>()
  const columnCount = ref(1)
  const cellWidth = ref(230)
  const columnGap = ref(BASE_GAP)
  let resizeObserver: ResizeObserver | undefined

  const gridStyle = computed(() => ({
    '--mango-table-search-column-count': String(columnCount.value),
    '--mango-table-search-cell-width': `${cellWidth.value}px`,
    '--mango-table-search-column-gap': `${columnGap.value}px`,
    '--table-filter-item-width': `${cellWidth.value}px`,
    '--table-filter-control-width': `${Math.max(
      0,
      cellWidth.value - scaleDensityPixels(LABEL_WIDTH)
    )}px`,
  }))

  const updateGrid = (width: number) => {
    if (width <= 0) return

    const minCellWidth = scaleDensityPixels(MIN_CELL_WIDTH)
    const maxCellWidth = scaleDensityPixels(MAX_CELL_WIDTH)
    const baseGap = scaleDensityPixels(BASE_GAP)
    const count = Math.max(1, Math.floor((width + baseGap) / (minCellWidth + baseGap)))
    const availableCellWidth = (width - baseGap * (count - 1)) / count
    const nextCellWidth = Math.min(
      maxCellWidth,
      Math.max(width < minCellWidth ? width : minCellWidth, availableCellWidth)
    )
    const nextGap =
      count > 1 && availableCellWidth > maxCellWidth
        ? (width - maxCellWidth * count) / (count - 1)
        : baseGap

    columnCount.value = count
    cellWidth.value = Math.round(nextCellWidth * 100) / 100
    columnGap.value = Math.round(nextGap * 100) / 100
  }

  onMounted(() => {
    if (!contentRef.value) return
    updateGrid(contentRef.value.clientWidth)
    resizeObserver = new ResizeObserver(([entry]) => updateGrid(entry.contentRect.width))
    resizeObserver.observe(contentRef.value)
  })

  onBeforeUnmount(() => resizeObserver?.disconnect())

  watch(displayDensityScale, () => {
    if (contentRef.value) updateGrid(contentRef.value.clientWidth)
  })

  const emit = defineEmits<{
    (event: 'search'): void
    (event: 'reset-search'): void
  }>()
</script>

<style lang="less" scoped>
  .mango-table-search-panel :deep(.mango-table-header__card) {
    border: 0;
    background: transparent;
  }

  .mango-table-search-panel,
  .mango-table-search-panel :deep(.mango-table-header),
  .mango-table-search-panel :deep(.mango-table-header__card) {
    height: auto;
    min-height: 0;
  }

  .mango-table-search-panel :deep(.arco-card-header) {
    min-height: 32px;
    padding: 2px 4px;
    border-bottom: 0;
  }

  .mango-table-search-panel :deep(.arco-card-body) {
    padding: 4px;
  }

  .mango-table-search-panel__content {
    display: grid;
    width: 100%;
    min-width: 0;
    grid-template-columns: repeat(
      var(--mango-table-search-column-count),
      var(--mango-table-search-cell-width)
    );
    column-gap: var(--mango-table-search-column-gap);
    row-gap: 8px;
    align-items: start;
  }

  .mango-table-search-panel__content :deep(.arco-form-layout-inline),
  .mango-table-search-panel__content :deep(.arco-form-inline) {
    display: contents !important;
  }

  .mango-table-search-panel__content :deep(.mango-table-search-actions) {
    grid-row: 1;
    grid-column: -2 / -1;
    width: var(--mango-table-search-cell-width);
    align-self: start;
    justify-content: flex-end;
  }
</style>
