<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    :visible="visible"
    :title="recordId === null ? '新增灰度开关' : '编辑灰度开关'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error" class="mango-feature-editor-error"
      >保存失败或结果未确认，输入已保留，请核对后重试。</a-alert
    >



    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving">
      <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item"
        ><ProjectProductSelect
          v-model="form.project_product"
          :disabled="saving"
          placeholder="请选择项目/产品"
          @change="onProductChange"
      /></a-form-item>
      <a-form-item label="模块" class="mango-form-item__require mango-simple-form-item"
        ><ProductModuleSelect
          v-model="form.module"
          :project-product-id="idOf(form.project_product)"
          :auto-clear="false"
          :disabled="saving"
          placeholder="请选择模块"
      /></a-form-item>
      <a-form-item label="灰度编号" class="mango-form-item__require mango-simple-form-item"
        ><a-input v-model="form.gray_code" placeholder="请输入灰度编号"
      /></a-form-item>
      <a-form-item label="灰度名称" class="mango-form-item__require mango-simple-form-item"
        ><a-input v-model="form.name" placeholder="请输入灰度名称"
      /></a-form-item>
      <a-form-item label="配置类型" class="mango-form-item__require mango-simple-form-item"
        ><a-select
          v-model="form.config_type"
          :options="configTypeOptions"
          placeholder="请选择配置类型"
      /></a-form-item>
      <a-form-item label="灰度Key" class="mango-form-item__require mango-simple-form-item"
        ><a-input v-model="form.feature_key" placeholder="请输入灰度Key"
      /></a-form-item>
      <a-form-item v-if="form.config_type === 1" label="配置文件" class="mango-form-item__require mango-simple-form-item"
        ><a-select
          v-model="form.yaml_file"
          :options="yamlOptions"
          :loading="yamlLoading"
          allow-search
          placeholder="请选择配置文件"
      /></a-form-item>
      <a-form-item v-if="form.config_type === 2" label="逻辑数据源" class="mango-form-item__require mango-simple-form-item"
        ><a-select
          v-model="form.datasource_alias"
          :options="aliasOptions"
          :loading="aliasesLoading || enumLoading"
          allow-clear
          allow-search
          placeholder="请选择逻辑数据源"
      /></a-form-item>
      <template v-if="form.config_type === 2">
        <a-form-item label="执行SQL" class="mango-form-item__require mango-simple-form-item"
          ><a-textarea
            v-model="form.enable_sql"
            :auto-size="{ minRows: 3, maxRows: 8 }"
            placeholder="请输入执行SQL"
        /></a-form-item>
        <a-form-item label="关闭SQL" class="mango-form-item__require mango-simple-form-item"
          ><a-textarea
            v-model="form.disable_sql"
            :auto-size="{ minRows: 2, maxRows: 6 }"
            placeholder="请输入关闭灰度时使用的SQL"
        /></a-form-item>
        <a-form-item label="恢复SQL" class="mango-form-item__require mango-simple-form-item"
          ><a-textarea
            v-model="form.restore_sql"
            :auto-size="{ minRows: 2, maxRows: 6 }"
            placeholder="执行完成后用于恢复配置"
        /></a-form-item>
      </template>
      <template v-if="form.config_type === 3">
        <a-form-item label="执行代码" class="mango-form-item__require mango-simple-form-item"
          ><a-textarea
            v-model="form.enable_code"
            :auto-size="{ minRows: 4, maxRows: 10 }"
            placeholder="必须定义 gray(context) 函数"
        /></a-form-item>
        <a-form-item label="关闭代码" class="mango-form-item__require mango-simple-form-item"
          ><a-textarea
            v-model="form.disable_code"
            :auto-size="{ minRows: 3, maxRows: 8 }"
            placeholder="关闭灰度时使用，必须定义 gray(context) 函数"
        /></a-form-item>
        <a-form-item label="恢复代码" class="mango-form-item__require mango-simple-form-item"
          ><a-textarea
            v-model="form.restore_code"
            :auto-size="{ minRows: 3, maxRows: 8 }"
            placeholder="执行完成后用于恢复配置，必须定义 gray(context) 函数"
        /></a-form-item>
      </template>
      <a-form-item class="mango-simple-form-item" label="启用状态"
        ><a-switch v-model="form.status" :checked-value="1" :unchecked-value="0"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="说明"
        ><a-textarea
          v-model="form.description"
          :auto-size="{ minRows: 3, maxRows: 6 }"
          placeholder="请输入说明"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getGrayYamlFile, postGrayFeature, putGrayFeature } from '@/api/gray'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import { configTypeOptions } from '../config'
  import {
    createForm,
    contextOf,
    idOf,
    object,
    parseAliases,
    parseYamlOptions,
    payload,
    validation,
  } from '../editor-form'
  import type { ContextSource, FeatureForm, FeatureRecord, Option, Selection } from '../editor-form'
  const props = defineProps<{ contextKey: ContextSource; blocked: boolean }>()
  const contextKey = computed(() => contextOf(props.contextKey))
  const emit = defineEmits<{
    (event: 'saved', id: number): void
    (event: 'busy', value: boolean): void
    (event: 'visible', value: boolean): void
  }>()
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false),
    recordId = ref<number | null>(null)
  const form: FeatureForm = reactive(createForm()),
    original = ref<{ yaml: Option | null; alias: Option | null } | null>(null)
  const yamlRows = ref<Option[]>([]),
    aliasRows = ref<Option[]>([])
  const yamlLoading = ref(false),
    yamlError = ref(false),
    aliasesLoading = ref(false),
    aliasesError = ref(false),
    enumLoading = ref(false),
    enumError = ref(false)
  const enums = useEnum()
  let active = true,
    generation = 0,
    yamlSequence = 0,
    aliasSequence = 0,
    enumSequence = 0,
    previousProduct: number | null = null
  const current = (version: number) => active && visible.value && version === generation
  const canCancel = () => !saving.value
  const yamlOptions = computed(() =>
    optionsWithSource(yamlRows.value, original.value?.yaml, form.yaml_file)
  )
  const aliasOptions = computed(() =>
    optionsWithSource(aliasRows.value, original.value?.alias, form.datasource_alias).map((row) => ({
      ...row,
      label:
        row.db_type === undefined
          ? row.label
          : `${row.label} / ${
              enums.data_source_type.find((option) => option.key === row.db_type)?.title ??
              row.db_type
            }`,
    }))
  )
  function optionsWithSource(
    rows: Option[],
    source: Option | null | undefined,
    selected: number | string | null
  ) {
    const id = idOf(selected)
    return id !== null && !rows.some((row) => row.value === id)
      ? [...rows, source?.value === id ? source : { value: id, label: `ID ${id}` }]
      : rows
  }
  function sourceOption(value: FeatureRecord['yaml_file']): Option | null {
    const id = idOf(value)
    return id === null
      ? null
      : {
          value: id,
          label: value && typeof value === 'object' ? value.name || `ID ${id}` : `ID ${id}`,
          ...(value && typeof value === 'object' && value.db_type !== undefined
            ? { db_type: value.db_type }
            : {}),
        }
  }
  function reset() {
    ++generation
    ++yamlSequence
    ++aliasSequence
    ++enumSequence
    visible.value = false
    recordId.value = null
    original.value = null
    yamlRows.value = []
    aliasRows.value = []
    yamlLoading.value = false
    yamlError.value = false
    aliasesLoading.value = false
    aliasesError.value = false
    enumLoading.value = false
    enumError.value = false
    saveError.value = false
    previousProduct = null
    Object.assign(form, createForm())
  }
  function onVisibleChange(value: boolean) {
    if (!value && canCancel()) reset()
  }
  function open(
    record?: FeatureRecord,
    navigation?: { projectProduct: Selection; module: Selection }
  ) {
    if (!active || saving.value || props.blocked || (record && !idOf(record.id))) return
    reset()
    recordId.value = record?.id ?? null
    original.value = record
      ? { yaml: sourceOption(record.yaml_file), alias: sourceOption(record.datasource_alias) }
      : null
    Object.assign(form, createForm(record, navigation))
    previousProduct = idOf(form.project_product)
    visible.value = true
    void loadYaml()
    void loadAliases()
    void loadEnums()
  }
  async function loadYaml() {
    if (!current(generation) || saving.value) return
    const version = generation,
      sequence = ++yamlSequence
    yamlLoading.value = true
    yamlError.value = false
    try {
      const response = await getGrayYamlFile({})
      if (current(version) && sequence === yamlSequence) yamlRows.value = parseYamlOptions(response)
    } catch (loadFailure0) {
      if (current(version) && sequence === yamlSequence) (reportLoadError(loadFailure0, "加载失败，请重试", false), yamlError.value = true)
    } finally {
      if (current(version) && sequence === yamlSequence) yamlLoading.value = false
    }
  }
  async function loadAliases() {
    if (!current(generation) || saving.value) return
    const version = generation,
      sequence = ++aliasSequence,
      productId = idOf(form.project_product)
    aliasRows.value = []
    aliasesError.value = false
    if (productId === null) {
      aliasesLoading.value = false
      return
    }
    aliasesLoading.value = true
    try {
      const response = await getDataFactoryDatasourceAlias({
        project_product: productId,
        status: 1,
        page: 1,
        pageSize: 500,
      })
      if (
        current(version) &&
        sequence === aliasSequence &&
        productId === idOf(form.project_product)
      )
        aliasRows.value = parseAliases(response, productId)
    } catch (loadFailure1) {
      if (current(version) && sequence === aliasSequence) (reportLoadError(loadFailure1, "加载失败，请重试", false), aliasesError.value = true)
    } finally {
      if (current(version) && sequence === aliasSequence) aliasesLoading.value = false
    }
  }
  async function loadEnums() {
    if (!current(generation) || saving.value) return
    const version = generation,
      sequence = ++enumSequence
    enumLoading.value = true
    enumError.value = false
    try {
      await enums.getEnum()
    } catch (loadFailure2) {
      if (current(version) && sequence === enumSequence) (reportLoadError(loadFailure2, "加载失败，请重试", false), enumError.value = true)
    } finally {
      if (current(version) && sequence === enumSequence) enumLoading.value = false
    }
  }
  function onProductChange(value: Selection) {
    if (saving.value) return
    form.project_product = value
    const id = idOf(value)
    if (id === previousProduct) return
    previousProduct = id
    form.module = null
    form.datasource_alias = null
    original.value = original.value ? { yaml: original.value.yaml, alias: null } : null
    void loadAliases()
  }
  async function save() {
    if (!current(generation) || saving.value || props.blocked) return false
    const message = validation(form)
    if (message) {
      Message.warning(message)
      return false
    }
    const version = generation,
      request = payload(form, recordId.value)
    saving.value = true
    saveError.value = false
    emit('busy', true)
    try {
      const response = await (recordId.value === null
        ? postGrayFeature(request)
        : putGrayFeature(request))
      if (!current(version)) return false
      const row = object(response.data),
        id = idOf(row.id)
      if (
        response.code !== 200 ||
        id === null ||
        ('id' in request && request.id !== id) ||
        row.project_product !== request.project_product ||
        row.module !== request.module ||
        row.config_type !== request.config_type ||
        row.status !== request.status
      )
        throw Error('Invalid feature acknowledgment')
      reset()
      Message.success('保存成功')
      emit('saved', id)
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
      emit('busy', false)
    }
    return false
  }
  watch(visible, (value) => emit('visible', value), { flush: 'sync' })
  watch(contextKey, reset, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    reset()
  })
  defineExpose({ open })
</script>
<style scoped>
  .mango-feature-editor-error {
    margin-bottom: var(--m-page-gap);
  }
</style>
