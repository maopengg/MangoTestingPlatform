<template>
  <div class="mango-key-value-editor">
    <div v-for="(row, index) in rows" :key="row.id" class="mango-key-value-editor__row">
      <a-input
        :model-value="row.key"
        :disabled="disabled"
        placeholder="字段名"
        @update:model-value="updateRow(index, 'key', $event)" data-testid="qa-components-forms-keyvalueeditor-input-字段名"
      />
      <a-input
        :model-value="row.value"
        :disabled="disabled"
        placeholder="字段值"
        @update:model-value="updateRow(index, 'value', $event)" data-testid="qa-components-forms-keyvalueeditor-input-字段值"
      />
      <a-button
        size="mini"
        type="text"
        status="danger"
        :disabled="disabled || rows.length <= 1"
        @click="removeRow(index)" data-testid="qa-components-forms-keyvalueeditor-button-移除"
      >
        移除
      </a-button>
    </div>
    <a-button size="mini" type="text" :disabled="disabled" @click="addRow" data-testid="qa-components-forms-keyvalueeditor-button-添加字段">添加字段</a-button>
  </div>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue'

  interface KeyValueRow {
    id: number
    key: string
    value: string
  }

  const props = withDefaults(
    defineProps<{
      modelValue?: unknown
      disabled?: boolean
    }>(),
    {
      modelValue: undefined,
      disabled: false,
    }
  )
  const emit = defineEmits<{
    (event: 'update:modelValue', value: Record<string, string>): void
  }>()

  let sequence = 0
  let emittedFingerprint = ''
  const rows = ref<KeyValueRow[]>([])

  function parseValue(value: unknown): Record<string, unknown> {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, unknown>
    }
    if (typeof value !== 'string' || !value.trim()) return {}
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    } catch (_) {
      return {}
    }
  }

  function createRow(key = '', value = ''): KeyValueRow {
    sequence += 1
    return { id: sequence, key, value }
  }

  function hydrate(value: unknown) {
    const entries = Object.entries(parseValue(value))
    rows.value = entries.length
      ? entries.map(([key, item]) => createRow(key, item == null ? '' : String(item)))
      : [createRow()]
  }

  function emitValue() {
    const value = Object.fromEntries(
      rows.value.map((row) => [row.key.trim(), row.value] as const).filter(([key]) => Boolean(key))
    )
    emittedFingerprint = JSON.stringify(value)
    emit('update:modelValue', value)
  }

  function updateRow(index: number, field: 'key' | 'value', value: string) {
    rows.value[index][field] = value
    emitValue()
  }

  function addRow() {
    rows.value.push(createRow())
  }

  function removeRow(index: number) {
    rows.value.splice(index, 1)
    emitValue()
  }

  watch(
    () => props.modelValue,
    (value) => {
      if (JSON.stringify(parseValue(value)) === emittedFingerprint) {
        emittedFingerprint = ''
        return
      }
      hydrate(value)
    },
    { immediate: true, deep: true }
  )
</script>

<style scoped lang="less">
  .mango-key-value-editor {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 6px;
  }

  .mango-key-value-editor__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
    min-width: 0;
    gap: 6px;
    align-items: center;
  }

  .mango-key-value-editor > :deep(.arco-btn) {
    align-self: flex-start;
  }
</style>
