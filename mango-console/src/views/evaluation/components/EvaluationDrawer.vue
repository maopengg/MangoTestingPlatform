<template>
  <a-drawer
    class="mango-evaluation-side-panel"
    :body-class="['mango-evaluation-side-panel__body', { 'mango-evaluation-side-panel__body--contained': contained }]"
    :width="width"
    :footer="footer"
    unmount-on-close
  >
    <template v-for="(_, name) in $slots" #[name]="slotProps">
      <slot :name="name" v-bind="slotProps || {}" />
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
  withDefaults(defineProps<{ width?: string | number; contained?: boolean; footer?: boolean }>(), {
    width: 900,
    contained: false,
    footer: false,
  })
</script>

<style scoped>
  :global(.mango-evaluation-side-panel__body) {
    box-sizing: border-box;
    min-width: 0;
    min-height: 0;
    padding: var(--m-page-gap);
    overflow: auto;
    container-type: inline-size;
  }
  :global(.mango-evaluation-side-panel__body--contained) {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
</style>
