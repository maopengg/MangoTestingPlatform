<template>
  <div class="mango-mock-condition-editor">
    <div class="mango-mock-editor-toolbar">
      <span class="mango-mock-editor-tip">{{
        mode === 'assertion'
          ? '所有断言都会执行；失败只记录，不改变响应。'
          : '规则内条件需全部满足。'
      }}</span>
      <a-button size="small" type="primary" :disabled="disabled" @click="addItem"
        >增加{{ mode === 'assertion' ? '断言' : '条件' }}</a-button
      >
    </div>
    <a-table
      v-if="rows.length"
      :data="rows"
      :pagination="false"
      :bordered="false"
      :scroll="{ x: 1160 }"
      row-key="key"
    >
      <template #columns>
        <a-table-column title="名称" :width="170">
          <template #cell="{ record }"
            ><a-input
              :disabled="disabled"
              :model-value="record.name"
              @update:model-value="updateField(record.key, 'name', $event)"
              placeholder="请输入名称"
          /></template>
        </a-table-column>
        <a-table-column title="数据来源" :width="140">
          <template #cell="{ record }"
            ><a-select
              :disabled="disabled"
              :model-value="record.source"
              @update:model-value="updateField(record.key, 'source', $event)"
              :options="sourceOptions"
          /></template>
        </a-table-column>
        <a-table-column title="字段/JSONPath" :width="220">
          <template #cell="{ record }"
            ><a-input
              :model-value="record.field"
              @update:model-value="updateField(record.key, 'field', $event)"
              :disabled="disabled || record.source === 'text_body'"
              placeholder="如 user_id 或 $.data.id"
          /></template>
        </a-table-column>
        <a-table-column title="校验方式" :width="190">
          <template #cell="{ record }">
            <a-cascader
              :model-value="record.operator"
              :disabled="disabled"
              :options="assertionOperatorOptions"
              :loading="methodsLoading"
              allow-search
              placeholder="请选择断言方式"
              @change="(value) => updateOperator(record.key, value)"
            />
          </template>
        </a-table-column>
        <a-table-column title="期望值" :width="200">
          <template #cell="{ record }"
            ><a-input
              :model-value="expectedText(record.expected)"
              @update:model-value="updateField(record.key, 'expected', $event)"
              :disabled="disabled || !requiresExpected(record.operator)"
              placeholder="请输入期望值，JSON可直接填写对象或数组"
          /></template>
        </a-table-column>
        <a-table-column title="启用" :width="80" align="center">
          <template #cell="{ record }"
            ><a-switch
              :disabled="disabled"
              :model-value="record.enabled"
              @update:model-value="updateField(record.key, 'enabled', $event)"
          /></template>
        </a-table-column>
        <a-table-column title="操作" :width="160" align="center" fixed="right">
          <template #cell="{ rowIndex }"
            ><MangoTableActions
              :actions="[
                { label: '删除', danger: true, disabled, onClick: () => removeItem(rowIndex) },
              ]"
          /></template>
        </a-table-column>
      </template>
    </a-table>
    <div v-else class="mango-empty-state"
      >暂无{{ mode === 'assertion' ? '请求断言' : '匹配条件' }}</div
    >
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { cloneLosslessJson, stringifyLosslessJson } from '@/utils/lossless-json'
  import type { MockAssertionMethodOption, MockCondition } from '@/api/apitest/mock'
  import { sourceOptions } from '../config'
  import { editorKey } from '../form'
  const props = withDefaults(
    defineProps<{
      modelValue: MockCondition[]
      mode: 'assertion' | 'matcher'
      assertionMethods?: MockAssertionMethodOption[]
      methodsLoading?: boolean
      disabled?: boolean
    }>(),
    { assertionMethods: () => [], methodsLoading: false, disabled: false }
  )
  const emit = defineEmits<{ (event: 'update:modelValue', value: MockCondition[]): void }>()
  const rows = ref(cloneLosslessJson(props.modelValue))
  watch(
    () => props.modelValue,
    (value) => {
      rows.value = cloneLosslessJson(value)
    },
    { flush: 'sync' }
  )
  const assertionOperatorOptions = computed(() => props.assertionMethods)
  const expectedFreeOperators = computed(() => {
    const result = new Set<string>()
    function walk(items: MockAssertionMethodOption[]) {
      for (const item of items) {
        if (item.children?.length) walk(item.children)
        else if (item.requires_expected === false) result.add(item.value)
      }
    }
    walk(props.assertionMethods)
    return result
  })
  function publish() {
    emit('update:modelValue', cloneLosslessJson(rows.value))
  }
  function requiresExpected(operator: string) {
    return !expectedFreeOperators.value.has(operator)
  }
  function expectedText(value: unknown) {
    return typeof value === 'string'
      ? value
      : value === undefined
      ? ''
      : stringifyLosslessJson(value)
  }
  function updateField<K extends keyof MockCondition>(
    key: string,
    field: K,
    value: MockCondition[K]
  ) {
    if (props.disabled) return
    const record = rows.value.find((item) => item.key === key)
    if (!record) return
    Object.assign(record, { [field]: value })
    publish()
  }
  function updateOperator(key: string, value: unknown) {
    if (props.disabled) return
    const record = rows.value.find((item) => item.key === key)
    if (!record) return
    record.operator = String(Array.isArray(value) ? value[value.length - 1] : value)
    if (!requiresExpected(record.operator)) record.expected = ''
    publish()
  }
  function addItem() {
    if (props.disabled) return
    rows.value.push({
      key: editorKey('condition'),
      name: '',
      enabled: true,
      source: 'query',
      field: '',
      operator: 'p_is_not_none',
      expected: '',
    })
    publish()
  }
  function removeItem(index: number) {
    if (props.disabled) return
    rows.value.splice(index, 1)
    publish()
  }
</script>
<style scoped>
  .mango-mock-condition-editor {
    min-width: 0;
  }
  .mango-mock-editor-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
  }
  .mango-mock-editor-tip {
    color: var(--m-muted);
  }
</style>
