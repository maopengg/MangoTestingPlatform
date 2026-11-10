<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="templateVisible"
    :on-before-ok="saveTemplate"
    :ok-loading="templateSaving"
    :title="editingId !== null ? '编辑场景模板' : '新增场景模板'"
    :width="560"
    :closable="!templateSaving"
    :mask-closable="!templateSaving"
    :esc-to-close="!templateSaving"
    :cancel-button-props="{ disabled: templateSaving }"
    unmount-on-close
    @cancel="close"
  >
    
    <a-form auto-label-width
      :model="templateForm"
      layout="horizontal"
      :disabled="templateSaving"
      class="mango-template-form mango-simple-form"
    >
      <a-grid class="mango-simple-form-fields" :cols="2" :col-gap="16">
        <a-grid-item class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="产品" required
            ><ProjectProductSelect
              v-model="templateForm.project_product"
              :disabled="templateSaving"
              @change="onTemplateProjectChange"
          /></a-form-item>
        </a-grid-item>
        <a-grid-item class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="模块名称" required
            ><ProductModuleSelect
              v-model="templateForm.module"
              :disabled="templateSaving"
              :project-product-id="templateForm.project_product"
              :auto-clear="false"
              @change="onTemplateModuleChange"
          /></a-form-item>
        </a-grid-item>
        <a-grid-item class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="实体名称" required
            ><a-select
              v-model="templateForm.entity"
              :options="templateEntityOptions"
              :loading="entityLoading"
              @change="onTemplateEntityChange"
              :field-names="{ value: 'id', label: 'display_name' }"
              :filter-option="filterEntityOption"
              allow-search
          /></a-form-item>
        </a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="场景名称" required
            ><a-input v-model="templateForm.name" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="清理策略"
            ><a-select
              v-model="templateForm.cleanup_strategy"
              :options="enumStore.data_factory_cleanup_strategy"
              :field-names="enumFieldNames"
          /></a-form-item>
        </a-grid-item>
        <a-grid-item class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="默认场景">
            <a-switch v-model="templateForm.is_default" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="场景用途" required>
            <a-select
              v-model="templateForm.usage_scope"
              :options="enumStore.data_factory_template_usage_scope"
              :field-names="enumFieldNames"
              placeholder="请选择场景用途"
              data-testid="qa-views-data-factory-template-select-请选择场景用途"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item class="mango-simple-form-fields" :span="2">
          <a-form-item class="mango-simple-form-item" label="描述"
            ><a-textarea v-model="templateForm.description" :auto-size="{ minRows: 1, maxRows: 4 }"
          /></a-form-item>
        </a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postDataFactoryTemplate, putDataFactoryTemplate } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { enumFieldNames } from '../config'
  import {
    createDraft,
    templatePayload,
    validateDraft,
    filterEntityOption,
    optionId,
  } from '../form'
  import { useTemplateScope } from '../composables/useTemplateScope'
  import { useTemplateEntities } from '../composables/useTemplateEntities'
  import type { TemplateRecord, NavigationDefaults } from '../types'
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'saving-change', id: number | null, pending: boolean): void
  }>()
  const enumStore = useEnum(),
    templateForm = reactive(createDraft()),
    editingId = ref<number | null>(null)
  const templateVisible = ref(false),
    templateSaving = ref(false)
  const entities = useTemplateEntities(),
    { options: templateEntityOptions, loading: entityLoading, error: entityError } = entities
  let session = 0
  const scope = useTemplateScope(close)
  function close() {
    ++session
    templateVisible.value = false
    editingId.value = null
    entities.clear()
    Object.assign(templateForm, createDraft())
  }
  function open(record?: TemplateRecord, defaults?: NavigationDefaults) {
    if (!scope.isActive() || templateSaving.value) return
    close()
    editingId.value = record?.id ?? null
    Object.assign(templateForm, createDraft(record, defaults))
    templateVisible.value = true
    void loadEntities()
  }
  function loadEntities() {
    if (templateVisible.value && scope.isActive())
      return entities.load(templateForm.project_product, templateForm.module)
  }
  function clearConfig() {
    templateForm.field_overrides = {}
    templateForm.output_config = []
  }
  function onTemplateProjectChange(value: unknown) {
    if (templateSaving.value) return
    templateForm.project_product = optionId(value)
    templateForm.module = null
    templateForm.entity = null
    clearConfig()
    entities.clear()
  }
  function onTemplateModuleChange() {
    if (templateSaving.value) return
    templateForm.entity = null
    clearConfig()
    void loadEntities()
  }
  function onTemplateEntityChange() {
    if (templateSaving.value) return
    clearConfig()
  }
  async function saveTemplate(): Promise<boolean> {
    if (!templateVisible.value || templateSaving.value || entityLoading.value || !scope.isActive())
      return false
    const error = validateDraft(templateForm)
    if (error) {
      Message.error(error)
      return false
    }
    const current = session,
      version = scope.snapshot(),
      id = editingId.value,
      payload = templatePayload(templateForm)
    templateSaving.value = true
    emit('saving-change', id, true)
    try {
      const response = await (id === null
        ? postDataFactoryTemplate(payload)
        : putDataFactoryTemplate({ ...payload, id }))
      if (current !== session || !scope.current(version)) return false
      if (Number(response.data?.config_status) === 0)
        Message.warning('配置已保存，待校验后可执行；请通过校验操作完成校验')
      else Message.success(response.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      templateSaving.value = false
      emit('saving-change', id, false)
    }
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-template-form :deep(.arco-form-item-label-col) {
    flex: 0 0 90px;
    width: 90px;
    max-width: none;
    white-space: nowrap;
  }
  .mango-template-form :deep(.arco-form-item-wrapper-col) {
    flex: 1;
    min-width: 0;
    width: auto;
    max-width: none;
  }
</style>
