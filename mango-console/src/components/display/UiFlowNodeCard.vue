<template>
  <div
    :class="[
      'mango-ui-flow-node',
      `mango-ui-flow-node--${statusKey}`,
      { 'mango-ui-flow-node--selected': selected },
    ]"
    :style="{ '--node-color': color || 'var(--m-primary)' }"
  >
    <slot name="before"></slot>
    <slot name="actions"></slot>

    <div class="mango-ui-flow-node__main">
      <div class="mango-ui-flow-node__kicker">
        <span class="mango-ui-flow-node__type" :title="typeText">
          <span class="mango-ui-flow-node__dot"></span>
          {{ typeText }}
        </span>
        <span class="mango-ui-flow-node__badges">
          <span
            v-for="(badge, index) in badges"
            :key="`${badge.label}-${index}`"
            :title="badge.title || badge.label"
            :class="[
              'mango-ui-flow-node__badge',
              `mango-ui-flow-node__badge--${badge.tone || 'ready'}`,
            ]"
          >
            <span class="mango-ui-flow-node__dot"></span>
            {{ badge.label }}
          </span>
        </span>
      </div>
      <div class="mango-ui-flow-node__title" :title="title">{{ title }}</div>
      <div class="mango-ui-flow-node__meta">
        <span>{{ operationLabel }}</span>
        <strong :title="operation">{{ operation }}</strong>
      </div>
    </div>

    <slot name="after"></slot>
  </div>
</template>

<script lang="ts" setup>
  import type { UiFlowNodeBadge, UiFlowNodeTone } from './ui-flow'

  withDefaults(
    defineProps<{
      typeText: string
      title: string
      operation: string
      operationLabel?: string
      statusKey?: UiFlowNodeTone
      badges?: UiFlowNodeBadge[]
      color?: string
      selected?: boolean
    }>(),
    {
      operationLabel: '方法',
      statusKey: 'ready',
      badges: () => [],
      color: 'var(--m-primary)',
      selected: false,
    }
  )
</script>

<style scoped>
  .mango-ui-flow-node {
    position: relative;
    width: 208px;
    min-height: 88px;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-left: 4px solid var(--node-color, var(--m-primary));
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
    cursor: pointer;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  }

  .mango-ui-flow-node:hover {
    border-color: var(--node-color, var(--m-primary));
    transform: translateY(-1px);
  }

  .mango-ui-flow-node--selected {
    border-color: var(--node-color, var(--m-primary));
    border-left-width: 6px;
    background: color-mix(in srgb, var(--node-color, var(--m-primary)) 8%, var(--m-surface));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--node-color, var(--m-primary)) 18%, transparent),
      var(--m-shadow);
    transform: translateY(-1px);
  }

  .mango-ui-flow-node--unsaved {
    border-color: color-mix(in srgb, var(--m-muted) 58%, var(--m-border));
  }

  .mango-ui-flow-node--isolated,
  .mango-ui-flow-node--warning,
  .mango-ui-flow-node--pending {
    border-color: color-mix(in srgb, var(--m-warning) 64%, var(--m-border));
  }

  .mango-ui-flow-node--ready {
    border-color: color-mix(in srgb, var(--m-success) 22%, var(--m-border));
  }

  .mango-ui-flow-node--passed {
    border-color: color-mix(in srgb, var(--m-success) 58%, var(--m-border));
    background: color-mix(in srgb, var(--m-success) 7%, var(--m-surface));
  }

  .mango-ui-flow-node--running {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--m-primary) 14%, transparent), var(--m-shadow);
  }

  .mango-ui-flow-node--failed {
    border-color: var(--m-danger);
    background: color-mix(in srgb, var(--m-danger) 7%, var(--m-surface));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--m-danger) 14%, transparent), var(--m-shadow);
  }

  .mango-ui-flow-node__main {
    min-width: 0;
  }

  .mango-ui-flow-node__kicker {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    margin-bottom: 2px;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 15px;
    white-space: nowrap;
  }

  .mango-ui-flow-node__type {
    display: flex;
    min-width: 55px;
    flex: 1 1 auto;
    align-items: center;
    gap: 5px;
    overflow: hidden;
    color: var(--node-color, var(--m-primary));
    font-weight: 600;
    text-overflow: ellipsis;
  }

  .mango-ui-flow-node__dot {
    flex: none;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }

  .mango-ui-flow-node__badges {
    display: flex;
    min-width: 0;
    flex: 0 1 auto;
    align-items: center;
    gap: 3px;
    overflow: hidden;
  }

  .mango-ui-flow-node__badge {
    display: flex;
    min-height: 20px;
    flex: none;
    align-items: center;
    gap: 3px;
    padding: 1px 4px;
    color: var(--m-muted);
    font-size: 11px;
    font-weight: 600;
    line-height: 16px;
    border: 1px solid var(--m-border);
    border-radius: 999px;
    background: var(--m-surface-soft);
  }

  .mango-ui-flow-node__badge--ready {
    color: var(--m-text);
  }

  .mango-ui-flow-node__badge--isolated,
  .mango-ui-flow-node__badge--warning,
  .mango-ui-flow-node__badge--pending {
    color: var(--m-warning);
    border-color: color-mix(in srgb, var(--m-warning) 28%, var(--m-border));
    background: color-mix(in srgb, var(--m-warning) 10%, var(--m-surface));
  }

  .mango-ui-flow-node__badge--unsaved {
    color: var(--m-muted);
    border-color: color-mix(in srgb, var(--m-muted) 28%, var(--m-border));
    background: color-mix(in srgb, var(--m-muted) 8%, var(--m-surface));
  }

  .mango-ui-flow-node__badge--passed {
    color: var(--m-success);
    border-color: color-mix(in srgb, var(--m-success) 28%, var(--m-border));
    background: color-mix(in srgb, var(--m-success) 10%, var(--m-surface));
  }

  .mango-ui-flow-node__badge--running {
    color: var(--m-primary);
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    background: color-mix(in srgb, var(--m-primary) 10%, var(--m-surface));
  }

  .mango-ui-flow-node__badge--failed {
    color: var(--m-danger);
    border-color: color-mix(in srgb, var(--m-danger) 28%, var(--m-border));
    background: color-mix(in srgb, var(--m-danger) 10%, var(--m-surface));
  }

  .mango-ui-flow-node__title {
    margin: 6px 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-flow-node__meta {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr);
    min-width: 0;
    gap: 6px;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 16px;
  }

  .mango-ui-flow-node__meta strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  @media (prefers-reduced-motion: reduce) {
    .mango-ui-flow-node {
      transition: none;
    }
  }
</style>
