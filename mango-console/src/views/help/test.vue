<template>
  <a-space direction="vertical">
    <a-checkbox-group direction="vertical" v-model="data" @change="handleChange">
      <a-checkbox value="1">Option 1</a-checkbox>
      <a-checkbox value="2">Option 2</a-checkbox>
      <a-checkbox value="3">Option 3</a-checkbox>
    </a-checkbox-group>
  </a-space>
</template>

<script setup>
  import { ref } from 'vue'

  const data = ref(['2'])

  const handleChange = (values) => {
    console.log(values)
  }
</script>
