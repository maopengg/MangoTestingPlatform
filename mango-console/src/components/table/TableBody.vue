<template>
  <a-card :bordered="false" class="mango-table-body">
    <div class="mango-table-body__header">
      <slot name="header"></slot>
    </div>
    <div class="mango-table-body__content">
      <slot name="default"></slot>
    </div>
    <div class="mango-table-body__footer">
      <slot name="footer"></slot>
    </div>
  </a-card>
</template>

<script lang="ts">
  import { defineComponent } from 'vue'

  export default defineComponent({
    name: 'TableBody',
  })
</script>

<style lang="less" scoped>
  .mango-table-body {
    display: flex;
    flex-direction: column;
    position: absolute;
    left: 6px;
    right: 6px;
    top: 4px;
    bottom: 55px;
    background: var(--m-surface);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    box-shadow: var(--m-shadow);
    overflow: hidden;
  }

  :deep(.arco-card-body) {
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

  .mango-table-body__header {
    padding: 4px 8px 0;
  }

  .mango-table-body__content {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    overflow-y: auto;
    padding: 0 8px 8px;

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

  .mango-table-body__footer {
    padding: 0 8px 8px;
  }
</style>
