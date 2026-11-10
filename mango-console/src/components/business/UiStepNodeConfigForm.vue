<template>
  <a-form
    :model="model"
    layout="horizontal"
    class="mango-ui-step-node-form"
    :class="{ 'is-compact': compact }"
  >
    <a-form-item
      v-for="item in items"
      :key="item.key"
      :class="{
        'is-compact-half': compact && item.compactHalf,
        'is-compact-narrow': compact && item.compactNarrow,
        'is-compact-wide-label': compact && item.compactWideLabel,
      }"
      :required="item.required && !isInherited(item)"
      :label="item.label"
    >
      <template v-if="isInherited(item)">
        <div class="mango-ui-step-node-form__inherited">
          <span :title="inheritedValue(item)">{{ inheritedValue(item) }}</span>
          <a-tag size="small" color="gray">继承页面步骤</a-tag>
        </div>
      </template>
      <a-input
        :key="controlKey(item, 'input')"
        v-else-if="item.type === 'input'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        :input-attrs="fieldAttrs(item)"
        :placeholder="item.placeholder"
        @update:model-value="setValue(item, $event)"
      />
      <a-input-number
        :key="controlKey(item, 'input-number')"
        v-else-if="item.type === 'input-number'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        :min="item.min"
        :max="item.max"
        :precision="item.precision"
        :placeholder="item.placeholder"
        hide-button
        @update:model-value="setValue(item, $event)"
      >
        <template v-if="item.suffix" #suffix>{{ item.suffix }}</template>
      </a-input-number>
      <a-cascader
        :key="controlKey(item, 'file-select')"
        v-else-if="item.type === 'file-select'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        :loading="fileLoading"
        :name="String(item.key)"
        :options="fileOptions"
        :placeholder="item.placeholder"
        allow-clear
        allow-search
        expand-trigger="hover"
        path-mode
        @update:model-value="setValue(item, $event)"
      />
      <a-cascader
        :key="controlKey(item, 'element-cascader')"
        v-else-if="item.type === 'element-cascader'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        :format-label="formatElementLabel"
        :name="String(item.key)"
        :options="elementCascaderOptions"
        :placeholder="item.placeholder"
        allow-clear
        allow-search
        expand-trigger="hover"
        path-mode
        @update:model-value="setValue(item, $event)"
        @change="emit('element-change', item.value)"
      />
      <a-select
        :key="controlKey(item, 'element-select')"
        v-else-if="item.type === 'select' && item.label === '选择元素'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        :field-names="fieldNames"
        :name="String(item.key)"
        :options="elementOptions"
        :placeholder="item.placeholder"
        allow-clear
        allow-search
        value-key="key"
        @update:model-value="setValue(item, $event)"
      />
      <a-select
        :key="controlKey(item, 'datasource-select')"
        v-else-if="item.type === 'datasource-select'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        :name="String(item.key)"
        :options="datasourceOptions"
        :placeholder="item.placeholder"
        allow-clear
        allow-search
        @update:model-value="setValue(item, $event)"
      />
      <a-cascader
        :key="controlKey(item, 'operation-cascader')"
        v-else-if="item.type === 'cascader' && item.label === '元素操作'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        :name="String(item.key)"
        :options="operationOptions"
        :placeholder="item.placeholder"
        allow-clear
        allow-search
        expand-trigger="hover"
        value-key="key"
        @update:model-value="setValue(item, $event)"
        @change="emit('method-change', item.value)"
      />
      <a-cascader
        :key="controlKey(item, 'assertion-cascader')"
        v-else-if="item.type === 'cascader'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        :name="String(item.key)"
        :options="assertionOptions"
        :placeholder="item.placeholder"
        allow-clear
        allow-search
        expand-trigger="hover"
        value-key="key"
        @update:model-value="setValue(item, $event)"
        @change="emit('method-change', item.value)"
      />
      <CodeEditor
        :key="controlKey(item, 'code')"
        v-else-if="item.type === 'code'"
        :model-value="item.value"
        :readonly="isDisabled(item)"
        :line-height="compact ? 150 : 360"
        :code-style="{ width: '100%' }"
        :placeholder="item.placeholder"
        @update:model-value="setValue(item, $event)"
      />
      <KeyValueEditor
        :key="controlKey(item, 'key-value')"
        v-else-if="item.type === 'key-value'"
        :model-value="item.value"
        :disabled="isDisabled(item)"
        @update:model-value="setValue(item, $event)"
      />
      <a-textarea
        :key="controlKey(item, 'textarea')"
        v-else
        :model-value="textareaValue(item.value)"
        :disabled="isDisabled(item)"
        :textarea-attrs="fieldAttrs(item)"
        :auto-size="compact ? { minRows: 1, maxRows: 4 } : { minRows: 4, maxRows: 7 }"
        :placeholder="item.placeholder"
        allow-clear
        @update:model-value="setValue(item, $event)"
      />
    </a-form-item>
    <slot></slot>
  </a-form>
</template>

