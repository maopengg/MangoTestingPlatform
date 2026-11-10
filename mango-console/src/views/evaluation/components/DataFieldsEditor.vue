<template>
  <div class="mango-data-fields-editor">
    <template v-if="kind === 'object'">
      <div v-for="key in keys" :key="key" class="mango-data-field-row">
        <div
          class="mango-data-field-label"
          :class="{ 'mango-form-item__require': schema?.required?.includes(key) }"
          ><label :for="`${uid}-${key}`">{{
            schema?.properties?.[key]?.title || fieldTitle(key)
          }}</label></div
        >
        <div class="mango-data-field-control"
          ><DataFieldsEditor
            :model-value="objectValue[key]"
            :schema="schema?.properties?.[key]"
            :input-id="`${uid}-${key}`"
            :required="schema?.required?.includes(key)"
            :disabled="disabled"
            @update:model-value="set(key, $event)"
        /></div>
        <a-button
          v-if="
            !disabled &&
            !schema?.required?.includes(key) &&
            Object.prototype.hasOwnProperty.call(objectValue, key)
          "
          class="mango-data-field-action"
          size="small"
          type="text"
          status="danger"
          @click="remove(key)"
          >{{
            schema?.properties?.[key]
              ? Array.isArray(objectValue[key])
                ? '清空列表'
                : '清空'
              : '移除字段'
          }}</a-button
        >
      </div>
      <div
        v-if="!disabled && schema?.additionalProperties !== false"
        class="mango-data-field-add"
        :class="{ 'mango-data-field-add--editing': addingField }"
      >
        <template v-if="addingField"
          ><a-input
            v-model="newKey"
            size="small"
            placeholder="字段名称"
            aria-label="新字段名称"
          /><a-select
            v-model="newType"
            size="small"
            :options="typeOptions"
            aria-label="新字段类型"
          /><a-space
            ><a-button size="small" @click="add">添加</a-button
            ><a-button size="small" type="text" @click="addingField = false"
              >取消</a-button
            ></a-space
          ></template
        >
        <a-button v-else size="small" type="text" @click="addingField = true">添加字段</a-button>
      </div>
      <span v-if="!keys.length && disabled" class="mango-data-field-hint">未配置</span>
    </template>
    <template v-else-if="kind === 'array'">
      <div
        v-for="(item, index) in arrayValue"
        :key="index"
        class="mango-data-array-row"
        :class="{ 'mango-data-array-row--structured': item !== null && typeof item === 'object' }"
      >
        <div class="mango-data-array-index">{{
          item !== null && typeof item === 'object' ? `第 ${index + 1} 条` : index + 1
        }}</div>
        <DataFieldsEditor
          :model-value="item"
          :schema="schema?.items"
          :disabled="disabled"
          @update:model-value="setAt(index, $event)"
        />
        <a-button
          v-if="!disabled"
          class="mango-data-array-remove"
          size="small"
          type="text"
          status="danger"
          :aria-label="`移除第 ${index + 1} 条`"
          @click="removeAt(index)"
          >移除条目</a-button
        >
      </div>
      <a-space v-if="!disabled"
        ><a-select
          v-if="!schema?.items && !arrayValue.length"
          v-model="newType"
          size="small"
          :options="typeOptions"
          aria-label="条目类型"
        /><a-button size="small" @click="addItem">添加条目</a-button></a-space
      >
    </template>
    <a-select
      v-else-if="schema?.enum"
      :id="inputId"
      size="small"
      :aria-required="required || undefined"
      :model-value="modelValue"
      :options="schema.enum.map((value) => ({ label: String(value), value }))"
      :disabled="disabled"
      allow-clear
      @change="emit('update:modelValue', $event)"
    />
    <a-switch
      v-else-if="kind === 'boolean'"
      :id="inputId"
      :aria-required="required || undefined"
      :model-value="modelValue === true"
      :disabled="disabled"
      size="small"
      @change="emit('update:modelValue', $event)"
    />
    <a-input-number
      v-else-if="kind === 'number' || kind === 'integer'"
      :id="inputId"
      size="small"
      :aria-required="required || undefined"
      :model-value="modelValue"
      :min="schema?.minimum"
      :max="schema?.maximum"
      :precision="kind === 'integer' ? 0 : undefined"
      :disabled="disabled"
      @change="emit('update:modelValue', $event)"
    />
    <a-textarea
      v-else
      :id="inputId"
      size="small"
      :aria-required="required || undefined"
      :model-value="modelValue == null ? '' : String(modelValue)"
      :placeholder="schema?.description"
      :disabled="disabled"
      :auto-size="{ minRows: 1, maxRows: 6 }"
      @update:model-value="emit('update:modelValue', $event)"
    />
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, useId } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldTitle, valueType } from './presentation'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import type { ParameterSchema } from '../types'
  const props = withDefaults(
    defineProps<{
      modelValue: unknown
      schema?: ParameterSchema
      disabled?: boolean
      inputId?: string
      required?: boolean
    }>(),
    { disabled: false, required: false }
  )
  const emit = defineEmits<{ (event: 'update:modelValue', value: unknown): void }>()
  const uid = useId(),
    newKey = ref(''),
    newType = ref('string'),
    addingField = ref(false)
  const typeOptions = [
    { label: '文本', value: 'string' },
    { label: '数字', value: 'number' },
    { label: '开关', value: 'boolean' },
    { label: '对象', value: 'object' },
    { label: '列表', value: 'array' },
  ]
  const kind = computed(() =>
    props.schema?.type === 'integer' && typeof props.modelValue === 'number'
      ? 'integer'
      : props.modelValue != null
      ? valueType(props.modelValue)
      : props.schema?.type || (props.schema?.properties ? 'object' : 'string')
  )
  const objectValue = computed<Record<string, unknown>>(() =>
    props.modelValue !== null &&
    typeof props.modelValue === 'object' &&
    !Array.isArray(props.modelValue)
      ? (props.modelValue as Record<string, unknown>)
      : {}
  )
  const arrayValue = computed<unknown[]>(() =>
    Array.isArray(props.modelValue) ? props.modelValue : []
  )
  const keys = computed(() => [
    ...new Set([...Object.keys(props.schema?.properties || {}), ...Object.keys(objectValue.value)]),
  ])
  function initial(schema?: ParameterSchema): unknown {
    if (schema?.default !== undefined) return cloneLosslessJson(schema.default)
    switch (schema?.type) {
      case 'object':
        return {}
      case 'array':
        return []
      case 'boolean':
        return false
      case 'integer':
      case 'number':
        return 0
      default:
        return ''
    }
  }
  function set(key: string, value: unknown) {
    if (!props.disabled) emit('update:modelValue', { ...objectValue.value, [key]: value })
  }
  function remove(key: string) {
    if (props.disabled) return
    const next = { ...objectValue.value }
    delete next[key]
    emit('update:modelValue', next)
  }
  function setAt(index: number, value: unknown) {
    if (!props.disabled)
      emit(
        'update:modelValue',
        arrayValue.value.map((item, i) => (i === index ? value : item))
      )
  }
  function removeAt(index: number) {
    if (!props.disabled)
      emit(
        'update:modelValue',
        arrayValue.value.filter((_, i) => i !== index)
      )
  }
  function addItem() {
    if (!props.disabled)
      emit('update:modelValue', [
        ...arrayValue.value,
        initial(
          props.schema?.items || {
            type: arrayValue.value.length ? valueType(arrayValue.value[0]) : newType.value,
          }
        ),
      ])
  }
  function add() {
    if (props.disabled) return
    const key = newKey.value.trim()
    if (!key || keys.value.includes(key)) {
      Message.warning('请输入不重复的字段编码')
      return
    }
    set(key, initial({ type: newType.value }))
    newKey.value = ''
    addingField.value = false
  }
