<template>
  <div class="mango-task-recent-results">
    <a-skeleton v-if="loading" :animation="true" class="mango-task-recent-results__loading">
      <a-skeleton-line :rows="2" :widths="['58%', '88%']" />
    </a-skeleton>
    <div v-else-if="results.length" class="mango-task-recent-results__content">
      <div class="mango-task-recent-results__timeline" aria-label="最近执行结果">
        <a-tooltip v-for="(item, index) in results" :key="index" position="top">
          <template #content>
            <div class="mango-task-recent-results__tooltip">
              <strong>{{ index === 0 ? '最近一次' : `第 ${index + 1} 次` }} · {{ item.status_text }}</strong>
              <span>{{ item.test_env_text }} · {{ item.create_time || '-' }}</span>
              <span>用例 {{ item.total }} · 通过 {{ item.success }} · 失败 {{ item.fail }} · 警告 {{ item.warning }}</span>
              <span>最终通过率 {{ formatRate(item.pass_rate) }} · 耗时 {{ formatDuration(item.duration_ms) }}</span>
              <span v-if="'report_retained' in item && item.report_retained === false">执行成功，未保留完整报告</span>
            </div>
          </template>
          <button
            type="button"
            :class="[
              'mango-task-recent-results__point',
              `mango-task-recent-results__point--${item.status_key}`,
            ]"
            :aria-label="`打开${item.create_time || ''}${item.status_text}报告`"
            @click="emit('open', index)"
          >
            {{ statusSymbol(item.status_key) }}
          </button>
        </a-tooltip>
      </div>
      <div class="mango-task-recent-results__summary">
        <span :class="['mango-task-recent-results__status', `is-${results[0].status_key}`]">
          {{ results[0].status_text }}
        </span>
        <span>{{ formatRate(results[0].pass_rate) }}</span>
        <span>{{ resultSummary(results[0]) }}</span>
      </div>
    </div>
    <div v-else class="mango-empty-state mango-task-recent-results__empty">暂无执行记录</div>
  </div>
</template>

<script lang="ts" setup>
  import type { ExecutionQualityResult } from '@/api/system/tasks'

  defineProps<{
    results: ExecutionQualityResult[]
    loading?: boolean
  }>()

  const emit = defineEmits<{
    (event: 'open', index: number): void
  }>()

  function formatRate(value: number | null) {
    if (value === null || value === undefined) return '-'
    return `${Number(value).toFixed(2)}%`
  }

  function formatDuration(value: number) {
    if (!value) return '-'
    if (value < 1000) return `${value} ms`
    if (value < 60_000) return `${(value / 1000).toFixed(1)} 秒`
    return `${(value / 60_000).toFixed(1)} 分钟`
  }

  function resultSummary(item: ExecutionQualityResult) {
    if (!item.total && item.excluded_count) return `已排除 ${item.excluded_count} 个用例`
    if (!item.total) return '暂无用例明细'
    const parts = [`${item.total} 个用例`]
    if (item.fail) parts.push(`失败 ${item.fail}`)
    if (item.warning) parts.push(`警告 ${item.warning}`)
    if (item.excluded_count) parts.push(`排除 ${item.excluded_count}`)
    if (item.proceed) parts.push(`进行中 ${item.proceed}`)
    return parts.join(' · ')
  }

  function statusSymbol(status: ExecutionQualityResult['status_key']) {
    if (status === 'success') return '✓'
    if (status === 'fail') return '×'
    if (status === 'warning') return '!'
    if (status === 'proceed') return '↻'
    if (status === 'stopped') return '—'
    return '·'
  }
</script>

<style scoped>
  .mango-task-recent-results {
    min-width: 0;
  }

  .mango-task-recent-results__loading {
    width: 100%;
  }

  .mango-task-recent-results__content {
    display: grid;
    min-width: 0;
    gap: 5px;
  }

  .mango-task-recent-results__timeline {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .mango-task-recent-results__point {
    display: inline-flex;
    width: 22px;
    height: 22px;
    align-items: center;
    justify-content: center;
    flex: 0 0 22px;
    padding: 0;
    border: 1px solid currentColor;
    border-radius: 50%;
    background: var(--m-surface);
    color: var(--m-muted);
    cursor: pointer;
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
  }

  .mango-task-recent-results__point:hover {
    background: var(--m-surface-soft);
  }

  .mango-task-recent-results__point--success,
  .mango-task-recent-results__status.is-success {
    color: var(--m-success);
  }

  .mango-task-recent-results__point--fail,
  .mango-task-recent-results__status.is-fail {
    color: var(--m-danger);
  }

  .mango-task-recent-results__point--warning,
  .mango-task-recent-results__status.is-warning {
    color: var(--m-warning);
  }

  .mango-task-recent-results__point--proceed,
  .mango-task-recent-results__status.is-proceed {
    color: var(--m-primary);
  }

  .mango-task-recent-results__summary {
    display: flex;
    min-width: 0;
    align-items: center;
    padding: 0;
    border: 0;
    gap: 6px;
    background: transparent;
    color: var(--m-muted);
    font: inherit;
    font-size: 12px;
    text-align: left;
    white-space: nowrap;
  }

  .mango-task-recent-results__summary span:nth-child(3) {
    overflow: hidden;
    color: var(--m-text);
    text-overflow: ellipsis;
  }

  .mango-task-recent-results__status {
    flex: 0 0 auto;
    font-weight: 600;
  }

  .mango-task-recent-results__empty {
    min-height: 48px;
    border-radius: var(--m-radius-md);
    font-size: 12px;
  }

  .mango-task-recent-results__tooltip {
    display: grid;
    max-width: 360px;
    gap: 4px;
    font-size: 12px;
  }
</style>
