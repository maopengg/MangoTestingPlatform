<template>
  <div class="mango-assertion-parameter-editor">
    <div class="mango-assertion-parameter-editor__label">
      <span :title="parameter.p || parameter.n || parameter.f">
        {{ parameter.n || parameter.f }}
      </span>
    </div>
    <div class="mango-assertion-parameter-editor__control">
      <KeyValueEditor
        v-if="isKeyValueParameter"
        :model-value="modelValue"
        :disabled="disabled"
        @update:model-value="emitValue"
      />
      <CodeEditor
        v-else-if="isCodeParameter"
        :model-value="stringValue"
        :readonly="disabled"
        :placeholder="stringPlaceholder"
        language="python"
        :line-height="180"
        @update:model-value="emitValue"
      />
      <a-input-number
        v-else-if="currentType === 'number'"
        :model-value="numberValue"
        :disabled="disabled"
        :placeholder="parameter.p || '请输入数字'"
        allow-clear
        hide-button
        @update:model-value="emitValue"
      />
      <a-select
        v-else-if="currentType === 'boolean'"
        :model-value="booleanValue"
        :disabled="disabled"
        placeholder="请选择布尔值"
        :options="booleanOptions"
        @update:model-value="emitValue" data-testid="qa-components-forms-assertionparametereditor-select-请选择布尔值"
      />
      <div v-else-if="currentType === 'null'" class="mango-assertion-parameter-editor__null">
        以 <code>null</code> 提交
      </div>
      <a-textarea
        v-else-if="currentType === 'string' && parameter.input_type === 'textarea'"
        :model-value="stringValue"
        :disabled="disabled"
        :placeholder="stringPlaceholder"
        :auto-size="{ minRows: 2, maxRows: 5 }"
        allow-clear
        @update:model-value="emitValue"
      />
      <a-input
        v-else-if="currentType === 'string'"
        :model-value="stringValue"
        :disabled="disabled"
        :placeholder="stringPlaceholder"
        allow-clear
        @update:model-value="emitValue"
      />

      <div v-else class="mango-assertion-parameter-editor__structured">
        <div
          v-if="currentType === 'object' && objectFieldKeys.length"
          class="mango-assertion-parameter-editor__object-grid"
        >
          <div
            v-for="fieldKey in objectFieldKeys"
            :key="fieldKey"
            class="mango-assertion-parameter-editor__object-field"
          >
            <label :title="objectFieldLabel(fieldKey)">{{ objectFieldLabel(fieldKey) }}</label>
            <a-select
              v-if="objectFieldType(fieldKey) === 'boolean'"
              :model-value="objectFieldValue(fieldKey)"
              :disabled="disabled"
              :options="booleanOptions"
              placeholder="请选择布尔值"
              @update:model-value="updateObjectField(fieldKey, $event)" data-testid="qa-components-forms-assertionparametereditor-select-请选择布尔值-2"
            />
            <a-input-number
              v-else-if="objectFieldType(fieldKey) === 'number'"
              :model-value="objectFieldNumberValue(fieldKey)"
              :disabled="disabled"
              :placeholder="objectFieldPlaceholder(fieldKey)"
              allow-clear
              hide-button
              @update:model-value="updateObjectField(fieldKey, $event)"
            />
            <a-input
              v-else
              :model-value="objectFieldDisplayValue(fieldKey)"
              :disabled="disabled"
              :placeholder="objectFieldPlaceholder(fieldKey)"
              allow-clear
              @update:model-value="
                updateObjectField(fieldKey, parseObjectFieldValue(fieldKey, $event))
              "
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import KeyValueEditor from '@/components/forms/KeyValueEditor.vue'
  import type { AssertionMethodParameter, AssertionValueType } from '@/types/assertion'

  const props = withDefaults(
    defineProps<{
      modelValue?: unknown
      parameter: AssertionMethodParameter
      disabled?: boolean
    }>(),
    {
      modelValue: '',
      disabled: false,
    }
  )

  const emit = defineEmits<{
    (event: 'update:modelValue', value: unknown): void
  }>()

  const booleanOptions = [
    { label: 'true', value: true },
    { label: 'false', value: false },
  ]

  function parseStructuredExample(value: unknown) {
    if (value && typeof value === 'object') return value
    if (typeof value !== 'string') return null
    const text = value.trim()
    if (!text.startsWith('{') && !text.startsWith('[')) return null
    try {
      return JSON.parse(text)
    } catch {
      return null
    }
  }

  function inferValueType(): AssertionValueType {
    if (props.parameter.value_type) return props.parameter.value_type
    const example = parseStructuredExample(props.parameter.v)
    if (Array.isArray(example)) return 'array'
    if (example && typeof example === 'object') return 'object'
    if (typeof props.parameter.v === 'number') return 'number'
    if (typeof props.parameter.v === 'boolean') return 'boolean'
    return 'string'
  }

  const currentType = ref<AssertionValueType>(inferValueType())
  const stringValue = computed(() =>
    typeof props.modelValue === 'string'
      ? props.modelValue
      : props.modelValue === undefined || props.modelValue === null
      ? ''
      : String(props.modelValue)
  )
  const stringPlaceholder = computed(() => {
    if (props.parameter.p) return props.parameter.p
    if (props.parameter.example_as_placeholder && props.parameter.v !== undefined) {
      return String(props.parameter.v)
    }
    return '请输入内容'
  })
  const isCodeParameter = computed(
    () => props.parameter.input_type === 'code' || props.parameter.n === '函数代码'
  )
  const isKeyValueParameter = computed(() => props.parameter.input_type === 'key_value')
  const numberValue = computed(() => {
    if (typeof props.modelValue === 'number') return props.modelValue
    if (props.modelValue === '' || props.modelValue === null || props.modelValue === undefined)
      return undefined
    const value = Number(props.modelValue)
    return Number.isFinite(value) ? value : undefined
  })
  const booleanValue = computed(() =>
    typeof props.modelValue === 'boolean' ? props.modelValue : undefined
  )

  const templateValue = computed(() => parseStructuredExample(props.parameter.v))
  const structuredValue = computed<Record<string, unknown> | unknown[]>(() => {
    if (currentType.value === 'array') {
      if (Array.isArray(props.modelValue)) return props.modelValue
      const parsed = parseStructuredExample(props.modelValue)
      return Array.isArray(parsed) ? parsed : []
    }
    if (
      props.modelValue &&
      typeof props.modelValue === 'object' &&
      !Array.isArray(props.modelValue)
    ) {
      return props.modelValue as Record<string, unknown>
    }
    const parsed = parseStructuredExample(props.modelValue)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {}
  })
  const objectTemplate = computed<Record<string, unknown>>(() =>
    templateValue.value &&
    typeof templateValue.value === 'object' &&
    !Array.isArray(templateValue.value)
      ? (templateValue.value as Record<string, unknown>)
      : {}
  )
  const objectFieldKeys = computed(() =>
    currentType.value === 'object'
      ? Array.from(
          new Set([
            ...(props.parameter.object_fields || []).map((field) => field.f),
            ...Object.keys(objectTemplate.value),
            ...Object.keys(structuredValue.value as Record<string, unknown>),
          ])
        )
      : []
  )
  function emitValue(value: unknown) {
    emit('update:modelValue', value)
  }

  function objectFieldValue(key: string) {
    return (structuredValue.value as Record<string, unknown>)[key]
  }

  function objectFieldDefinition(key: string) {
    return props.parameter.object_fields?.find((field) => field.f === key)
  }

  function objectFieldLabel(key: string) {
    return objectFieldDefinition(key)?.n || key
  }

  function objectFieldType(key: string): AssertionValueType {
    const definedType = objectFieldDefinition(key)?.value_type
    if (definedType) return definedType
    const value = objectFieldValue(key) ?? objectTemplate.value[key]
    if (typeof value === 'number') return 'number'
    if (typeof value === 'boolean') return 'boolean'
    if (Array.isArray(value)) return 'array'
    if (value && typeof value === 'object') return 'object'
    return 'string'
  }

  function objectFieldPlaceholder(key: string) {
    const definedPlaceholder = objectFieldDefinition(key)?.p
    if (definedPlaceholder) return definedPlaceholder
    const template = objectTemplate.value[key]
    return typeof template === 'string' ? template : `请输入${key}`
  }

  function objectFieldDisplayValue(key: string) {
    const value = objectFieldValue(key)
    if (value === undefined || value === null) return ''
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  function objectFieldNumberValue(key: string) {
    const value = Number(objectFieldValue(key))
    return Number.isFinite(value) ? value : undefined
  }

  function parseObjectFieldValue(key: string, value: string) {
    const type = objectFieldType(key)
    if (!['object', 'array', 'json'].includes(type)) return value
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  }

  function updateObjectField(key: string, value: unknown) {
    emitValue({
      ...(structuredValue.value as Record<string, unknown>),
      [key]: value,
    })
  }
</script>

<style scoped lang="less">
  .mango-assertion-parameter-editor {
    display: grid;
    grid-template-columns: 88px minmax(0, 1fr);
    min-width: 0;
    gap: 8px;
    align-items: start;
  }

  .mango-assertion-parameter-editor__label {
    display: flex;
    gap: 4px;
    align-items: center;
    justify-content: space-between;
  }

  .mango-assertion-parameter-editor__label {
    min-width: 0;
    min-height: 32px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-assertion-parameter-editor__label > span:first-child {
    overflow: hidden;
    min-width: 0;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-assertion-parameter-editor__control,
  .mango-assertion-parameter-editor__control > :deep(.arco-input-wrapper),
  .mango-assertion-parameter-editor__control > :deep(.arco-input-number),
  .mango-assertion-parameter-editor__control > :deep(.arco-select) {
    width: 100%;
    min-width: 0;
  }

  .mango-assertion-parameter-editor__null {
    min-height: 32px;
    padding: 6px 10px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
  }

  .mango-assertion-parameter-editor__structured {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 6px;
  }

  .mango-assertion-parameter-editor__object-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .mango-assertion-parameter-editor__object-field {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    min-width: 0;
    gap: 6px;
    align-items: center;
  }

  .mango-assertion-parameter-editor__object-field label {
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  @container mango-assertion-editor (max-width: 520px) {
    .mango-assertion-parameter-editor {
      grid-template-columns: 72px minmax(0, 1fr);
    }
  }
</style>
