<template>
  <div class="mango-mock-condition-editor mango-horizontal-scroll-region">
    <div class="mango-mock-editor-toolbar">
      <span class="mango-mock-editor-tip">{{ mode === 'assertion' ? '所有断言都会执行；失败只记录，不改变响应。' : '规则内条件需全部满足。' }}</span>
      <a-button size="small" type="primary" @click="addItem">增加{{ mode === 'assertion' ? '断言' : '条件' }}</a-button>
    </div>
    <a-table v-if="modelValue.length" :data="modelValue" :pagination="false" :bordered="false" :scroll="{ x: 1090 }" row-key="key">
      <template #columns>
        <a-table-column title="名称" :width="170">
          <template #cell="{ record }"><a-input v-model="record.name" placeholder="请输入名称" /></template>
        </a-table-column>
        <a-table-column title="数据来源" :width="140">
          <template #cell="{ record }"><a-select v-model="record.source" :options="sourceOptions" /></template>
        </a-table-column>
        <a-table-column title="字段/JSONPath" :width="220">
          <template #cell="{ record }"><a-input v-model="record.field" :disabled="record.source === 'text_body'" placeholder="如 user_id 或 $.data.id" /></template>
        </a-table-column>
        <a-table-column title="校验方式" :width="190">
          <template #cell="{ record }">
            <a-cascader
              v-model="record.operator"
              :options="assertionOperatorOptions"
              :loading="methodsLoading"
              allow-search
              placeholder="请选择断言方式"
              @change="handleOperatorChange(record)"
            />
          </template>
        </a-table-column>
        <a-table-column title="期望值" :width="200">
          <template #cell="{ record }"><a-input v-model="record.expected" :disabled="!requiresExpected(record.operator)" placeholder="请输入期望值，JSON可直接填写对象或数组" /></template>
        </a-table-column>
        <a-table-column title="启用" :width="80" align="center">
          <template #cell="{ record }"><a-switch v-model="record.enabled" size="small" /></template>
        </a-table-column>
        <a-table-column title="操作" :width="90" align="center" fixed="right">
          <template #cell="{ rowIndex }"><a-button  type="text" status="danger" @click="removeItem(rowIndex)">删除</a-button></template>
        </a-table-column>
      </template>
    </a-table>
    <a-empty v-else :description="`暂无${mode === 'assertion' ? '请求断言' : '匹配条件'}`" />
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import type { MockAssertionMethodOption, MockCondition } from '@/api/apitest/mock'

  const props = withDefaults(defineProps<{
    modelValue: MockCondition[]
    mode: 'assertion' | 'matcher'
    assertionMethods?: MockAssertionMethodOption[]
    methodsLoading?: boolean
  }>(), {
    assertionMethods: () => [],
    methodsLoading: false,
  })
  const emit = defineEmits<{ (event: 'update:modelValue', value: MockCondition[]): void }>()
  const sourceOptions = [
    { label: 'Path参数', value: 'path' }, { label: 'Query参数', value: 'query' },
    { label: '请求头', value: 'header' }, { label: 'JSON请求体', value: 'json_body' },
    { label: '文本请求体', value: 'text_body' },
  ]
  const assertionOperatorOptions = computed(() => props.assertionMethods)
  const expectedFreeOperators = computed(() => {
    const result = new Set<string>()
    const walk = (items: MockAssertionMethodOption[]) => {
      items.forEach((item) => {
        if (item.children?.length) walk(item.children)
        else if (item.requires_expected === false) result.add(item.value)
      })
    }
    walk(props.assertionMethods)
    return result
  })
  const key = () => `condition-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`

  function addItem() {
    emit('update:modelValue', [...props.modelValue, {
      key: key(), name: '', enabled: true, source: 'query', field: '', operator: 'p_is_not_none', expected: '',
    }])
  }
  function requiresExpected(operator: string) {
    return !expectedFreeOperators.value.has(operator)
  }
  function handleOperatorChange(record: MockCondition) {
    if (!requiresExpected(record.operator)) record.expected = ''
  }
  function removeItem(index: number) {
    emit('update:modelValue', props.modelValue.filter((_, itemIndex) => itemIndex !== index))
  }
</script>

<style scoped>
  .mango-mock-condition-editor { min-width: 0; }
  .mango-mock-editor-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
  .mango-mock-editor-tip { color: var(--m-muted); }
</style>
