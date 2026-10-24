<template>
  <div
    class="mango-effectiveness-empty-state"
    :class="{ 'is-positive': positive }"
  >
    <span class="mango-effectiveness-empty-state__icon">
      <icon-check-circle v-if="positive" />
      <icon-info-circle v-else />
    </span>
    <div>
      <strong>{{ title }}</strong>
      <small v-if="description">{{ description }}</small>
    </div>
  </div>
</template>

<script setup lang="ts">
  withDefaults(
    defineProps<{
      title: string
      description?: string
      positive?: boolean
    }>(),
    {
      description: '',
      positive: false,
    }
  )
</script>

<style scoped>
  .mango-effectiveness-empty-state {
    display: flex;
    width: 100%;
    min-height: 150px;
    padding: 24px;
    align-items: center;
    justify-content: center;
    gap: 12px;
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    text-align: left;
  }

  .mango-effectiveness-empty-state__icon {
    display: inline-flex;
    width: 40px;
    height: 40px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--m-border);
    border-radius: 50%;
    background: var(--m-surface);
    color: var(--m-primary);
    font-size: 20px;
  }

  .mango-effectiveness-empty-state > div {
    display: flex;
    max-width: 420px;
    flex-direction: column;
    gap: 3px;
  }

  .mango-effectiveness-empty-state strong {
    color: var(--m-text);
    font-size: 14px;
    line-height: 20px;
  }

  .mango-effectiveness-empty-state small {
    color: var(--m-muted);
    font-size: 11px;
    line-height: 18px;
  }

  .mango-effectiveness-empty-state.is-positive {
    background: color-mix(in srgb, var(--m-success) 5%, var(--m-surface));
  }

  .mango-effectiveness-empty-state.is-positive .mango-effectiveness-empty-state__icon {
    border-color: color-mix(in srgb, var(--m-success) 24%, var(--m-border));
    color: var(--m-success);
  }
</style>
