<template>
  <section class="api-case-panel api-case-right" :class="{ 'api-case-edit-locked': editLocked }">
    <div class="api-case-panel-head">
      <div>
        <div class="api-case-panel-title">
          <span>场景扩展</span>
          <a-tag
            v-if="latestExecutionLabel"
            class="api-case-latest-time-tag"
            :color="resultOutdated ? 'orange' : 'arcoblue'"
            size="small"
          >
            {{ latestExecutionLabel }}
          </a-tag>
        </div>
        <div class="api-case-panel-subtitle">{{ summary }}</div>
      </div>
      <a-space class="api-case-panel-actions">
        <a-button
          size="small"
          type="primary"
          :disabled="editLocked"
          data-testid="qa-views-apitest-case-details-button-增加场景"
          @click="$emit('add')"
        >
          增加场景
        </a-button>
        <a-button size="small" type="outline" @click="$emit('toggle-size')">
          {{ expanded ? '缩小' : '放大' }}
        </a-button>
      </a-space>
    </div>
    <div class="api-case-panel-body">
      <slot></slot>
    </div>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    editLocked: boolean
    latestExecutionLabel: string
    resultOutdated: boolean
    summary: string
    expanded: boolean
  }>()

  defineEmits<{
    (event: 'add'): void
    (event: 'toggle-size'): void
  }>()
</script>

<style scoped>
  .api-case-panel {
    display: flex;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .api-case-panel-head {
    display: flex;
    min-height: 58px;
    padding: 10px 12px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .api-case-panel-head > div:first-child {
    min-width: 0;
    flex: 1;
  }

  .api-case-panel-title {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .api-case-latest-time-tag {
    max-width: 260px;
    overflow: hidden;
    flex: 0 1 auto;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-case-panel-subtitle {
    overflow: hidden;
    max-width: 680px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-case-panel-actions {
    flex: none;
    white-space: nowrap;
  }

  .api-case-panel-body {
    min-height: 0;
    overflow: auto;
    flex: 1;
  }
</style>
