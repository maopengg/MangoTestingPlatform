<template>
  <div>
    <a-input v-model="name" />
    <a-button @click="f" data-testid="qa-views-perf-prepare-button-点击">点击</a-button>
  </div>
  <span>{{ name }}</span>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'

  const name = ref('')

  function f() {}
</script>
