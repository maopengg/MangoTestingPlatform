<template>
  <a-card>
    <div>
      <a-input-tag
        :default-value="data"
        :style="{ width: '380px' }"
        placeholder="Please Enter"
        :max-tag-count="4"
        allow-clear
        @change="handleTagChange"
      />
    </div>
  </a-card>
</template>

<script setup lang="ts">
  import { onMounted, reactive } from 'vue'
  const data: any = reactive(['one', 'two', 'three', 'four'])

  function handleTagChange(value: string[]) {
    console.log(value)
  }

  onMounted(() => {})
</script>
