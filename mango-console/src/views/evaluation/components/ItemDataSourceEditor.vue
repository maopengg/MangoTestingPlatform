<template>
  <section class="mango-item-source">
    <h3 class="mango-section-title">数据来源</h3>
    <div class="mango-item-source-body">
      <a-form-item label="来源类型"
        ><a-select
          :model-value="source.kind"
          :options="sourceTypes"
          :disabled="disabled"
          @change="changeKind"
      /></a-form-item>
      <template v-if="source.kind === 'sql'">
        <a-form-item label="项目产品" required
          ><ProjectProductSelect
            :model-value="source.binding?.project_product_id"
            :disabled="disabled"
            @update:model-value="setProduct"
        /></a-form-item>
        <DataSourceOperationList
          :data-list="sqlRows"
          :datasource-options="resources"
          :datasource-loading="loading"
          :project-product-id="source.binding?.project_product_id"
          :show-environment="false"
          key-placeholder="例如：contract_id,contract_name"
          :show-delete="false"
          :show-test="false"
          :disabled="disabled || !source.binding?.project_product_id"
          :on-save="saveSql"
          :on-draft-change="saveSql"
          @open-datasources="loadResources()"
          @search-datasource="loadResources($event)"
          @load-more-datasources="loadResources(search, true)"
        />
      </template>
      <template v-else-if="source.kind === 'api_info'">
        <a-form-item label="项目产品" required
          ><ProjectProductSelect
            :model-value="source.binding?.project_product_id"
            :disabled="disabled"
            @update:model-value="setProduct"
        /></a-form-item>
        <a-form-item label="接口模块" required
          ><ProductModuleSelect
            :model-value="source.module_id"
            :project-product-id="source.binding?.project_product_id"
            :selectable-level="0"
            check-strictly
            :disabled="disabled || !source.binding?.project_product_id"
            @update:model-value="setModule"
        /></a-form-item>
        <a-form-item label="参考接口" required
          ><a-select
            :model-value="source.binding?.ref_id"
            :options="resources"
            :loading="loading"
            :disabled="disabled || !source.module_id"
            allow-search
            :filter-option="false"
            placeholder="选择已发布的 HTTP / SSE 接口"
            @change="setApi"
            @search="loadResources($event)"
            @popup-visible-change="(visible) => visible && loadResources()"
            @dropdown-reach-bottom="loadResources(search, true)"
        /></a-form-item>
        <a-form-item label="接口变量"
          ><DataFieldsEditor
            :model-value="source.parameters || {}"
            :disabled="disabled"
            @update:model-value="update({ parameters: $event })"
        /></a-form-item>
        <a-form-item label="响应变量" required>
          <div class="mango-reference-variables">
            <div
              v-for="(variable, index) in source.variables || []"
              :key="index"
              class="mango-reference-variable-row"
            >
              <a-input
                :model-value="variable.name"
                placeholder="变量名称"
                aria-label="变量名称"
                :disabled="disabled"
                @update:model-value="setVariable(index, { name: $event })"
              />
              <a-input
                :model-value="variable.path"
                placeholder="JSONPath，如 $.json.data.id"
                aria-label="响应 JSONPath"
                :disabled="disabled"
                @update:model-value="setVariable(index, { path: $event })"
              />
              <a-button
                v-if="!disabled"
                size="small"
                type="text"
                status="danger"
                @click="removeVariable(index)"
                >移除</a-button
              >
            </div>
            <a-button
              v-if="!disabled"
              size="small"
              @click="update({ variables: [...(source.variables || []), { name: '', path: '' }] })"
              >添加变量</a-button
            >
          </div>
        </a-form-item>
      </template>
      <DataFactoryCaseConfigPanel
        v-else-if="source.kind === 'factory'"
        local
        :configs="factoryConfigs"
        :readonly="disabled"
        :project-product-id="source.binding?.project_product_id"
        :show-add-button="!source.binding?.ref_id"
        @update:configs="saveFactory"
      />
      
    </div>
  </section>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { Message } from '@arco-design/web-vue'
  import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import DataFieldsEditor from './DataFieldsEditor.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import { getDatasetWorkflowResources } from '@/api/evaluation'
  import { useEvaluationEnums } from './useEvaluationEnums'
  import type { InputVariable } from '../types'
  import type { DatasetItemSource } from '../dataset/types'
  interface ResourceOption {
    value: number
    label: string
    disabled?: boolean
  }
  interface ResourceRecord {
    id: number
    name: string
    available: boolean
  }
  interface SqlRow {
    datasource_alias: number | string | null
    value: string
    key: string
  }
  interface FactorySelection {
    template?: { id: number; name?: string; project_product?: number | { id: number } }
  }
  function isFactoryTemplate(value: unknown): value is NonNullable<FactorySelection['template']> {
    const validId = (id: unknown): id is number => typeof id === 'number' && Number.isSafeInteger(id) && id >= 0
    if (!value || typeof value !== 'object' || !('id' in value) || !validId(value.id)) return false
    if ('name' in value && value.name !== undefined && typeof value.name !== 'string') return false
    if (!('project_product' in value) || value.project_product === undefined) return true
    const product = value.project_product
    return validId(product) || (product !== null && typeof product === 'object' && 'id' in product && validId(product.id))
  }
  const props = withDefaults(
    defineProps<{ modelValue: DatasetItemSource; versionId: number; disabled?: boolean }>(),
    { disabled: false }
  )
  const emit = defineEmits<{ (event: 'update:modelValue', value: DatasetItemSource): void }>()
  const user = useUserStore(),
    route = useRoute(),
    { options } = useEvaluationEnums()
  const resources = ref<ResourceOption[]>([]),
    loading = ref(false),
    loadError = ref('')
  const search = ref(''),
    page = ref(0),
    count = ref(0)
  const source = computed<DatasetItemSource>(() => props.modelValue || { kind: 'manual' })
  const sourceTypes = computed(() => options('evaluation_item_source'))
  const sqlRows = ref<SqlRow[]>([])
  const factoryConfigs = computed(() =>
    source.value.binding?.ref_id
      ? [
          {
            id: 'local',
            name: 'data',
            template: {
              id: source.value.binding.ref_id,
              name: source.value.binding.name || '已选择模板',
              project_product: source.value.binding.project_product_id,
            },
            field_overrides: source.value.parameters || {},
          },
        ]
      : []
  )
  let generation = 0,
    active = true,
    retryAppend = false
  function selectedOptions() {
    const binding = source.value.binding
    return binding?.ref_id ? [{ value: binding.ref_id, label: binding.name || '已选择资源' }] : []
  }
  function invalidate() {
    ++generation
    loading.value = false
    loadError.value = ''
    resources.value = active ? selectedOptions() : []
    page.value = 0
    count.value = 0
    search.value = ''
  }
  function relationId(value: unknown): number | null {
    const leaf = Array.isArray(value) ? value[value.length - 1] : value
    const id = Number(leaf)
    return Number.isSafeInteger(id) && id > 0 ? id : null
  }
  function update(value: Partial<DatasetItemSource>) {
    if (!props.disabled && active) emit('update:modelValue', { ...source.value, ...value })
  }
  function changeKind(kind: string) {
    if (!props.disabled && active) emit('update:modelValue', { kind, query: '', binding: null })
  }
  function setProduct(value: unknown) {
    const id = relationId(value)
    update({
      binding: id ? { resource: 'item_source', project_product_id: id } : null,
      parameters: {},
      ...(source.value.kind === 'api_info' ? { module_id: null } : {}),
    })
  }
  function setModule(value: unknown) {
    update({
      module_id: relationId(value),
      binding: source.value.binding?.project_product_id
        ? { resource: 'item_source', project_product_id: source.value.binding.project_product_id }
        : null,
      parameters: {},
    })
  }
  function setApi(value: unknown) {
    const id = relationId(value)
    update({
      binding: {
        resource: 'item_source',
        project_product_id: source.value.binding?.project_product_id,
        ...(id
          ? { ref_id: id, name: resources.value.find((item) => item.value === id)?.label || '' }
          : {}),
      },
    })
  }
  function setVariable(index: number, value: Partial<InputVariable>) {
    if (!source.value.variables?.[index]) return
    update({
      variables: source.value.variables.map((variable, i) =>
        i === index ? { ...variable, ...value } : variable
      ),
    })
  }
  function removeVariable(index: number) {
    update({ variables: (source.value.variables || []).filter((_, i) => i !== index) })
  }
  function saveSql() {
    if (props.disabled || !active || source.value.kind !== 'sql') return
    const row = sqlRows.value[0],
      previous = source.value.binding
    if (!row) return
    const id = relationId(row.datasource_alias)
    update({
      query: row.value,
      key: row.key || '',
      binding: id
        ? {
            ...(previous?.ref_id === id ? previous : {}),
            resource: 'item_source',
            project_product_id: previous?.project_product_id,
            ref_id: id,
            name: resources.value.find((item) => item.value === id)?.label || previous?.name || '',
          }
        : previous?.project_product_id
        ? { resource: 'item_source', project_product_id: previous.project_product_id }
        : null,
    })
  }
  function saveFactory(configs: unknown[]) {
    if (props.disabled || !active || source.value.kind !== 'factory') return
    const selection = configs[0]
    const value = selection && typeof selection === 'object' ? (selection as { template?: unknown }).template : undefined
    if (value != null && !isFactoryTemplate(value)) {
      Message.error('场景模板标识无效，请重新选择')
      return
    }
    const template = isFactoryTemplate(value) ? value : undefined, previous = source.value.binding
    const product =
      typeof template?.project_product === 'object'
        ? template.project_product.id
        : template?.project_product
    update({
      binding: template
        ? {
            ...(previous?.ref_id === template.id ? previous : {}),
            resource: 'item_source',
            project_product_id: product,
            ref_id: template.id,
            name: template.name,
          }
        : null,
      parameters: previous?.ref_id === template?.id ? source.value.parameters || {} : {},
    })
  }
  watch(
    () => [source.value.binding?.ref_id, source.value.query, source.value.key],
    () => {
      sqlRows.value = [
        {
          datasource_alias: source.value.binding?.ref_id ?? null,
          value: source.value.query || '',
          key: source.value.key || '',
        },
      ]
    },
    { immediate: true, flush: 'sync' }
  )
  watch(
    () => [
      props.versionId,
      source.value.kind,
      source.value.binding?.project_product_id,
      source.value.module_id,
      route.path,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
    ],
    invalidate,
    { flush: 'sync' }
  )
  watch(
    () => [source.value.binding?.ref_id, source.value.binding?.name],
    () => {
      const chosen = selectedOptions()
      if (
        active &&
        chosen.length &&
        !resources.value.some((item) => item.value === chosen[0].value)
      )
        resources.value.push(...chosen)
    },
    { immediate: true }
  )
  async function loadResources(value = '', append = false) {
    const product = source.value.binding?.project_product_id,
      kind = source.value.kind
    if (
      !active ||
      !product ||
      !['sql', 'api_info'].includes(kind) ||
      (kind === 'api_info' && !source.value.module_id) ||
      (append && (loading.value || page.value * 20 >= count.value))
    )
      return false
    const current = ++generation,
      nextPage = append ? page.value + 1 : 1
    search.value = value
    loading.value = true
    loadError.value = ''
    retryAppend = append
    try {
      const response: { data: { items?: ResourceRecord[]; count?: number } } =
        await getDatasetWorkflowResources(props.versionId, {
          action: kind,
          project_product_id: product,
          ...(kind === 'api_info' ? { module_id: source.value.module_id } : {}),
          search: value,
          page: nextPage,
        })
      if (!active || current !== generation) return false
      const incoming = (response.data?.items || []).map((item) => ({
        value: item.id,
        label:
          item.name + (item.available ? '' : kind === 'api_info' ? '（未发布）' : '（未启用）'),
        disabled: !item.available,
      }))
      const values = append ? [...resources.value, ...incoming] : incoming
      const ids = new Set(values.map((item) => item.value))
      resources.value = [
        ...new Map(
          [...values, ...selectedOptions().filter((item) => !ids.has(item.value))].map((item) => [
            item.value,
            item,
          ])
        ).values(),
      ]
      page.value = nextPage
      count.value = response.data?.count || 0
      return true
    } catch (loadFailure0) {
      if (active && current === generation) (reportLoadError(loadFailure0, "资源加载失败，请重试", false), loadError.value = '资源加载失败，请重试')
      return false
    } finally {
      if (current === generation) loading.value = false
    }
  }
  function retryResources() {
    return loadResources(search.value, retryAppend)
  }
  function stop() {
    active = false
    invalidate()
  }
  onDeactivated(stop)
  onBeforeUnmount(stop)
  onActivated(() => {
    if (!active) {
      active = true
      invalidate()
    }
  })
</script>

<style scoped>
  .mango-item-source {
    min-width: 0;
  }
  .mango-item-source-body {
    padding-inline-start: 16px;
    min-width: 0;
  }
  .mango-item-source > h3 {
    margin: 0 0 var(--m-page-gap);
    font-size: var(--m-font-body);
  }
  .mango-reference-variables {
    width: 100%;
    min-width: 0;
  }
  .mango-reference-variable-row {
    display: grid;
    grid-template-columns: minmax(100px, 1fr) minmax(180px, 2fr) auto;
    gap: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
  }
  @media (max-width: 900px) {
    .mango-reference-variable-row {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
