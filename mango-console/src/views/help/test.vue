<template>
  <div>
    <a-input v-model="name" />
    <a-button @click="f">点击</a-button>
  </div>
  <span>{{ name }}</span>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import curlconverter from 'curlconverter'
  const name = ref('')
  function f() {
    name.value = curlconverter.toJsonString(name.value)
    console.log(name.value)
  }
</script>
