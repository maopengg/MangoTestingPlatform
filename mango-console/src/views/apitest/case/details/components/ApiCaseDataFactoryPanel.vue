<template>
  <div class="m-2">
    <JsonDisplay v-if="active" :data="data" />
  </div>
</template>

<script setup lang="ts">
  defineProps<{ active: boolean; data: any }>()
</script>
