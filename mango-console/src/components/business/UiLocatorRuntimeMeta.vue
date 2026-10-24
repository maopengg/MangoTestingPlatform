<template>
  <div class="mango-locator-runtime-meta" :class="{ 'is-empty': !hasRuntimeData }">
    <template v-if="hasRuntimeData">
      <a-tag v-if="matchCount !== null" size="small" :color="matchColor">
        最近匹配 {{ matchCount }}
      </a-tag>
      <a-tag
        v-if="runtimeData.visible !== null && runtimeData.visible !== undefined"
        size="small"
        :color="runtimeData.visible ? 'green' : 'red'"
      >
        {{ runtimeData.visible ? '可见' : '不可见' }}
      </a-tag>
      <a-tag
        v-if="runtimeData.enabled !== null && runtimeData.enabled !== undefined"
        size="small"
        :color="runtimeData.enabled ? 'green' : 'red'"
      >
        {{ runtimeData.enabled ? '可操作' : '不可操作' }}
      </a-tag>
      <span v-if="durationText">定位 {{ durationText }}</span>
      <a-tooltip v-if="elementText" :content="elementText">
        <span class="mango-locator-runtime-meta__text">文本摘要 {{ elementText }}</span>
      </a-tooltip>
      <span v-if="runtimeTime">检测时间 {{ runtimeTime }}</span>
    </template>
    <span v-else>暂无最近检测数据</span>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  const props = withDefaults(
    defineProps<{
      data?: Record<string, any> | null
      fallbackMatchCount?: number | string | null
      fallbackText?: string | null
      runtimeTime?: string | null
    }>(),
    {
      data: null,
      fallbackMatchCount: null,
      fallbackText: '',
      runtimeTime: '',
    }
  )

  const runtimeData = computed(() => props.data || {})
  const matchCount = computed(() => {
    const value = runtimeData.value.count ?? props.fallbackMatchCount
    if (value === null || value === undefined || value === '') return null
    const count = Number(value)
    return Number.isFinite(count) ? count : null
  })
  const elementText = computed(() =>
    String(runtimeData.value.element_text || props.fallbackText || '').trim()
  )
  const durationText = computed(() => {
    const duration = Number(runtimeData.value.duration_ms)
    if (!Number.isFinite(duration)) return ''
    if (duration >= 1000) return `${(duration / 1000).toFixed(duration >= 10000 ? 1 : 2)} 秒`
    return `${Math.max(0, Math.round(duration))} ms`
  })
  const matchColor = computed(() => {
    if (matchCount.value === 1) return 'green'
    if (matchCount.value === 0) return 'red'
    return 'orange'
  })
  const hasRuntimeData = computed(
    () =>
      matchCount.value !== null ||
      Boolean(elementText.value) ||
      Boolean(durationText.value) ||
      (runtimeData.value.visible !== null && runtimeData.value.visible !== undefined) ||
      (runtimeData.value.enabled !== null && runtimeData.value.enabled !== undefined)
  )
</script>

<style scoped>
  .mango-locator-runtime-meta {
    display: flex;
    align-items: center;
    min-width: 0;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed var(--m-border);
    color: var(--m-text-3);
    font-size: 12px;
  }

  .mango-locator-runtime-meta.is-empty {
    color: var(--m-muted);
  }

  .mango-locator-runtime-meta__text {
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
