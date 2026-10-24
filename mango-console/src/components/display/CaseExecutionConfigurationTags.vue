<template>
  <span v-if="sqlCount == null || factoryCount == null">—</span>
  <a-space v-else-if="sqlCount > 0 || factoryCount > 0" :size="4">
    <a-tag v-if="sqlCount > 0" color="orange" size="small">SQL {{ sqlCount }}</a-tag>
    <a-tag v-if="factoryCount > 0" color="blue" size="small">数据工厂 {{ factoryCount }}</a-tag>
  </a-space>
  <span v-else>无</span>
</template>

<script setup lang="ts">
  defineProps<{
    sqlCount?: number | null
    factoryCount?: number | null
  }>()
</script>
