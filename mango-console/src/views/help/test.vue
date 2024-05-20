<template>
  <a-card>
    <a-space>
      <a-input v-model="value" />
      <a-button @click="postApiInfo">点击</a-button>
    </a-space>
    <span>1 {{ value }}</span>
  </a-card>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { post } from '@/api/http'
  import { apiImportUrl } from '@/api/apitest/url'
  const value: any = ref('测试')
  function postApiInfo() {
    post({
      url: apiImportUrl,
      data: () => {
        return {
          command: value.value,
          target: 'json',
        }
      },
    })
      .then((res) => {
        console.log(res)
      })
      .catch(console.log)
  }
</script>
