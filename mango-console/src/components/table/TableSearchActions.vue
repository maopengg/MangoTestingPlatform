<template>
  <div class="mango-table-search-actions">
    <a-button
      size="small"
      type="primary"
      data-testid="qa-components-table-tablesearchactions-button-search"
      @click="emit('search')"
    >
      搜索
    </a-button>
    <a-button
      size="small"
      data-testid="qa-components-table-tablesearchactions-button-reset"
      @click="emit('reset')"
    >
      重置
    </a-button>
  </div>
</template>

<script lang="ts" setup>
  const emit = defineEmits<{
    (event: 'search'): void
    (event: 'reset'): void
  }>()
</script>

<style lang="less" scoped>
  .mango-table-search-actions {
    display: flex;
    width: 100%;
    min-width: 0;
    min-height: 30px;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
  }
</style>
