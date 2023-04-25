<template>
  <div>
    <a-split
      :style="{
        height: '200px',
        width: '100%',
        minWidth: '500px',
        border: '1px solid var(--color-border)'
      }"
      v-model:size="size"
      min="80px"
    >
      <template #first>
        <a-typography-paragraph>Left</a-typography-paragraph>
      </template>
      <template #second>
        <a-typography-paragraph>Right</a-typography-paragraph>
      </template>
    </a-split>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'

const content = ref('')
</script>
