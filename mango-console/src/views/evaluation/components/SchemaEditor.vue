<template>
  <div class="mango-schema-editor">
    <a-table class="mango-native-scroll-table" :data="rows" :columns="columns" :pagination="false" :scroll="{ x: 910, y: 360 }" size="small" row-key="key">
      <template #title="{ record }"><span v-if="readonly" class="mango-schema-value" :title="record.spec.title">{{ record.spec.title || '—' }}</span><a-input v-else size="small" :model-value="record.spec.title" :disabled="disabled" placeholder="显示名称" @update:model-value="update(record.key, { title: $event })" /></template>
      <template #type="{ record }"><span v-if="readonly">{{ types.find(item => item.value === (record.spec.type || 'string'))?.label || record.spec.type }}</span><a-select v-else size="small" :model-value="record.spec.type || 'string'" :options="types" :disabled="disabled" @change="update(record.key, { type: $event })" /></template>
      <template #required="{ record }"><span v-if="readonly">{{ (modelValue?.required || []).includes(record.key) ? '必填' : '可选' }}</span><a-switch v-else size="small" :disabled="disabled" :model-value="(modelValue?.required || []).includes(record.key)" @change="requireField(record.key, Boolean($event))" /></template>
      <template #description="{ record }"><span v-if="readonly" class="mango-schema-value" :title="record.spec.description">{{ record.spec.description || '—' }}</span><a-input v-else size="small" :model-value="record.spec.description" :disabled="disabled" placeholder="字段用途" @update:model-value="update(record.key, { description: $event })" /></template>
      <template #actions="{ record }"><MangoTableActions :actions="[{ label: selected === record.key ? '收起' : readonly ? '查看约束' : '配置', permission: 'evaluation.dataset:detail', onClick: () => selected = selected === record.key ? '' : record.key }, { label: '移除', permission: 'evaluation.dataset:edit', hidden: disabled || readonly, danger: true, onClick: () => remove(record.key) }]" /></template>
    </a-table>
    <div v-if="selected && modelValue?.properties?.[selected]" class="mango-schema-constraints">
      <div class="mango-section-title">{{ selected }} · 字段约束</div>
      <DataFieldsEditor :model-value="modelValue.properties[selected]" :disabled="disabled || readonly" @update:model-value="replace(selected, $event)" />
      <SchemaEditor v-if="modelValue.properties[selected].type === 'object'" :readonly="readonly" :disabled="disabled" :model-value="modelValue.properties[selected]" @update:model-value="replace(selected, $event)" />
      <SchemaEditor v-if="modelValue.properties[selected].type === 'array' && modelValue.properties[selected].items?.type === 'object'" :readonly="readonly" :disabled="disabled" :model-value="modelValue.properties[selected].items" @update:model-value="update(selected, { items: $event })" />
    </div>
    <div v-if="!disabled && !readonly" class="mango-schema-add"><a-input v-model="newKey" size="small" placeholder="新字段名称" aria-label="新增字段名称" /><a-select v-model="newType" size="small" :options="types" aria-label="字段类型" /><a-button v-permission="'evaluation.dataset:edit'" size="small" @click="add">添加字段</a-button></div>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import DataFieldsEditor from './DataFieldsEditor.vue'
  const props = withDefaults(defineProps<{ modelValue: any; disabled?: boolean; readonly?: boolean }>(), { disabled: false, readonly: false })
  const emit = defineEmits<{ (event: 'update:modelValue', value: any): void }>()
  const newKey = ref(''), newType = ref('string'), selected = ref('')
  const types = ['string', 'number', 'integer', 'boolean', 'object', 'array', 'null'].map(value => ({ value, label: ({ string: '文本', number: '数字', integer: '整数', boolean: '布尔', object: '对象', array: '列表', null: '空值' } as any)[value] }))
  const columns = [{ title: '字段名称', dataIndex: 'key', width: 150, ellipsis: true, tooltip: true }, { title: '显示名称', slotName: 'title', width: 160 }, { title: '说明', slotName: 'description', width: 220 }, { title: '类型', slotName: 'type', width: 150, align: 'center' }, { title: '必填', slotName: 'required', width: 70, align: 'center' }, { title: '操作', slotName: 'actions', width: 160, fixed: 'right', align: 'center' }]
  const rows = computed(() => Object.entries(props.modelValue?.properties || {}).map(([key, spec]) => ({ key, spec })))
  function replace(key: string, value: any) { if (props.disabled || props.readonly) return; emit('update:modelValue', { ...props.modelValue, type: 'object', properties: { ...props.modelValue?.properties, [key]: value } }) }
  function update(key: string, value: any) { replace(key, { ...props.modelValue?.properties?.[key], ...value }) }
  function add() { const key = newKey.value.trim(); if (!key || Object.prototype.hasOwnProperty.call(props.modelValue?.properties || {}, key)) { Message.warning('请输入不重复的字段编码'); return }; replace(key, { type: newType.value, ...(newType.value === 'array' ? { items: { type: 'string' } } : {}) }); newKey.value = '' }
  function requireField(key: string, required: boolean) { if (props.disabled || props.readonly) return; const values = new Set<string>(props.modelValue?.required || []); required ? values.add(key) : values.delete(key); emit('update:modelValue', { ...props.modelValue, required: [...values] }) }
  function remove(key: string) { if (props.disabled || props.readonly) return; const properties = { ...props.modelValue?.properties }; delete properties[key]; emit('update:modelValue', { ...props.modelValue, properties, required: (props.modelValue?.required || []).filter((item: string) => item !== key) }); if (selected.value === key) selected.value = '' }
</script>
<style scoped>
  .mango-schema-editor { min-width: 0; }
  .mango-schema-value { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-schema-add { display: grid; grid-template-columns: minmax(0, 1fr) minmax(80px, 120px) auto; gap: var(--m-page-gap); margin-top: var(--m-page-gap); align-items: center; }
  .mango-schema-constraints { padding-top: var(--m-card-padding); border-top: 1px solid var(--m-border); margin-top: var(--m-page-gap); }
</style>
