<template>
  <div class="mango-table-actions">
    <a-button
      v-for="action in visibleInlineActions"
      :key="actionKey(action)"
      class="mango-table-action-btn"
      :class="{ 'mango-table-action-btn--danger': action.danger }"
      :disabled="action.disabled"
      :loading="action.loading"
      size="mini"
      :status="action.danger ? 'danger' : undefined"
      type="text"
      @click="handleClick(action)"
    >
      {{ action.label }}
    </a-button>
    <a-dropdown v-if="overflowActions.length" content-class="mango-table-actions-dropdown" trigger="hover">
      <a-button class="mango-table-action-more" size="mini" type="text">更多</a-button>
      <template #content>
        <a-doption
          v-for="action in overflowActions"
          :key="actionKey(action)"
          :disabled="action.disabled"
          @click="handleClick(action)"
        >
          <span
            class="mango-table-action-menu-item"
            :class="{ 'mango-table-action-menu-item--danger': action.danger }"
          >
            {{ action.label }}
          </span>
        </a-doption>
      </template>
    </a-dropdown>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  type MangoTableAction = {
    label: string
    onClick?: () => void
    danger?: boolean
    loading?: boolean
    disabled?: boolean
    hidden?: boolean
    priority?: number
  }

  const props = withDefaults(
    defineProps<{
      actions: MangoTableAction[]
      maxInline?: number
    }>(),
    {
      maxInline: 2,
    }
  )

  const normalizedActions = computed(() =>
    props.actions
      .filter((action) => !action.hidden)
      .map((action, index) => ({ ...action, priority: action.priority ?? index }))
      .sort((a, b) => (a.priority ?? 0) - (b.priority ?? 0))
  )

  const visibleInlineActions = computed(() => normalizedActions.value.slice(0, props.maxInline))
  const overflowActions = computed(() => normalizedActions.value.slice(props.maxInline))

  function actionKey(action: MangoTableAction) {
    return `${action.label}-${action.priority ?? ''}`
  }

  function handleClick(action: MangoTableAction) {
    if (action.disabled || action.loading) return
    action.onClick?.()
  }
</script>

<style scoped>
  .mango-table-actions {
    display: inline-flex;
    max-width: 100%;
    min-width: 0;
    align-items: center;
    justify-content: center;
    gap: 4px;
    white-space: nowrap;
  }

  .mango-table-action-btn {
    max-width: 64px;
  }

  .mango-table-action-btn :deep(.arco-btn-content) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-table-action-btn--danger,
  .mango-table-action-menu-item--danger {
    color: var(--m-danger);
  }

  .mango-table-action-more {
    padding: 0 4px;
  }

  .mango-table-action-menu-item {
    display: flex;
    min-width: 64px;
    width: 100%;
    align-items: center;
    justify-content: center;
    text-align: center;
  }

  :global(.mango-table-actions-dropdown .arco-dropdown-option) {
    padding-right: 12px;
    padding-left: 12px;
  }

  :global(.mango-table-actions-dropdown .arco-dropdown-option-content) {
    display: flex;
    width: 100%;
    justify-content: center;
    text-align: center;
  }
</style>
