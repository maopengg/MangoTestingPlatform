<template>
  <a-card title="测试报告">
    <a-input v-model="content" placeholder="请输入信息" />
  </a-card>
</template>

<script lang="ts" setup>
import { ref } from 'vue'

const content = ref('')
</script>
