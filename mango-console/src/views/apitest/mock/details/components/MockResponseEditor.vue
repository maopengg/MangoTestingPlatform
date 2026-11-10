<template>
  <div class="mango-mock-response-editor">
    <div class="mango-mock-response-row">
      <a-form-item label="状态码"
        ><a-input-number
          :disabled="disabled"
          :model-value="response.status_code"
          :min="100"
          :max="599"
          @update:model-value="updateField('status_code', $event)"
      /></a-form-item>
      <a-form-item label="响应类型"
        ><a-select
          :disabled="disabled"
          :model-value="response.body_type"
          :options="bodyTypeOptions"
          @update:model-value="updateField('body_type', $event)"
      /></a-form-item>
      <a-form-item label="Content-Type"
        ><a-input
          :disabled="disabled"
          :model-value="response.content_type"
          @update:model-value="updateField('content_type', $event)"
      /></a-form-item>
      <a-form-item label="延迟(ms)"
        ><a-input-number
          :disabled="disabled"
          :model-value="response.delay_ms"
          :min="0"
          :max="30000"
          @update:model-value="updateField('delay_ms', $event)"
      /></a-form-item>
    </div>
    <a-form-item
      label="响应头(JSON)"
      :validate-status="headersError ? 'error' : undefined"
      :help="headersError || undefined"
    >
      <a-textarea
        :model-value="headersText"
        :disabled="disabled"
        @update:model-value="onHeadersInput"
        :auto-size="{ minRows: 2, maxRows: 5 }"
        placeholder='如 {"X-Mock":"true"}'
        @blur="applyHeaders"
      />
    </a-form-item>
    <a-form-item v-if="response.body_type !== 'empty'" label="响应体">
      <a-textarea
        :disabled="disabled"
        :model-value="response.body"
        class="mango-mock-response-body"
        :auto-size="{ minRows: 8, maxRows: 18 }"
        placeholder="请输入原始响应内容"
        @update:model-value="updateField('body', $event)"
      />
    </a-form-item>
  </div>
</template>

<script setup lang="ts">
  import { ref, watch, onBeforeUnmount } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { cloneLosslessJson, stringifyLosslessJson } from '@/utils/lossless-json'
  import type { MockResponseConfig } from '@/api/apitest/mock'
  import { bodyTypeOptions } from '../config'
  const props = withDefaults(
    defineProps<{ modelValue: MockResponseConfig; disabled?: boolean }>(),
    { disabled: false }
  )
  const emit = defineEmits<{
    (event: 'update:modelValue', value: MockResponseConfig): void
    (event: 'validity-change', valid: boolean): void
  }>()
  const response = ref(cloneLosslessJson(props.modelValue))
  const headersText = ref(stringifyLosslessJson(props.modelValue.headers || {}, 2)),
    headersError = ref('')
  let previousHeaders = stringifyLosslessJson(props.modelValue.headers)
  watch(
    () => props.modelValue,
    (value) => {
      response.value = cloneLosslessJson(value)
      const text = stringifyLosslessJson(value.headers || {}, 2)
      const nextHeaders = stringifyLosslessJson(value.headers)
      if (
        nextHeaders !== previousHeaders &&
        nextHeaders !== stringifyLosslessJson(parsedHeaders())
      ) {
        headersText.value = text
        headersError.value = ''
        emit('validity-change', true)
      }
      previousHeaders = nextHeaders
    }
  )
  function parsedHeaders(): Record<string, string> | null {
    try {
      const value: unknown = JSON.parse(headersText.value || '{}')
      if (
        !value ||
        typeof value !== 'object' ||
        Array.isArray(value) ||
        !Object.values(value).every((item) => typeof item === 'string')
      )
        return null
      return value as Record<string, string>
    } catch {
      return null
    }
  }
  function updateField<K extends keyof MockResponseConfig>(key: K, value: MockResponseConfig[K]) {
    if (props.disabled) return
    Object.assign(response.value, { [key]: cloneLosslessJson(value) })
    emit('update:modelValue', cloneLosslessJson(response.value))
  }
  function onHeadersInput(value: string) {
    if (props.disabled) return
    headersText.value = value
    const headers = parsedHeaders()
    headersError.value = headers ? '' : '响应头必须是键值均为字符串的 JSON 对象'
    emit('validity-change', Boolean(headers))
    if (headers) updateField('headers', headers)
  }
  function applyHeaders() {
    if (props.disabled) return
    onHeadersInput(headersText.value)
    if (headersError.value) Message.error(headersError.value)
  }
  onBeforeUnmount(() => emit('validity-change', true))
</script>
<style scoped>
  .mango-mock-response-editor {
    width: 100%;
    max-width: 1180px;
  }
  .mango-mock-response-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(180px, 1fr));
    gap: 8px;
  }
  .mango-mock-response-body {
    font-family: var(--m-font-mono);
  }
  @container (max-width: 980px) {
    .mango-mock-response-row {
      grid-template-columns: repeat(2, minmax(180px, 1fr));
    }
  }
</style>
