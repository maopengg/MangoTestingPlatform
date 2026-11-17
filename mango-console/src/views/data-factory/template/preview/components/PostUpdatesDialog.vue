<template>
  <a-modal v-model:visible="visible" title="插入后回写" :width="920" :footer="false">
    <a-alert type="info" class="mango-post-update-alert">
      适用于两张表互相引用的场景。全部数据创建完成后，系统会把来源记录的真实字段值写入目标记录，并且只更新本次执行创建的那一条数据。
    </a-alert>
    <div class="mango-post-update-list" :inert="props.disabled ? '' : undefined">
      <section
        v-for="(item, index) in draft || []"
        :key="`${item.target_node}-${item.target_field}-${index}`"
        class="mango-post-update-rule"
      >
        <header class="mango-post-update-rule-header">
          <div>
            <span class="mango-post-update-rule-title">回写规则 {{ index + 1 }}</span>
            <span class="mango-post-update-rule-summary">{{ getPostUpdateSummary(item) }}</span>
          </div>
          <a-button size="mini" type="text" status="danger" @click="removePostInsertUpdate(index)">
            删除规则
          </a-button>
        </header>

        <div class="mango-post-update-mapping">
          <div class="mango-post-update-side mango-post-update-source">
            <div class="mango-post-update-side-title">取值来源</div>
            <label class="mango-post-update-field">
              <span>来源节点</span>
              <a-select
                v-model="item.source_node"
                :options="sceneNodeOptions"
                placeholder="选择已创建的数据节点"
                allow-search
                @change="handlePostUpdateSourceNodeChange(item)"
              />
            </label>
            <label class="mango-post-update-field">
              <span>来源字段</span>
              <a-select
                v-model="item.source_field"
                :options="getPostUpdateSourceFieldOptions(item)"
                placeholder="选择要取出的字段"
                allow-search
                @change="handlePostUpdateFieldChange(item)"
              />
            </label>
          </div>

          <div class="mango-post-update-direction" aria-hidden="true">
            <span>写入</span>
            <strong>→</strong>
          </div>

          <div class="mango-post-update-side mango-post-update-target">
            <div class="mango-post-update-side-title">写入目标</div>
            <label class="mango-post-update-field">
              <span>目标节点</span>
              <a-select
                v-model="item.target_node"
                :options="sceneNodeOptions"
                placeholder="选择要更新的数据节点"
                allow-search
                @change="handlePostUpdateTargetNodeChange(item)"
              />
            </label>
            <label class="mango-post-update-field">
              <span>目标字段</span>
              <a-select
                v-model="item.target_field"
                :options="getPostUpdateTargetFieldOptions(item.target_node)"
                placeholder="仅显示可安全回写字段"
                allow-search
                @change="handlePostUpdateFieldChange(item)"
              />
            </label>
          </div>
        </div>

        <a-alert
          :type="getPostUpdateValidation(item, index).type"
          class="mango-post-update-validation"
        >
          {{ getPostUpdateValidation(item, index).message }}
        </a-alert>

        <details class="mango-post-update-advanced">
          <summary>高级设置与执行详情</summary>
          <div class="mango-post-update-advanced-content">
            <label class="mango-post-update-order-field">
              <span>执行顺序</span>
              <a-input-number
                v-model="item.sort"
                @change="publish"
                :min="0"
                placeholder="数字越小越先执行"
              />
            </label>
            <div class="mango-post-update-order-tip">存在多条回写规则时，数字越小越先执行。</div>
            <div v-if="props.checks?.[index]?.valid" class="mango-post-update-sql">
              {{ props.checks[index].sql_template }}
            </div>
          </div>
        </details>
      </section>
      <div v-if="!draft?.length" class="mango-empty-state">
        <div>暂未配置回写规则</div>
        <div class="mango-post-update-empty-tip"
          >例如：评分创建后，将评分 ID 写入状态表的当前评分结果字段。</div
        >
      </div>
    </div>
    <a-space>
      <a-button size="small" type="primary" @click="addPostInsertUpdate">添加回写规则</a-button>
      <a-button size="small" :loading="props.loading" @click="emit('check')">检查全部规则</a-button>
    </a-space>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { clone } from '../form'
  import type {
    PostUpdate,
    PostUpdateNode,
    PostUpdateResult,
    FieldRecord,
    Overrides,
  } from '../types'
  const props = defineProps<{
    modelValue: PostUpdate[]
    nodes: PostUpdateNode[]
    checks: PostUpdateResult[]
    loading: boolean
    disabled: boolean
  }>()
  const emit = defineEmits<{
    (event: 'update:modelValue', value: PostUpdate[]): void
    (event: 'check'): void
  }>()
  const visible = ref(false),
    draft = ref<PostUpdate[]>([])
  watch(
    () => props.modelValue,
    (value) => {
      draft.value = clone(value)
    },
    { immediate: true }
  )
  function open() {
    visible.value = true
  }
  function close() {
    visible.value = false
  }
  function publish() {
    if (!props.disabled) emit('update:modelValue', clone(draft.value))
  }
  const sceneNodeOptions = computed(() =>
    props.nodes.map((node) => ({ label: node.label, value: node.value }))
  )
  function getPostUpdateNodeFields(node: string): FieldRecord[] {
    return props.nodes.find((item) => item.value === node)?.fields || []
  }
  function getPostUpdateNodeOverrides(node: string): Overrides {
    return props.nodes.find((item) => item.value === node)?.overrides || {}
  }
  function getEffectiveGeneratorType(node: string, field: FieldRecord) {
    return getPostUpdateNodeOverrides(node)?.[field.name]?.generator_type ?? field.generator_type
  }

  function getPostUpdateField(node: string, fieldName: string) {
    return getPostUpdateNodeFields(node).find((field) => field.name === fieldName)
  }

  function formatPostUpdateFieldOption(node: string, field: FieldRecord) {
    const tags: string[] = []
    if (field.primary_key) tags.push('主键')
    if (field.autoincrement) tags.push('自增')
    if (field.nullable) tags.push('可空')
    if (getEffectiveGeneratorType(node, field) === 0) tags.push('已跳过')
    if (field.platform_type) tags.push(field.platform_type)
    const businessName = field.label && field.label !== field.name ? `${field.label}｜` : ''
    return `${businessName}${field.name}${tags.length ? ` · ${tags.join(' · ')}` : ''}`
  }

  function getPostUpdateTargetFieldOptions(node: string) {
    return getPostUpdateNodeFields(node)
      .filter(
        (field) =>
          field.nullable && !field.primary_key && getEffectiveGeneratorType(node, field) === 0
      )
      .map((field) => ({
        label: formatPostUpdateFieldOption(node, field),
        value: field.name,
      }))
  }

  function getPostUpdateSourceFieldOptions(item: PostUpdate) {
    const targetField = getPostUpdateField(item.target_node, item.target_field)
    return getPostUpdateNodeFields(item.source_node)
      .filter((field) => !targetField || field.platform_type === targetField.platform_type)
      .map((field) => ({
        label: formatPostUpdateFieldOption(item.source_node, field),
        value: field.name,
      }))
  }

  function getPostUpdateNodeLabel(node: string) {
    return props.nodes.find((option) => option.value === node)?.label || '未选择节点'
  }

  function getPostUpdateFieldLabel(node: string, fieldName: string) {
    const field = getPostUpdateField(node, fieldName)
    if (!field) return fieldName || '未选择字段'
    return field.label && field.label !== field.name
      ? `${field.label}（${field.name}）`
      : field.name
  }

  function getPostUpdateSummary(item: PostUpdate) {
    if (!item.source_node || !item.source_field || !item.target_node || !item.target_field) {
      return '请选择取值来源和写入目标'
    }
    return `将 ${getPostUpdateNodeLabel(item.source_node)} 的 ${getPostUpdateFieldLabel(
      item.source_node,
      item.source_field
    )} 写入 ${getPostUpdateNodeLabel(item.target_node)} 的 ${getPostUpdateFieldLabel(
      item.target_node,
      item.target_field
    )}`
  }

  function clearPostUpdatePreview() {
    publish()
  }
  function selectOnlyPostUpdateOption(
    item: PostUpdate,
    key: 'source_field' | 'target_field',
    options: Array<{ label: string; value: string }>
  ) {
    if (!options.some((option) => option.value === item[key])) {
      item[key] = options.length === 1 ? options[0].value : ''
    }
  }

  function handlePostUpdateSourceNodeChange(item: PostUpdate) {
    selectOnlyPostUpdateOption(item, 'source_field', getPostUpdateSourceFieldOptions(item))
    clearPostUpdatePreview()
  }

  function handlePostUpdateTargetNodeChange(item: PostUpdate) {
    selectOnlyPostUpdateOption(
      item,
      'target_field',
      getPostUpdateTargetFieldOptions(item.target_node)
    )
    selectOnlyPostUpdateOption(item, 'source_field', getPostUpdateSourceFieldOptions(item))
    clearPostUpdatePreview()
  }

  function handlePostUpdateFieldChange(item: PostUpdate) {
    selectOnlyPostUpdateOption(item, 'source_field', getPostUpdateSourceFieldOptions(item))
    clearPostUpdatePreview()
  }

  function getPostUpdateValidation(
    item: PostUpdate,
    index: number
  ): { type: 'warning' | 'error' | 'success' | 'info'; message: string } {
    if (!item.source_node || !item.source_field || !item.target_node || !item.target_field) {
      return { type: 'warning', message: '请完整选择来源节点、来源字段、目标节点和目标字段。' }
    }
    const targetField = getPostUpdateField(item.target_node, item.target_field)
    const sourceField = getPostUpdateField(item.source_node, item.source_field)
    if (!targetField || !sourceField) {
      return { type: 'error', message: '所选字段已不存在，请重新选择。' }
    }
    if (
      !targetField.nullable ||
      targetField.primary_key ||
      getEffectiveGeneratorType(item.target_node, targetField) !== 0
    ) {
      return {
        type: 'error',
        message: '目标字段必须可空、不能是主键，并且需要在字段规则中配置为“跳过”。',
      }
    }
    if (sourceField.platform_type !== targetField.platform_type) {
      return {
        type: 'error',
        message: `字段类型不一致：来源为 ${sourceField.platform_type}，目标为 ${targetField.platform_type}。`,
      }
    }
    const checkedResult = props.checks?.[index]
    if (checkedResult?.valid === false) {
      return { type: 'error', message: checkedResult.message || '后端检查未通过，请调整配置。' }
    }
    if (checkedResult?.valid) {
      return { type: 'success', message: '检查通过，将按本次 execution 生成的目标主键安全回写。' }
    }
    return { type: 'info', message: '配置完整，请点击“检查全部规则”确认可执行 SQL。' }
  }

  function addPostInsertUpdate() {
    if (props.disabled) return
    const item = {
      target_node: 'root',
      target_field: '',
      source_node: props.nodes[1]?.value || '',
      source_field: '',
      sort: (draft.value?.length || 0) * 10,
    }
    draft.value = [...(draft.value || []), item]
    handlePostUpdateTargetNodeChange(item)
    handlePostUpdateSourceNodeChange(item)
  }

  function removePostInsertUpdate(index: number) {
    if (props.disabled) return
    draft.value.splice(index, 1)
    publish()
    emit('check')
  }

  defineExpose({ open, close })
