<template>
  <section class="mango-item-source">
    <h3 class="mango-section-title">数据来源</h3>
    <div class="mango-item-source-body">
    <a-form-item label="来源类型"><a-select :model-value="source.kind" :options="sourceTypes" :disabled="disabled" @change="changeKind" /></a-form-item>
    <template v-if="source.kind === 'sql'">
      <a-form-item label="项目产品" required><ProjectProductSelect :model-value="source.binding?.project_product_id" :disabled="disabled" @update:model-value="setProduct" /></a-form-item>
      <DataSourceOperationList :data-list="sqlRows" :datasource-options="resources" :datasource-loading="loading" :project-product-id="source.binding?.project_product_id" :show-environment="false" key-placeholder="例如：contract_id,contract_name" :show-delete="false" :show-test="false" :disabled="disabled || !source.binding?.project_product_id" :on-save="saveSql" :on-draft-change="saveSql"
        @open-datasources="loadResources()" @search-datasource="loadResources($event)" @load-more-datasources="loadResources(search, true)" />
    </template>
    <template v-else-if="source.kind === 'api_info'">
      <a-form-item label="项目产品" required><ProjectProductSelect :model-value="source.binding?.project_product_id" :disabled="disabled" @update:model-value="setProduct" /></a-form-item>
      <a-form-item label="接口模块" required><ProductModuleSelect :model-value="source.module_id" :project-product-id="source.binding?.project_product_id" :selectable-level="0" check-strictly :disabled="disabled || !source.binding?.project_product_id" @update:model-value="setModule" /></a-form-item>
      <a-form-item label="参考接口" required><a-select :model-value="source.binding?.ref_id" :options="resources" :loading="loading" :disabled="disabled || !source.module_id" allow-search :filter-option="false" placeholder="选择已发布的 HTTP / SSE 接口" @change="setApi" @search="loadResources($event)" @popup-visible-change="visible => visible && loadResources()" @dropdown-reach-bottom="loadResources(search, true)" /></a-form-item>
      <a-form-item label="接口变量"><DataFieldsEditor :model-value="source.parameters || {}" :disabled="disabled" @update:model-value="update({ parameters: $event })" /></a-form-item>
      <a-form-item label="响应变量" required>
        <div class="mango-reference-variables">
          <div v-for="(variable, index) in source.variables || []" :key="index" class="mango-reference-variable-row">
            <a-input :model-value="variable.name" placeholder="变量名称" aria-label="变量名称" :disabled="disabled" @update:model-value="setVariable(index, { name: $event })" />
            <a-input :model-value="variable.path" placeholder="JSONPath，如 $.json.data.id" aria-label="响应 JSONPath" :disabled="disabled" @update:model-value="setVariable(index, { path: $event })" />
            <a-button v-if="!disabled" size="small" type="text" status="danger" @click="update({ variables: source.variables.filter((_: any, i: number) => i !== index) })">移除</a-button>
          </div>
          <a-button v-if="!disabled" size="small" @click="update({ variables: [...source.variables || [], { name: '', path: '' }] })">添加变量</a-button>
        </div>
      </a-form-item>
    </template>
    <DataFactoryCaseConfigPanel v-else-if="source.kind === 'factory'" local :configs="factoryConfigs" :readonly="disabled" readonly-permission="data_factory.template:read" local-permission="evaluation.dataset:change" :project-product-id="source.binding?.project_product_id" :show-add-button="!source.binding?.ref_id" @update:configs="saveFactory" />
    </div>
  </section>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import DataFieldsEditor from './DataFieldsEditor.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import { getDatasetWorkflowResources } from '@/api/evaluation'
  import { useEnum } from '@/store/modules/get-enum'
  const props = withDefaults(defineProps<{ modelValue: any; versionId: number; disabled?: boolean }>(), { disabled: false })
  const emit = defineEmits<{ (event: 'update:modelValue', value: any): void }>()
  const enums = useEnum(), resources = ref<any[]>([]), loading = ref(false), search = ref(''), page = ref(0), count = ref(0)
  const source = computed(() => ({ kind: 'manual', ...props.modelValue }))
  const sourceTypes = computed(() => ((enums as any).evaluation_item_source || []).map((item: any) => ({ label: item.title, value: item.key })))
  const sqlRows = ref<any[]>([])
  const factoryConfigs = computed(() => source.value.binding?.ref_id ? [{ id: 'local', name: 'data', template: { id: source.value.binding.ref_id, name: source.value.binding.name || '已选择模板', project_product: source.value.binding.project_product_id }, field_overrides: source.value.parameters || {} }] : [])
  let generation = 0
  function update(value: any) { if (!props.disabled) emit('update:modelValue', { ...source.value, ...value }) }
  function changeKind(kind: string) { if (!props.disabled) emit('update:modelValue', { kind, query: '', binding: null }) }
  function setProduct(value: any) { const id = Array.isArray(value) ? value[value.length - 1] : value; update({ binding: id ? { resource: 'item_source', project_product_id: id } : null, parameters: {}, ...(source.value.kind === 'api_info' ? { module_id: null } : {}) }) }
  function setModule(value: any) { update({ module_id: value || null, binding: source.value.binding?.project_product_id ? { resource: 'item_source', project_product_id: source.value.binding.project_product_id } : null, parameters: {} }) }
  function setApi(value: any) { update({ binding: value ? { resource: 'item_source', project_product_id: source.value.binding?.project_product_id, ref_id: value, name: resources.value.find(item => item.value === value)?.label || '' } : { resource: 'item_source', project_product_id: source.value.binding?.project_product_id } }) }
  function setVariable(index: number, value: any) { update({ variables: source.value.variables.map((variable: any, i: number) => i === index ? { ...variable, ...value } : variable) }) }
  function saveSql() {
    if (props.disabled) return
    const row = sqlRows.value[0], previous = source.value.binding
    update({ query: row.value, key: row.key || '', binding: row.datasource_alias ? { ...(previous?.ref_id === row.datasource_alias ? previous : {}), resource: 'item_source', project_product_id: previous?.project_product_id, ref_id: row.datasource_alias, name: resources.value.find(item => item.value === row.datasource_alias)?.label || previous?.name || '' } : previous?.project_product_id ? { resource: 'item_source', project_product_id: previous.project_product_id } : null })
  }
  function saveFactory(configs: any[]) {
    if (props.disabled) return
    const template = configs[0]?.template, previous = source.value.binding
    const product = template?.project_product?.id || template?.project_product
    update({ binding: template ? { ...(previous?.ref_id === template.id ? previous : {}), resource: 'item_source', project_product_id: product, ref_id: template.id, name: template.name } : null, parameters: previous?.ref_id === template?.id ? source.value.parameters || {} : {} })
  }
  watch(() => props.modelValue, () => { sqlRows.value = [{ datasource_alias: source.value.binding?.ref_id || null, value: source.value.query || '', key: source.value.key || '' }] }, { immediate: true, deep: true })
  watch([() => props.versionId, () => source.value.kind, () => source.value.binding?.project_product_id, () => source.value.module_id], () => { generation++; loading.value = false; resources.value = []; page.value = 0; count.value = 0; search.value = '' })
  watch(() => source.value.binding?.ref_id, () => { const binding = source.value.binding; if (binding?.ref_id && !resources.value.some(item => item.value === binding.ref_id)) resources.value.push({ value: binding.ref_id, label: binding.name || '已选择资源' }) }, { immediate: true })
  async function loadResources(value = '', append = false) {
    const product = source.value.binding?.project_product_id
    if (!product || source.value.kind === 'api_info' && !source.value.module_id || append && (loading.value || page.value * 20 >= count.value)) return
    const current = ++generation, nextPage = append ? page.value + 1 : 1
    search.value = value; loading.value = true
    try {
      const response: any = await getDatasetWorkflowResources(props.versionId, { action: source.value.kind, project_product_id: product, ...(source.value.kind === 'api_info' ? { module_id: source.value.module_id } : {}), search: value, page: nextPage })
      if (current !== generation) return
      const items = (response.data?.items || []).map((item: any) => ({ value: item.id, label: item.name + (item.available ? '' : source.value.kind === 'api_info' ? '（未发布）' : '（未启用）'), disabled: !item.available }))
      resources.value = append ? [...resources.value, ...items] : items
      page.value = nextPage; count.value = response.data?.count || 0
    } finally { if (current === generation) loading.value = false }
  }
</script>
<style scoped>
  .mango-item-source { min-width: 0; }
  .mango-item-source-body { padding-inline-start: 16px; min-width: 0; }
  .mango-item-source > h3 { margin: 0 0 var(--m-page-gap); font-size: var(--m-font-body); }
  .mango-reference-variables { width: 100%; min-width: 0; }
  .mango-reference-variable-row { display: grid; grid-template-columns: minmax(100px, 1fr) minmax(180px, 2fr) auto; gap: var(--m-page-gap); margin-bottom: var(--m-page-gap); }
  @media (max-width: 900px) { .mango-reference-variable-row { grid-template-columns: minmax(0, 1fr); } }
</style>
