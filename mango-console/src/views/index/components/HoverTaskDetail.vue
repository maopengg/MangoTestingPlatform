<template>
  <a-trigger
    :trigger="['hover', 'focus']"
    :position="position"
    :mouse-enter-delay="delay"
    :focus-delay="delay"
    :mouse-leave-delay="100"
    :popup-offset="10"
    auto-fit-position
    update-at-scroll
  >
    <div class="mango-task-hover-trigger">
      <slot></slot>
    </div>
    <template #content>
      <div class="mango-task-hover-detail mango-native-scrollbar">
        <slot name="content"></slot>
      </div>
    </template>
  </a-trigger>
</template>

<script lang="ts" setup>
  withDefaults(
    defineProps<{
      delay?: number
      position?:
        | 'top'
        | 'bottom'
        | 'left'
        | 'right'
        | 'tl'
        | 'tr'
        | 'bl'
        | 'br'
        | 'lt'
        | 'lb'
        | 'rt'
        | 'rb'
    }>(),
    {
      delay: 1000,
      position: 'left',
    }
  )
</script>

<style lang="less" scoped>
  .mango-task-hover-detail {
    width: 400px;
    max-height: 420px;
    padding: 12px;
    overflow-y: auto;
    border: 1px solid var(--m-border-strong);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
    color: var(--m-text);
  }
</style>

<style lang="less">
  .mango-task-hover-trigger {
    display: block;
    width: 100%;
  }

  .mango-hover-task-row {
    cursor: default;
    transition: background-color 0.2s ease, box-shadow 0.2s ease;
  }

  .mango-hover-task-row.mango-hover-task-row:hover,
  .mango-hover-task-row.mango-hover-task-row:focus-visible {
    outline: none;
    background: var(--m-primary-soft);
    box-shadow: inset 3px 0 0 var(--m-primary);
  }
</style>
