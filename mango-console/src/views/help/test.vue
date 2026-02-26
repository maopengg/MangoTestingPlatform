<template>
  <div>
    <a-card :title="value">
      <JsonDisplay :data="jsonString" />
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'

  const value = ref('测试页面')
  const jsonString = ref(
    '{"data":1995772484258893823,"success":{"data":1995772484258893812,"success":true,"errorCode":"NO-ERROR","errorMessage":"NO-MESSAGE"},"errorCode":"NO-ERROR","errorMessage":"NO-MESSAGE"}'
  )
</script>

<style scoped></style>
