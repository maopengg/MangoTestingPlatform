<template>
  <div class="mango-sticky-horizontal-table" :class="contentClass">
    <div class="mango-sticky-horizontal-table__region">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
  withDefaults(
    defineProps<{
      scrollX?: number | string
      contentClass?: string | string[] | Record<string, boolean>
    }>(),
    {
      scrollX: 0,
      contentClass: '',
    }
  )
</script>

<style scoped>
  .mango-sticky-horizontal-table,
  .mango-sticky-horizontal-table__region {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-sticky-horizontal-table__region :deep(.arco-table) {
    height: 100%;
    min-height: 0;
  }

  .mango-sticky-horizontal-table__region
    :deep(.arco-scrollbar.arco-scrollbar-type-embed .arco-scrollbar-thumb) {
    opacity: 0.9;
  }
</style>
