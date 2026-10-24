<template>
  <div v-if="locator?.loc" class="mango-ui-locator-group-cell">
    <div class="mango-ui-locator-group-cell__head">
      <a-tag v-if="typeLabel" :color="typeColor" size="small">{{ typeLabel }}</a-tag>
      <span>下标 {{ locator.sub || '-' }}</span>
      <a-tag
        v-if="matchCount !== null && matchCount !== undefined"
        :color="matchColor"
        size="small"
      >
        {{ matchLabel }} {{ matchCount }}
      </a-tag>
      <span v-if="sourceLabel">{{ sourceLabel }}</span>
      <span v-if="score !== null && score !== undefined">{{ score }} 分</span>
    </div>
    <a-tooltip :content="locator.loc">
      <div class="mango-ui-locator-group-cell__expression">{{ locator.loc }}</div>
    </a-tooltip>
    <a-tooltip v-if="textSummary" :content="textSummary">
      <div class="mango-ui-locator-group-cell__text">文本摘要 {{ textSummary }}</div>
    </a-tooltip>
  </div>
  <span v-else class="mango-ui-muted">-</span>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'

  const props = withDefaults(
    defineProps<{
      locator?: Record<string, any> | null
      typeLabel?: string
      typeColor?: string
      matchCount?: number | string | null
      matchLabel?: string
      textSummary?: string
      sourceLabel?: string
      score?: number | string | null
    }>(),
    {
      locator: null,
      typeLabel: '',
      typeColor: '',
      matchCount: null,
      matchLabel: '最近',
      textSummary: '',
      sourceLabel: '',
      score: null,
    }
  )

  const matchColor = computed(() => {
    const count = Number(props.matchCount)
    if (count === 1) return 'green'
    if (count === 0) return 'red'
    return 'orange'
  })
</script>

<style scoped lang="less">
  .mango-ui-locator-group-cell {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 5px;
  }

  .mango-ui-locator-group-cell__head {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
    color: var(--m-muted);
    font-size: 12px;
    white-space: nowrap;
  }

  .mango-ui-locator-group-cell__expression,
  .mango-ui-locator-group-cell__text {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-locator-group-cell__text {
    color: var(--m-muted);
  }
</style>
