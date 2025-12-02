<template>
  <div>
    <a-card :title="value">
      <JsonDisplay :data="content" />
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { ref, reactive } from 'vue'

  const value = ref('测试页面')
  const content = reactive({
    data: 1995772484258893812,

    success: true,

    errorCode: 'NO-ERROR',

    errorMessage: 'NO-MESSAGE',
  })
</script>

<style scoped></style>
