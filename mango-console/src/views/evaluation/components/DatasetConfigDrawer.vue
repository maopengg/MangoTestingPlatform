<template>
  <BaseSidePanel v-model:visible="visible" title="数据集配置" :width="1100">
    <a-form v-if="version" :model="config" layout="horizontal" auto-label-width :disabled="readonly || saving" :inert="saving" class="mango-dataset-flow">
      <section class="mango-dataset-config-section">
        <h3 class="mango-dataset-config-heading">字段配置</h3>
        <section v-for="section in fieldSections" :key="section.key" class="mango-dataset-config-fields">
          <h4 class="mango-dataset-config-subtitle">{{ section.title }}</h4>
          <div class="mango-dataset-config-field-body"><SchemaEditor :model-value="config[section.key] || {}" :readonly="readonly" :disabled="readonly || saving" @update:model-value="config[section.key] = $event" /></div>
        </section>
      </section>
      <section class="mango-dataset-config-section">
        <div class="mango-dataset-config-toolbar"><h3 class="mango-dataset-config-heading">输入配置</h3><a-space><a-button size="small" :loading="previewing" :disabled="!sampleAvailable" @click="preview">预览输入变量</a-button><a-button v-if="!readonly"  size="small" @click="config.input_variables.push({ name: '', path: '$' })">添加变量</a-button></a-space></div>
        <div class="mango-dataset-config-input-body">
        <a-table size="small" class="mango-native-scroll-table" :columns="variableColumns" :data="config.input_variables" :pagination="false" :scroll="{ x: variableTableWidth, y: 240 }">
          <template #name="{ record }"><span v-if="readonly">{{ record.name }}</span><a-input v-else v-model="record.name" size="small" placeholder="如 case_input" aria-label="输入变量名称" /></template>
          <template #path="{ record }"><span v-if="readonly">{{ inputFieldOptions.find(item => item.value === record.path)?.label || record.path }}</span><a-select v-else v-model="record.path" size="small" :options="inputFieldOptions" placeholder="选择输入字段" aria-label="输入字段" allow-search /></template>
          <template #reference="{ record }"><code>{{ reference(record.name) }}</code></template>
          <template #actions="{ rowIndex }"><MangoTableActions :actions="readonly ? [] : [{ label: '移除', danger: true, disabled: config.input_variables.length === 1, onClick: () => config.input_variables.splice(rowIndex, 1) }]" /></template>
        </a-table>
        <JsonDisplay v-if="previewResult" :data="previewResult" :show-drawer-button="false" />
        <a-form-item label="条目组织" class="mango-dataset-config-sequence"><span v-if="readonly">{{ options('evaluation_sequence').find(item => item.value === config.workflow.sequence)?.label || config.workflow.sequence }}</span><a-select v-else v-model="config.workflow.sequence" size="small" :options="options('evaluation_sequence')" /></a-form-item>
        </div>
      </section>
      <a-alert v-if="error" type="error">{{ error }}</a-alert>
    </a-form>
    <template #footer-buttons><a-space><a-button v-if="!readonly"  type="primary" size="small" :loading="saving" @click="save">保存</a-button><a-button size="small" :disabled="saving" @click="visible = false">{{ readonly ? '关闭' : '取消' }}</a-button></a-space></template>
  </BaseSidePanel>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import SchemaEditor from './SchemaEditor.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import usePermissionStore from '@/store/modules/permission'
  import { updateDatasetVersion, previewDatasetInputs } from '@/api/evaluation'
  import { cloneDatasetConfig, defaultDatasetInputs, defaultDatasetWorkflow, inputVariableColumns, datasetConfigurationError } from '../dataset/workflow'
  const emit = defineEmits<{ (event: 'saved', value: any): void }>()
  const permissions = usePermissionStore(), enums = useEnum()
  const visible = ref(false), version = ref<any>(), config = ref<any>({}), sample = ref<any>(), previewResult = ref<any>(), saving = ref(false), previewing = ref(false), error = ref('')
  const fieldSections = [{ key: 'input_schema', title: '输入' }, { key: 'expected_schema', title: '期望输出' }, { key: 'context_schema', title: '评分依据' }]
  let generation = 0
  const readonly = computed(() => version.value?.status !== 'draft')
  const sampleAvailable = computed(() => sample.value !== undefined)
  const options = (key: string) => ((enums as any)[key] || []).map((item: any) => ({ label: item.title, value: item.key }))
  const reference = (name: string) => '${{' + name + '}}'
  const variableColumns = computed(() => inputVariableColumns.filter(column => {
    if (column.slotName === 'actions') return !readonly.value
    if (column.slotName === 'path') return config.value.input_variables?.length > 1 || config.value.input_variables?.some((item: any) => item.path !== '$')
    return true
  }))
  const variableTableWidth = computed(() => variableColumns.value.reduce((width, column) => width + column.width, 0))
  const inputFieldOptions = computed(() => {
    const fields = new Map<string, string>([['$', '完整输入']])
    function collect(schema: any, value: any, path: string, label: string, depth: number) {
      if (depth > 5) return
      const keys = new Set([...Object.keys(schema?.properties || {}), ...Object.keys(value && typeof value === 'object' && !Array.isArray(value) ? value : {})])
      for (const key of keys) {
        const child = schema?.properties?.[key]
        const next = path + (/^[A-Za-z_][A-Za-z0-9_]*$/.test(key) ? '.' + key : '[' + JSON.stringify(key) + ']')
        const title = label + (child?.title || key)
        fields.set(next, title)
        collect(child, value?.[key], next, title + ' / ', depth + 1)
      }
    }
    collect(config.value.input_schema, sample.value, '$', '', 0)
    for (const variable of config.value.input_variables || []) if (!fields.has(variable.path)) fields.set(variable.path, variable.path.replace(/^\$\.?/, '') || '完整输入')
    return [...fields].map(([value, label]) => ({ value, label }))
  })
  function open(record: any, input?: any) {
    if (saving.value)
    return;
    generation++
    version.value = record
    sample.value = input
    previewResult.value = undefined
    previewing.value = false
    error.value = ''
    config.value = cloneDatasetConfig({ ...record.schema_snapshot, input_variables: record.schema_snapshot?.input_variables || defaultDatasetInputs(), workflow: record.schema_snapshot?.workflow || defaultDatasetWorkflow() })
    visible.value = true
  }
  async function preview() { const current = generation; previewing.value = true; try { const response: any = await previewDatasetInputs(version.value.id, { input_variables: config.value.input_variables, input_data: sample.value }); if (current === generation) previewResult.value = response.data } finally { if (current === generation) previewing.value = false } }
  async function save() { error.value = datasetConfigurationError(config.value); if (error.value || readonly.value || saving.value) return; saving.value = true; const current = generation; try { const schema = cloneDatasetConfig(config.value); schema.workflow = { ...schema.workflow, preparation: 'none', steps: [], bindings: [] }; const response: any = await updateDatasetVersion(version.value.id, { schema_snapshot: schema }); if (current !== generation) return; emit('saved', response.data); visible.value = false; Message.success('数据集配置已保存') } finally { saving.value = false } }
  defineExpose({ open })
</script>
<style scoped>
  .mango-dataset-flow { min-width: 0; display: flex; flex-direction: column; gap: 20px; }
  .mango-dataset-config-heading { margin: 0; font-size: 15px; line-height: 24px; font-weight: 600; color: var(--m-text); }
  .mango-dataset-config-subtitle { margin: 0 0 var(--m-page-gap); font-size: 13px; line-height: 20px; font-weight: 500; color: var(--m-text-2); }
  .mango-dataset-config-section + .mango-dataset-config-section { padding-top: 16px; border-top: 1px solid var(--m-border); }
  .mango-dataset-config-fields { margin-top: 12px; padding-inline-start: 16px; min-width: 0; }
  .mango-dataset-config-field-body, .mango-dataset-config-input-body { padding-inline-start: 16px; min-width: 0; }
  .mango-dataset-config-toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--m-page-gap); margin-bottom: 12px; }
  .mango-dataset-config-sequence { margin-top: 12px; margin-bottom: 0; max-width: 420px; }
  .mango-dataset-flow code { overflow-wrap: anywhere; }
</style>