<script lang="ts" setup>
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import KeyValueEditor from '@/components/forms/KeyValueEditor.vue'
  import { fieldNames } from '@/setting'
  import type { StepField, StepElement } from './ui-page-step'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  interface NodeChoice { label?: string; value: string | number; children?: NodeChoice[] }

  const props = withDefaults(
    defineProps<{
      items: StepField[]
      operationOptions?: NodeChoice[]
      assertionOptions?: NodeChoice[]
      elementOptions?: StepElement[]
      elementCascaderOptions?: NodeChoice[]
      fileOptions?: NodeChoice[]
      fileLoading?: boolean
      datasourceOptions?: NodeChoice[]
      disabled?: boolean
      compact?: boolean
      isItemDisabled?: (item: StepField) => boolean
      isItemInherited?: (item: StepField) => boolean
      getInheritedValue?: (item: StepField) => string
      fieldPrefix?: string
    }>(),
    {
      operationOptions: () => [],
      assertionOptions: () => [],
      elementOptions: () => [],
      elementCascaderOptions: () => [],
      fileOptions: () => [],
      datasourceOptions: () => [],
      fileLoading: false,
      disabled: false,
      compact: false,
      isItemDisabled: undefined,
      isItemInherited: undefined,
      getInheritedValue: undefined,
      fieldPrefix: '',
    }
  )
  const emit = defineEmits<{
    (event: 'method-change', value: unknown): void
    (event: 'element-change', value: unknown): void
    (event: 'update-field', key: string, value: unknown): void
    (event: 'change'): void
  }>()
  const model = {}

  function setValue(item: StepField, value: unknown) {
    if (isDisabled(item) || isInherited(item)) return
    emit('update-field', item.key, cloneLosslessJson(value))
    emit('change')
  }
  function controlKey(item: StepField, controlType: string) {
    return `${props.fieldPrefix}:${String(item.key)}:${controlType}`
  }
  function fieldAttrs(item: StepField) {
    const field = String(item.key).replace(/[^a-zA-Z0-9_-]/g, '-')
    const prefix = String(props.fieldPrefix || 'node').replace(/[^a-zA-Z0-9_-]/g, '-')
    return { id: `mango-ui-step-${prefix}-${field}`, name: String(item.key) }
  }
  function isDisabled(item: StepField) {
    return props.disabled || Boolean(props.isItemDisabled?.(item))
  }
  function isInherited(item: StepField) {
    return Boolean(props.isItemInherited?.(item))
  }
  function inheritedValue(item: StepField) {
    return props.getInheritedValue?.(item) || '-'
  }
  function formatElementLabel(options: Array<{ label?: string }> = []) {
    return options
      .map((item) => item?.label)
      .filter(Boolean)
      .join(' / ')
  }
  function textareaValue(value: unknown) {
    if (value === undefined || value === null) return ''
    if (typeof value === 'string') return value
    try {
      return JSON.stringify(value)
    } catch (_) {
      return String(value)
    }
  }
</script>

<style scoped>
  .mango-ui-step-node-form.is-compact {
    display: grid;
    grid-template-columns: minmax(0, 0.72fr) minmax(0, 1.28fr);
    column-gap: 12px;
  }
  .mango-ui-step-node-form.is-compact :deep(.arco-form-item) {
    display: flex;
    grid-column: 1 / -1;
    align-items: flex-start;
    flex-wrap: nowrap;
  }
  .mango-ui-step-node-form.is-compact :deep(.arco-form-item.is-compact-half) {
    grid-column: auto;
  }
  .mango-ui-step-node-form.is-compact
    :deep(.arco-form-item.is-compact-half .arco-form-item-label-col) {
    width: 64px;
    flex-basis: 64px;
  }
  .mango-ui-step-node-form.is-compact
    :deep(.arco-form-item.is-compact-half .arco-form-item-wrapper-col) {
    width: calc(100% - 64px);
  }
  .mango-ui-step-node-form.is-compact
    :deep(.arco-form-item.is-compact-narrow .arco-form-item-label-col) {
    width: 48px;
    flex-basis: 48px;
  }
  .mango-ui-step-node-form.is-compact
    :deep(.arco-form-item.is-compact-narrow .arco-form-item-wrapper-col) {
    width: calc(100% - 48px);
  }
  .mango-ui-step-node-form.is-compact
    :deep(.arco-form-item.is-compact-wide-label .arco-form-item-label-col) {
    width: 88px;
    flex-basis: 88px;
  }
  .mango-ui-step-node-form.is-compact
    :deep(.arco-form-item.is-compact-wide-label .arco-form-item-wrapper-col) {
    width: calc(100% - 88px);
  }
  .mango-ui-step-node-form.is-compact :deep(.arco-form-item-label-col) {
    width: 88px;
    flex: 0 0 88px;
    padding-right: 10px;
  }
  .mango-ui-step-node-form.is-compact :deep(.arco-form-item-label) {
    justify-content: flex-start;
    white-space: nowrap;
  }
  .mango-ui-step-node-form.is-compact :deep(.arco-form-item-wrapper-col) {
    width: calc(100% - 88px);
    min-width: 0;
    flex: 1;
  }
  .mango-ui-step-node-form__inherited {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .mango-ui-step-node-form__inherited span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
