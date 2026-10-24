<template>
  <div class="mango-mock-response-editor">
    <div class="mango-mock-response-row">
      <a-form-item label="状态码"><a-input-number :model-value="modelValue.status_code" :min="100" :max="599" @update:model-value="updateField('status_code', $event)" /></a-form-item>
      <a-form-item label="响应类型"><a-select :model-value="modelValue.body_type" :options="bodyTypeOptions" @update:model-value="updateField('body_type', $event)" /></a-form-item>
      <a-form-item label="Content-Type"><a-input :model-value="modelValue.content_type" @update:model-value="updateField('content_type', $event)" /></a-form-item>
      <a-form-item label="延迟(ms)"><a-input-number :model-value="modelValue.delay_ms" :min="0" :max="30000" @update:model-value="updateField('delay_ms', $event)" /></a-form-item>
    </div>
    <a-form-item label="响应头(JSON)">
      <a-textarea v-model="headersText" :auto-size="{ minRows: 2, maxRows: 5 }" placeholder='如 {"X-Mock":"true"}' @blur="applyHeaders" />
    </a-form-item>
    <a-form-item v-if="modelValue.body_type !== 'empty'" label="响应体">
      <a-textarea :model-value="modelValue.body" class="mango-mock-response-body" :auto-size="{ minRows: 8, maxRows: 18 }" placeholder="请输入原始响应内容" @update:model-value="updateField('body', $event)" />
    </a-form-item>
  </div>
</template>

<script lang="ts" setup>
  import { ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type { MockResponseConfig } from '@/api/apitest/mock'

  const props = defineProps<{ modelValue: MockResponseConfig }>()
  const emit = defineEmits<{ (event: 'update:modelValue', value: MockResponseConfig): void }>()
  const headersText = ref(JSON.stringify(props.modelValue.headers || {}, null, 2))
  const bodyTypeOptions = [
    { label: 'JSON', value: 'json' }, { label: '文本', value: 'text' },
    { label: 'HTML', value: 'html' }, { label: 'XML', value: 'xml' }, { label: '空响应', value: 'empty' },
  ]
  watch(() => props.modelValue.headers, (value) => { headersText.value = JSON.stringify(value || {}, null, 2) }, { deep: true })

  function updateField<K extends keyof MockResponseConfig>(key: K, value: MockResponseConfig[K]) {
    emit('update:modelValue', { ...props.modelValue, [key]: value })
  }

  function applyHeaders() {
    try { updateField('headers', JSON.parse(headersText.value || '{}')) }
    catch { Message.error('响应头必须是合法 JSON 对象') }
  }
</script>

<style scoped>
  .mango-mock-response-editor { width: 100%; max-width: 1180px; }
  .mango-mock-response-row { display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 8px; }
  .mango-mock-response-body { font-family: var(--m-font-mono); }
  @container (max-width: 980px) { .mango-mock-response-row { grid-template-columns: repeat(2, minmax(180px, 1fr)); } }
</style>