</script>
<style scoped>
  .mango-data-fields-editor {
    min-width: 0;
    width: 100%;
    container-type: inline-size;
  }
  .mango-data-field-row {
    display: flex;
    align-items: flex-start;
    gap: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
  }
  .mango-data-field-label {
    flex: 0 0 112px;
    padding-top: 4px;
    overflow-wrap: anywhere;
    color: var(--m-text-2);
  }
  .mango-data-field-label > label {
    display: inline-flex;
    align-items: baseline;
  }
  .mango-data-field-control {
    flex: 1;
    min-width: 0;
  }
  .mango-data-field-add {
    display: flex;
    gap: var(--m-page-gap);
    margin-top: var(--m-page-gap);
  }
  .mango-data-field-add--editing {
    display: grid;
    grid-template-columns: minmax(100px, 1fr) 100px auto;
  }
  .mango-data-array-row {
    display: grid;
    grid-template-columns: 20px minmax(0, 1fr) auto;
    align-items: start;
    gap: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
  }
  .mango-data-array-index {
    padding-top: 4px;
    color: var(--m-muted);
  }
  .mango-data-array-row--structured {
    grid-template-columns: minmax(0, 1fr) auto;
    padding-bottom: var(--m-page-gap);
  }
  .mango-data-array-row--structured > .mango-data-array-index {
    grid-column: 1;
    grid-row: 1;
  }
  .mango-data-array-row--structured > .mango-data-array-remove {
    grid-column: 2;
    grid-row: 1;
  }
  .mango-data-array-row--structured > .mango-data-fields-editor {
    grid-column: 1 / -1;
    padding-left: 12px;
    border-left: 1px solid var(--m-border);
  }
  .mango-data-field-hint {
    color: var(--m-muted);
    overflow-wrap: anywhere;
  }
  @container (max-width: 420px) {
    .mango-data-field-row {
      gap: var(--m-space-sm);
      flex-wrap: wrap;
    }
    .mango-data-field-label {
      flex-basis: 88px;
    }
    .mango-data-field-action {
      margin-left: 96px;
    }
    .mango-data-field-add--editing {
      grid-template-columns: minmax(0, 1fr) 90px;
    }
    .mango-data-field-add--editing > .arco-space {
      grid-column: 1 / -1;
      justify-self: end;
    }
  }
</style>
