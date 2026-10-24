<template>
  <a-empty
    v-if="!detail"
    description="请选择执行记录"
    class="mango-ui-case-execution-result__empty"
  />
  <div v-else class="mango-ui-case-execution-result">
    <a-alert v-if="executionError" type="error" class="mango-ui-case-execution-result__alert">
      {{ executionError }}
    </a-alert>
    <ElementTestReport v-if="resultData" :result-data="resultData" />
    <a-empty
      v-else
      description="本轮执行没有可展示的 UI 测试结果"
      class="mango-ui-case-execution-result__empty"
    />
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import ElementTestReport from './ElementTestReport.vue'

  const props = defineProps<{
    detail: any | null
  }>()

  const resultData = computed(() => props.detail?.result_data || null)
  const executionError = computed(
    () => props.detail?.error_message || resultData.value?.error_message || ''
  )
</script>

<style scoped>
  .mango-ui-case-execution-result {
    min-width: 0;
    min-height: 0;
    flex: 1;
    overflow: auto;
  }

  .mango-ui-case-execution-result__alert {
    margin-bottom: 10px;
  }

  .mango-ui-case-execution-result__empty {
    margin: auto;
  }
</style>
