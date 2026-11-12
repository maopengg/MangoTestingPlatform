<template>
  <section class="mango-extraction-editor">
    <div class="mango-section-title">
      <strong>响应提取</strong>
      <a-button v-if="!disabled" size="small" :disabled="rows.length >= 100" @click="add"
        >添加提取</a-button
      >
    </div>
    <p v-if="showHint" class="mango-extraction-hint"
      >可选；留空使用完整输出。一个表达式直接取值，多个表达式按顺序返回列表。接口正文从 $.json
      提取，Python 返回值从 $ 提取。</p
    >
    <div v-for="(row, index) in rows" :key="row.id" class="mango-extraction-row">
      <a-input
        v-model="row.path"
        :max-length="512"
        :disabled="disabled"
        :aria-label="`JSONPath ${index + 1}`"
        placeholder="$.json.data.answer"
        @update:model-value="changed"
      />
      <a-button v-if="!disabled" size="small" type="text" status="danger" @click="remove(index)"
        >移除</a-button
      >
    </div>
    <p data-feedback-kind="validation" v-if="error" role="alert" class="mango-extraction-error">{{ error }}</p>
  </section>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue'
  const props = withDefaults(
    defineProps<{ modelValue: { paths: string[] }; disabled?: boolean; showHint?: boolean }>(),
    { disabled: false, showHint: true }
  )
  const emit = defineEmits<{
    (event: 'update:modelValue', value: { paths: string[] }): void
    (event: 'validity-change', message: string): void
  }>()
  const rows = ref<Array<{ id: number; path: string }>>([]),
    error = ref('')
  let sequence = 0,
    emitted = ''
  watch(
    () => props.modelValue,
    (value) => {
      if (JSON.stringify(value) === emitted) return
      rows.value = (value?.paths || []).map((path: string) => ({ id: ++sequence, path }))
      error.value = ''
      emit('validity-change', '')
    },
    { deep: true, immediate: true }
  )
  function changed() {
    if (props.disabled) return
    const paths = rows.value.map((row) => row.path.trim())
    error.value = paths.some((path) => !path)
      ? '请填写 JSONPath，或移除空行'
      : paths.length !== new Set(paths).size
      ? '提取表达式不能重复'
      : paths.some((path) => !path.startsWith('$'))
      ? '提取表达式必须以 $ 开头'
      : ''
    emit('validity-change', error.value)
    if (error.value) return
    const value = { paths }
    emitted = JSON.stringify(value)
    emit('update:modelValue', value)
  }
  function add() {
    if (!props.disabled && rows.value.length < 100) {
      rows.value.push({ id: ++sequence, path: '' })
      changed()
    }
  }
  function remove(index: number) {
    if (!props.disabled) {
      rows.value.splice(index, 1)
      changed()
    }
  }
</script>
<style scoped>
  .mango-extraction-editor {
    min-width: 0;
    max-width: 880px;
    margin-top: var(--m-page-gap);
  }
  .mango-extraction-hint {
    margin: var(--m-page-gap) 0;
    color: var(--m-muted);
    font-size: var(--m-font-caption);
    line-height: 1.6;
    overflow-wrap: anywhere;
  }
  .mango-extraction-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 48px;
    gap: var(--m-page-gap);
    align-items: center;
    margin-bottom: var(--m-page-gap);
  }
  .mango-extraction-error {
    color: var(--m-danger);
    margin: var(--m-page-gap) 0;
  }
</style>
