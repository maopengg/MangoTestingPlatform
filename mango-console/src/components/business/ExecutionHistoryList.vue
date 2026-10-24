<template>
  <section class="mango-execution-history-list">
    <div class="mango-execution-history-list__head">
      <strong>执行记录</strong>
      <span>{{ items.length }} 条</span>
    </div>
    <mango-panel-spin :loading="loading" class="mango-execution-history-list__spin">
      <div class="mango-execution-history-list__body mango-native-scrollbar">
        <a-empty
          v-if="!items.length"
          :description="emptyText"
          class="mango-execution-history-list__empty"
        />
        <template v-else>
          <button
            v-for="item in items"
            :key="item.id"
            v-memo="[
              item.title,
              item.statusText,
              item.time,
              item.actor,
              item.latest,
              item.sourceText,
              item.statusColor,
              String(selectedId) === String(item.id),
            ]"
            type="button"
            class="mango-execution-history-list__item"
            :class="[
              `mango-execution-history-list__item--${statusTone(item.statusColor)}`,
              { active: String(selectedId) === String(item.id) },
            ]"
            @click="emit('select', item.id)"
          >
            <span class="mango-execution-history-list__item-head">
              <span class="mango-execution-history-list__item-title">
                <a-tag :color="item.statusColor || 'gray'" size="small">
                  {{ item.statusText || '未知' }}
                </a-tag>
                <strong :title="item.sourceText || item.title">
                  {{ item.sourceText || item.title }}
                </strong>
              </span>
              <a-tag v-if="item.latest" color="arcoblue" size="small">最近</a-tag>
            </span>
            <span class="mango-execution-history-list__item-meta">
              <small>{{ item.time || '-' }}</small>
              <small v-if="item.actor" class="mango-execution-history-list__actor">
                {{ item.actor }}
              </small>
            </span>
          </button>
        </template>
      </div>
    </mango-panel-spin>
  </section>
</template>

<script lang="ts" setup>
  import type { ExecutionHistoryItem } from './execution-history'

  withDefaults(
    defineProps<{
      items: ExecutionHistoryItem[]
      selectedId?: number | string
      loading?: boolean
      emptyText?: string
    }>(),
    {
      selectedId: '',
      loading: false,
      emptyText: '暂无执行结果',
    }
  )

  const emit = defineEmits<{
    (event: 'select', id: number | string): void
  }>()

  function statusTone(color?: string) {
    const value = String(color || '').toLocaleLowerCase()
    if (value === 'green') return 'success'
    if (value === 'red') return 'danger'
    if (value === 'orange' || value === 'gold') return 'warning'
    if (value === 'arcoblue' || value === 'blue') return 'running'
    return 'neutral'
  }
</script>

<style scoped>
  .mango-execution-history-list {
    display: flex;
    min-height: 0;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
    overflow: hidden;
  }

  .mango-execution-history-list__head {
    display: flex;
    flex: 0 0 auto;
    align-items: baseline;
    gap: 8px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-execution-history-list__head strong {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
  }

  .mango-execution-history-list__head span,
  .mango-execution-history-list__item small {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-execution-history-list__spin {
    display: block;
    min-height: 0;
    flex: 1;
    overflow: hidden;
  }

  :deep(.mango-execution-history-list__spin > .arco-spin),
  :deep(.mango-execution-history-list__spin > .mango-panel-spin__content) {
    display: block;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-execution-history-list__body {
    height: 100%;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .mango-execution-history-list__empty {
    margin-top: 96px;
  }

  .mango-execution-history-list__item {
    --mango-history-tone: var(--m-primary);

    display: flex;
    width: 100%;
    flex-direction: column;
    gap: 8px;
    padding: 11px 12px;
    border: 0;
    border-bottom: 1px solid var(--m-border);
    background: color-mix(in srgb, var(--mango-history-tone) 3%, var(--m-surface));
    color: var(--m-text);
    cursor: pointer;
    text-align: left;
    transition: background var(--m-motion-duration-fast), box-shadow var(--m-motion-duration-fast);
  }

  .mango-execution-history-list__item:hover {
    background: color-mix(in srgb, var(--mango-history-tone) 7%, var(--m-surface));
  }

  .mango-execution-history-list__item:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }

  .mango-execution-history-list__item.active {
    position: relative;
    background: color-mix(in srgb, var(--mango-history-tone) 11%, var(--m-surface));
    box-shadow: inset 3px 0 0 var(--mango-history-tone);
  }

  .mango-execution-history-list__item--success {
    --mango-history-tone: var(--m-success);
  }

  .mango-execution-history-list__item--danger {
    --mango-history-tone: var(--m-danger);
  }

  .mango-execution-history-list__item--warning {
    --mango-history-tone: var(--m-warning);
  }

  .mango-execution-history-list__item--running {
    --mango-history-tone: var(--m-primary);
  }

  .mango-execution-history-list__item--neutral {
    --mango-history-tone: var(--m-border-strong);
  }

  .mango-execution-history-list__item-head,
  .mango-execution-history-list__item-meta {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    gap: 8px;
  }

  .mango-execution-history-list__item-meta {
    flex-wrap: wrap;
  }

  .mango-execution-history-list__item-meta small:first-child {
    white-space: nowrap;
  }

  .mango-execution-history-list__actor {
    margin-left: auto;
  }

  .mango-execution-history-list__item-title {
    display: flex;
    flex: 1;
    min-width: 0;
    align-items: center;
    gap: 6px;
  }

  .mango-execution-history-list__item-title strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
