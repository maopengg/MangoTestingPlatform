<template>
  <a-trigger
    v-if="active"
    :trigger="['hover', 'focus']"
    :popup-visible="popupVisible"
    @popup-visible-change="setPopupVisible"
    :position="position"
    :mouse-enter-delay="delay"
    :focus-delay="delay"
    :mouse-leave-delay="100"
    :popup-offset="scaleDensityPixels(10)"
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
  import { onActivated, onBeforeUnmount, onDeactivated, ref } from 'vue'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  const popupVisible = ref(false)
  const active = ref(true)
  function setPopupVisible(value: boolean) { popupVisible.value = active.value && value }
  function stopPopup() { active.value = false; popupVisible.value = false }
  onActivated(() => { active.value = true })
  onDeactivated(stopPopup)
  onBeforeUnmount(stopPopup)
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
    max-width: calc(100vw - 32px);
    max-height: min(420px, calc(100vh - 32px));
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
