<template>
  <a-tooltip v-if="normalizedValues.length" :content="tooltipContent">
    <div class="mango-execution-scene-grid">
      <a-tag
        v-for="value in visibleValues"
        :key="String(value)"
        :color="tagColor(value)"
        size="small"
      >
        {{ tagTitle(value) }}
      </a-tag>
      <a-tag
        v-if="hasOverflow"
        class="mango-execution-scene-grid__more"
        size="small"
        :aria-label="overflowLabel"
      >
        ...
      </a-tag>
    </div>
  </a-tooltip>
  <span v-else>-</span>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { getEnumTagColor } from '@/utils/business-format'

  type SceneValue = string | number
  type EnumOption = { key: SceneValue; title: string }

  const props = withDefaults(
    defineProps<{
      values?: unknown
      options?: EnumOption[] | null
      colors?: string[]
      maxVisibleTags?: 3 | 4
      overflowLabel?: string
    }>(),
    {
      options: () => [],
      colors: () => [],
      maxVisibleTags: 4,
      overflowLabel: '查看更多执行场景',
    }
  )

  const normalizedValues = computed<SceneValue[]>(() =>
    Array.isArray(props.values)
      ? props.values.filter(
          (value): value is SceneValue => typeof value === 'string' || typeof value === 'number'
        )
      : []
  )
  const hasOverflow = computed(() => normalizedValues.value.length > props.maxVisibleTags)
  const visibleValues = computed(() =>
    normalizedValues.value.slice(0, hasOverflow.value ? 3 : props.maxVisibleTags)
  )
  const tooltipContent = computed(() => normalizedValues.value.map(tagTitle).join('、'))

  function tagTitle(value: SceneValue) {
    return (
      (props.options || []).find((item) => String(item.key) === String(value))?.title ||
      String(value)
    )
  }

  function tagColor(value: SceneValue) {
    return getEnumTagColor(props.options, value, props.colors)
  }
</script>

<style scoped lang="less">
  .mango-execution-scene-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px;
    width: 100%;
  }

  .mango-execution-scene-grid :deep(.arco-tag) {
    min-width: 0;
    justify-content: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-execution-scene-grid__more {
    min-width: 0;
    justify-content: center;
    color: var(--m-muted);
  }
</style>
