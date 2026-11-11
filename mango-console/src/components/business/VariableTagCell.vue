<template>
  <ExecutionSceneTagGrid
    :values="names"
    :options="options"
    :colors="colors"
    :max-visible-tags="3"
    overflow-label="查看更多分类标签"
  />
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import { useEnum } from '@/store/modules/get-enum'

  const props = defineProps<{ tags?: string[] }>()
  const enumStore = useEnum()
  const names = computed(() => [...new Set((props.tags || []).map(tag => tag.trim()).filter(Boolean))])
  const options = computed(() => names.value.map(tag => ({ key: tag, title: tag })))
  const colors = computed(() => names.value.map(tag => {
    const palette = enumStore.colors || []
    // 同一分类在不同记录和排序下保持同色，颜色复用全局枚举调色板。
    let hash = 0
    for (const character of tag) hash = (Math.imul(hash, 31) + character.codePointAt(0)!) >>> 0
    return palette.length ? palette[hash % palette.length] : 'gray'
  }))
</script>
