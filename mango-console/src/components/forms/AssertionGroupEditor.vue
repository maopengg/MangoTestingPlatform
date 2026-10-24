<template>
  <div class="mango-assertion-group-editor">
    <div class="mango-assertion-group-editor__summary">
      <span>组内且/或 · 组间按且 · JSON 保持原类型</span>
      <a-button size="mini" :disabled="disabled" @click="addGroup" data-testid="qa-components-forms-assertiongroupeditor-button-增加断言组">增加断言组</a-button>
    </div>

    <section
      v-for="(group, groupIndex) in modelValue"
      :key="group.id"
      class="mango-assertion-group-editor__group"
    >
      <header class="mango-assertion-group-editor__group-header">
        <div class="mango-assertion-group-editor__group-identity">
          <span class="mango-assertion-group-editor__group-index">组{{ groupIndex + 1 }}</span>
          <a-input
            :model-value="group.name"
            :disabled="disabled"
            placeholder="请输入断言组名称"
            class="mango-assertion-group-editor__group-name"
            @update:model-value="updateGroup(groupIndex, { name: $event })" data-testid="qa-components-forms-assertiongroupeditor-input-请输入断言组名称"
          />
        </div>
        <div class="mango-assertion-group-editor__group-actions">
          <a-radio-group
            :model-value="group.logic"
            type="button"
            size="small"
            :disabled="disabled"
            @change="updateGroup(groupIndex, { logic: $event as 'AND' | 'OR' })"
          >
            <a-radio value="AND" data-testid="qa-components-forms-assertiongroupeditor-radio-且">且</a-radio>
            <a-radio value="OR" data-testid="qa-components-forms-assertiongroupeditor-radio-或">或</a-radio>
          </a-radio-group>
          <a-button
            size="mini"
            type="text"
            status="danger"
            :disabled="disabled || modelValue.length <= 1"
            @click="removeGroup(groupIndex)" data-testid="qa-components-forms-assertiongroupeditor-button-删除"
          >
            删除
          </a-button>
        </div>
      </header>

      <div class="mango-assertion-group-editor__items">
        <article
          v-for="(item, itemIndex) in group.assertions"
          :key="item.id"
          class="mango-assertion-group-editor__item"
        >
          <div class="mango-assertion-group-editor__item-header">
            <div class="mango-assertion-group-editor__method-select">
              <span>{{ itemIndex + 1 }}</span>
              <a-cascader
                :model-value="item.method"
                :options="scopedMethods"
                :disabled="disabled"
                allow-search
                expand-trigger="hover"
                placeholder="请选择断言方法"
                @change="changeMethod(groupIndex, itemIndex, String($event || ''))" data-testid="qa-components-forms-assertiongroupeditor-cascader-请选择断言方法"
              />
            </div>
            <div class="mango-assertion-group-editor__item-actions">
              <a-tooltip
                v-if="methodTestDisabledReason(item.method)"
                :content="methodTestDisabledReason(item.method)"
              >
                <a-tag size="small" color="gray">仅运行时验证</a-tag>
              </a-tooltip>
              <a-button
                v-if="showJsonEditorButton && jsonParameters(item.method).length"
                size="mini"
                type="text"
                :disabled="disabled"
                @click="openJsonEditor(groupIndex, itemIndex)" data-testid="qa-components-forms-assertiongroupeditor-button-编辑-json"
              >
                编辑 JSON
              </a-button>
              <a-button
                v-if="itemIndex === group.assertions.length - 1"
                size="mini"
                type="text"
                :disabled="disabled"
                @click="addAssertion(groupIndex)" data-testid="qa-components-forms-assertiongroupeditor-button-增加断言"
              >
                增加断言
              </a-button>
              <a-button
                size="mini"
                type="text"
                status="danger"
                :disabled="disabled"
                @click="removeAssertion(groupIndex, itemIndex)" data-testid="qa-components-forms-assertiongroupeditor-button-移除"
              >
                移除
              </a-button>
            </div>
          </div>

          <div
            v-if="visibleParameters(item.method).length"
            class="mango-assertion-group-editor__parameters"
          >
            <AssertionParameterEditor
              v-for="parameter in visibleParameters(item.method)"
              :key="`${item.method}-${parameter.f}`"
              :model-value="item.values[parameter.f]"
              :parameter="parameter"
              :disabled="disabled"
              @update:model-value="updateParameterValue(groupIndex, itemIndex, parameter.f, $event)"
            />
          </div>
          <div
            v-else-if="item.method && !visibleParameters(item.method).length"
            class="mango-assertion-group-editor__no-parameter"
          >
            当前断言无需配置参数
          </div>
        </article>

        <div
          v-if="!group.assertions.length"
          class="mango-assertion-group-editor__empty mango-empty-state"
        >
          <span>当前组暂无断言</span>
          <a-button size="mini" type="text" :disabled="disabled" @click="addAssertion(groupIndex)" data-testid="qa-components-forms-assertiongroupeditor-button-增加断言-2">
            增加断言
          </a-button>
        </div>
      </div>
    </section>

    <a-drawer
      v-model:visible="jsonEditorVisible"
      title="编辑断言 JSON"
      width="50%"
      unmount-on-close
    >
      <div class="mango-assertion-json-editor">
        <section
          v-for="parameter in jsonEditorTarget?.parameters || []"
          :key="parameter.f"
          class="mango-assertion-json-editor__pane"
        >
          <header>{{ parameter.f === 'actual' ? '实际值' : '预期值' }}</header>
          <MangoJsonEditor
            v-model="jsonEditorDrafts[parameter.f]"
            :placeholder="`请输入${parameter.f === 'actual' ? '实际值' : '预期值'} JSON`"
            min-height="calc((100vh - 240px) / 2)"
          />
        </section>
      </div>
      <template #footer>
        <div class="mango-assertion-json-editor__footer">
          <a-button size="small" @click="jsonEditorVisible = false" data-testid="qa-components-forms-assertiongroupeditor-button-取消">取消</a-button>
          <a-button size="small" type="primary" @click="saveJsonEditor" data-testid="qa-components-forms-assertiongroupeditor-button-保存">保存</a-button>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import MangoJsonEditor from '@/components/editors/MangoJsonEditor.vue'
  import AssertionParameterEditor from '@/components/forms/AssertionParameterEditor.vue'
  import type {
    AssertionEditorGroup,
    AssertionEditorItem,
    AssertionMethodItem,
    AssertionMethodParameter,
    AssertionMethodScope,
    AssertionTestAvailability,
    AssertionMethodTypeGroup,
  } from '@/types/assertion'

  const props = withDefaults(
    defineProps<{
      modelValue: AssertionEditorGroup[]
      methods: AssertionMethodTypeGroup[]
      methodScopes?: AssertionMethodScope[]
      disabled?: boolean
    }>(),
    {
      disabled: false,
      methodScopes: () => ['public'],
    }
  )

  const emit = defineEmits<{
    (event: 'update:modelValue', value: AssertionEditorGroup[]): void
    (event: 'testability-change', value: AssertionTestAvailability): void
  }>()

  // 暂时隐藏入口，保留抽屉与编辑逻辑，后续开放时只需恢复此开关。
  const showJsonEditorButton = false

  let sequence = 0
  function createId(prefix: string) {
    sequence += 1
    return `${prefix}-${Date.now()}-${sequence}`
  }

  const scopedMethods = computed(() =>
    props.methods.filter(
      (typeGroup) => !typeGroup.scope || props.methodScopes.includes(typeGroup.scope)
    )
  )

  const flatMethods = computed(() =>
    scopedMethods.value.flatMap((typeGroup) =>
      (typeGroup.children || []).flatMap((classGroup) => classGroup.children || [])
    )
  )
  const methodMap = computed(
    () => new Map(flatMethods.value.map((method) => [method.value, method]))
  )

  const testAvailability = computed<AssertionTestAvailability>(() => {
    const unavailable = props.modelValue
      .flatMap((group) => group.assertions)
      .map((item) => methodMap.value.get(item.method))
      .find((method) => method?.testable === false)
    return unavailable
      ? {
          allowed: false,
          reason: unavailable.test_disabled_reason || '当前断言只能在用例运行时验证',
        }
      : { allowed: true, reason: '' }
  })

  watch(
    testAvailability,
    (value, previousValue) => {
      if (
        previousValue &&
        previousValue.allowed === value.allowed &&
        previousValue.reason === value.reason
      ) {
        return
      }
      emit('testability-change', value)
    },
    { immediate: true }
  )

  function methodTestDisabledReason(methodValue: string) {
    const method = methodMap.value.get(methodValue)
    return method?.testable === false ? method.test_disabled_reason || '只能在用例运行时验证' : ''
  }

  function cloneGroups() {
    return props.modelValue.map((group) => ({
      ...group,
      assertions: group.assertions.map((item) => ({
        ...item,
        values: { ...item.values },
      })),
    }))
  }

  function parseStructuredExample(value: unknown) {
    if (value && typeof value === 'object') return value
    if (typeof value !== 'string') return value
    const text = value.trim()
    if (!text.startsWith('{') && !text.startsWith('[')) return value
    try {
      return JSON.parse(text)
    } catch {
      return value
    }
  }

  function cleanExample(value: unknown): unknown {
    if (Array.isArray(value)) return value.map((item) => cleanExample(item))
    if (value && typeof value === 'object') {
      return Object.fromEntries(
        Object.entries(value as Record<string, unknown>).map(([key, item]) => [
          key,
          cleanExample(item),
        ])
      )
    }
    if (typeof value === 'string' && value.startsWith('请输入')) return ''
    return value
  }

  function exampleValue(parameter: AssertionMethodParameter) {
    const parsed = cleanExample(parseStructuredExample(parameter.v))
    if (parameter.example_as_placeholder) {
      if (parameter.value_type === 'array') return []
      if (parameter.value_type === 'object' || parameter.value_type === 'json') return {}
      if (parsed && typeof parsed === 'object') return Array.isArray(parsed) ? [] : {}
      return ''
    }
    if (parameter.value_type === 'number') {
      const value = Number(parsed)
      return Number.isFinite(value) ? value : 0
    }
    if (parameter.value_type === 'boolean') return Boolean(parsed)
    if (parameter.value_type === 'null') return null
    if (parameter.value_type === 'array') return Array.isArray(parsed) ? parsed : []
    if (parameter.value_type === 'object') {
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    }
    if (parameter.value_type === 'json') {
      return parsed && typeof parsed === 'object' ? parsed : {}
    }
    return parsed ?? ''
  }

  function valuesForMethod(methodValue: string) {
    const method = methodMap.value.get(methodValue)
    return Object.fromEntries(
      (method?.parameter || []).map((parameter) => [parameter.f, exampleValue(parameter)])
    )
  }

  function createAssertion(methodValue = flatMethods.value[0]?.value || ''): AssertionEditorItem {
    return {
      id: createId('assertion'),
      method: methodValue,
      values: valuesForMethod(methodValue),
    }
  }

  function createGroup(index: number): AssertionEditorGroup {
    return {
      id: createId('group'),
      name: `断言组${index + 1}`,
      logic: 'AND',
      assertions: [createAssertion()],
    }
  }

  function visibleParameters(methodValue: string) {
    return (methodMap.value.get(methodValue)?.parameter || []).filter(
      (parameter) => parameter.d !== false
    )
  }

  function isStructuredParameter(parameter: AssertionMethodParameter) {
    if (['object', 'array', 'json'].includes(parameter.value_type || '')) return true
    if (['json', 'object'].includes(parameter.input_type || '')) return true
    const example = parseStructuredExample(parameter.v)
    return Boolean(example && typeof example === 'object')
  }

  function jsonParameters(methodValue: string) {
    return visibleParameters(methodValue).filter(
      (parameter) => ['actual', 'expect'].includes(parameter.f) && isStructuredParameter(parameter)
    )
  }

  const jsonEditorVisible = ref(false)
  const jsonEditorDrafts = ref<Record<string, string>>({})
  const jsonEditorTarget = ref<{
    groupIndex: number
    itemIndex: number
    parameters: AssertionMethodParameter[]
  } | null>(null)

  function normalizeJsonEditorValue(value: unknown) {
    if (value && typeof value === 'object') return value
    if (typeof value !== 'string' || !value.trim()) return value ?? null
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  }

  function openJsonEditor(groupIndex: number, itemIndex: number) {
    const item = props.modelValue[groupIndex].assertions[itemIndex]
    const parameters = jsonParameters(item.method)
    jsonEditorTarget.value = { groupIndex, itemIndex, parameters }
    jsonEditorDrafts.value = Object.fromEntries(
      parameters.map((parameter) => [
        parameter.f,
        JSON.stringify(normalizeJsonEditorValue(item.values[parameter.f]), null, 2),
      ])
    )
    jsonEditorVisible.value = true
  }

  function validateJsonParameter(parameter: AssertionMethodParameter, value: unknown) {
    if (parameter.value_type === 'array') return Array.isArray(value)
    if (parameter.value_type === 'object') {
      return Boolean(value && typeof value === 'object' && !Array.isArray(value))
    }
    return Boolean(value && typeof value === 'object')
  }

  function saveJsonEditor() {
    const target = jsonEditorTarget.value
    if (!target) return
    try {
      const parsedValues: Record<string, unknown> = {}
      for (const parameter of target.parameters) {
        const parsed = JSON.parse(jsonEditorDrafts.value[parameter.f] || '')
        if (!validateJsonParameter(parameter, parsed)) {
          Message.error(`${parameter.n || parameter.f} 的 JSON 类型不正确`)
          return
        }
        parsedValues[parameter.f] = parsed
      }
      const groups = cloneGroups()
      const item = groups[target.groupIndex].assertions[target.itemIndex]
      target.parameters.forEach((parameter) => {
        item.values[parameter.f] = parsedValues[parameter.f]
      })
      emit('update:modelValue', groups)
      jsonEditorVisible.value = false
      Message.success('实际值和预期值已更新')
    } catch (error) {
      Message.error(`JSON格式错误：${error instanceof Error ? error.message : String(error)}`)
    }
  }

  function updateGroup(index: number, patch: Partial<AssertionEditorGroup>) {
    const groups = cloneGroups()
    groups[index] = { ...groups[index], ...patch }
    emit('update:modelValue', groups)
  }

  function addGroup() {
    emit('update:modelValue', [...cloneGroups(), createGroup(props.modelValue.length)])
  }

  function removeGroup(index: number) {
    const groups = cloneGroups()
    groups.splice(index, 1)
    emit('update:modelValue', groups)
  }

  function addAssertion(groupIndex: number) {
    const groups = cloneGroups()
    groups[groupIndex].assertions.push(createAssertion())
    emit('update:modelValue', groups)
  }

  function removeAssertion(groupIndex: number, itemIndex: number) {
    const groups = cloneGroups()
    groups[groupIndex].assertions.splice(itemIndex, 1)
    emit('update:modelValue', groups)
  }

  function changeMethod(groupIndex: number, itemIndex: number, methodValue: string) {
    const groups = cloneGroups()
    groups[groupIndex].assertions[itemIndex] = {
      ...groups[groupIndex].assertions[itemIndex],
      method: methodValue,
      values: valuesForMethod(methodValue),
    }
    emit('update:modelValue', groups)
  }

  function updateParameterValue(
    groupIndex: number,
    itemIndex: number,
    field: string,
    value: unknown
  ) {
    const groups = cloneGroups()
    const item = groups[groupIndex].assertions[itemIndex]
    item.values = { ...item.values, [field]: value }
    emit('update:modelValue', groups)
  }

  function fillExamples() {
    const groups = cloneGroups().map((group) => ({
      ...group,
      assertions: group.assertions.map((item) => ({
        ...item,
        values: valuesForMethod(item.method),
      })),
    }))
    emit('update:modelValue', groups)
  }

  function clearValues() {
    const groups = cloneGroups().map((group) => ({
      ...group,
      assertions: group.assertions.map((item) => ({
        ...item,
        values: Object.fromEntries(
          visibleParameters(item.method).map((parameter) => [
            parameter.f,
            parameter.value_type === 'array'
              ? []
              : parameter.value_type === 'object' || parameter.value_type === 'json'
              ? {}
              : parameter.value_type === 'null'
              ? null
              : '',
          ])
        ),
      })),
    }))
    emit('update:modelValue', groups)
  }

  function setSingleMethod(methodValue: string) {
    emit('update:modelValue', [
      {
        id: createId('group'),
        name: '断言组1',
        logic: 'AND',
        assertions: [createAssertion(methodValue)],
      },
    ])
  }

  defineExpose({
    fillExamples,
    clearValues,
    setSingleMethod,
    testAvailability,
  })
