<template>
  <div>
    <a-card :title="value">
      <a-input :v-model="content" placeholder="请输入信息" />
      <a-button @click="sendMessage">发送</a-button>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'

const value = ref('测试页面')
const content = ref('')
</script>