</script>
<style scoped>
  .mango-post-update-alert {
    margin-bottom: var(--m-page-gap);
  }

  .mango-post-update-list {
    display: flex;
    flex-direction: column;
    margin-bottom: var(--m-page-gap);
    gap: 10px;
  }

  .mango-post-update-rule {
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-post-update-rule-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    min-width: 0;
    margin-bottom: 10px;
    gap: 12px;
  }

  .mango-post-update-rule-header > div {
    display: flex;
    flex: 1;
    align-items: baseline;
    min-width: 0;
    gap: 10px;
  }

  .mango-post-update-rule-title {
    flex: none;
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-post-update-rule-summary {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-post-update-mapping {
    display: grid;
    align-items: stretch;
    min-width: 0;
    gap: 10px;
    grid-template-columns: minmax(0, 1fr) 54px minmax(0, 1fr);
  }

  .mango-post-update-side {
    display: grid;
    min-width: 0;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    gap: 8px;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .mango-post-update-side-title {
    color: var(--m-text);
    font-weight: 600;
    grid-column: 1 / -1;
  }

  .mango-post-update-source .mango-post-update-side-title {
    color: var(--m-warning);
  }

  .mango-post-update-target .mango-post-update-side-title {
    color: var(--m-primary);
  }

  .mango-post-update-field,
  .mango-post-update-order-field {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }

  .mango-post-update-field > span,
  .mango-post-update-order-field > span {
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-post-update-field :deep(.arco-select-view),
  .mango-post-update-order-field :deep(.arco-input-wrapper) {
    width: 100%;
  }

  .mango-post-update-direction {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
    flex-direction: column;
    font-size: 12px;
    gap: 2px;
  }

  .mango-post-update-direction strong {
    color: var(--m-warning);
    font-size: 22px;
    font-weight: 500;
    line-height: 1;
  }

  .mango-post-update-validation {
    margin-top: 10px;
  }

  .mango-post-update-advanced {
    margin-top: 8px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-post-update-advanced summary {
    width: fit-content;
    color: var(--m-primary);
    cursor: pointer;
    user-select: none;
  }

  .mango-post-update-advanced-content {
    display: grid;
    align-items: end;
    margin-top: 8px;
    padding: 10px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    gap: 8px 12px;
    grid-template-columns: 160px minmax(0, 1fr);
  }

  .mango-post-update-order-tip {
    padding-bottom: 7px;
    color: var(--m-muted);
  }

  .mango-post-update-sql {
    overflow-x: auto;
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-code-bg);
    color: var(--m-code-text);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    grid-column: 1 / -1;
    white-space: nowrap;
  }

  .mango-post-update-empty-tip {
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
  }

  @media (max-width: 900px) {
    .mango-post-update-mapping {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-post-update-direction strong {
      transform: rotate(90deg);
    }
  }

</style>