</script>

<style scoped lang="less">
  .mango-assertion-group-editor {
    container: mango-assertion-editor / inline-size;
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 8px;
  }

  .mango-assertion-group-editor__summary,
  .mango-assertion-group-editor__group-header,
  .mango-assertion-group-editor__group-identity,
  .mango-assertion-group-editor__group-actions,
  .mango-assertion-group-editor__item-header,
  .mango-assertion-group-editor__method-select,
  .mango-assertion-group-editor__item-actions {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .mango-assertion-group-editor__summary,
  .mango-assertion-group-editor__group-header,
  .mango-assertion-group-editor__item-header {
    justify-content: space-between;
  }

  .mango-assertion-group-editor__summary {
    color: var(--m-text);
  }

  .mango-assertion-group-editor__summary span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-assertion-group-editor__group {
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-assertion-group-editor__group-header {
    padding: 6px 8px;
    background: var(--m-surface-soft);
  }

  .mango-assertion-group-editor__group-header {
    border-bottom: 1px solid var(--m-border);
  }

  .mango-assertion-group-editor__group-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    color: var(--m-text-2);
    font-size: 12px;
    font-weight: 600;
  }

  .mango-assertion-group-editor__group-name {
    width: 160px;
  }

  .mango-assertion-group-editor__items {
    display: flex;
    flex-direction: column;
    gap: 0;
    padding: 0 8px;
  }

  .mango-assertion-group-editor__item {
    padding: 8px 0;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-assertion-group-editor__item:last-child {
    border-bottom: 0;
  }

  .mango-assertion-group-editor__method-select {
    min-width: 0;
  }

  .mango-assertion-group-editor__method-select > span {
    flex: 0 0 auto;
    color: var(--m-text-2);
    font-size: 12px;
    font-weight: 600;
  }

  .mango-assertion-group-editor__method-select :deep(.arco-cascader) {
    width: min(360px, 48vw);
  }

  .mango-assertion-group-editor__parameters {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 8px;
    padding-left: 22px;
  }

  .mango-assertion-group-editor__no-parameter {
    margin-top: 6px;
    padding-left: 22px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-assertion-group-editor__empty {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 6px;
    min-height: 42px;
  }

  .mango-assertion-json-editor {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    grid-auto-rows: minmax(0, 1fr);
    height: 100%;
    min-height: 0;
    gap: 12px;
  }

  .mango-assertion-json-editor__pane {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    gap: 8px;
  }

  .mango-assertion-json-editor__pane header {
    flex: 0 0 auto;
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-assertion-json-editor__footer {
    display: flex;
    justify-content: flex-start;
    gap: 8px;
    width: 100%;
  }

  @container mango-assertion-editor (max-width: 620px) {
    .mango-assertion-group-editor__group-header,
    .mango-assertion-group-editor__item-header {
      align-items: center;
    }

    .mango-assertion-group-editor__group-name {
      width: auto;
      min-width: 0;
    }

    .mango-assertion-group-editor__group-identity {
      min-width: 0;
      flex: 1;
    }

    .mango-assertion-group-editor__group-actions {
      flex: 0 0 auto;
    }

    .mango-assertion-group-editor__method-select {
      flex: 1;
    }

    .mango-assertion-group-editor__method-select :deep(.arco-cascader) {
      width: auto;
      min-width: 0;
      flex: 1;
    }

    .mango-assertion-group-editor__parameters {
      padding-left: 20px;
    }
  }
</style>
