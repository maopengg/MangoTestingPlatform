<template>
  <span
    v-if="value !== null && value !== undefined && value !== ''"
    class="mango-menu-status-badge"
    role="status"
    :title="value === 'Beta' ? '功能仍在完善中' : String(value)"
  >
    {{ value }}
  </span>
</template>

<script lang="ts" setup>
  defineProps<{
    value?: string | number | null
  }>()
</script>

<style scoped>
  .mango-menu-status-badge {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    min-width: 25px;
    height: 14px;
    margin-right: 2px;
    padding: 0 4px;
    box-sizing: border-box;
    border: 1px solid color-mix(in srgb, var(--m-warning) 34%, transparent);
    border-radius: 7px;
    background: color-mix(in srgb, var(--m-warning) 12%, transparent);
    color: var(--m-warning);
    font-size: 11px;
    font-weight: 600;
    line-height: 12px;
    overflow: visible;
    white-space: nowrap;
  }
</style>
