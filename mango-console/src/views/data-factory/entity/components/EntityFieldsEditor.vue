<template>
  <a-modal
    v-model:visible="fieldVisible"
    :on-before-ok="saveFields"
    :ok-loading="fieldSaving"
    :title="`${currentEntity?.name || ''} 字段规则`"
    :width="1180"
    :closable="!busy"
    :mask-closable="!busy"
    :esc-to-close="!busy"
    :cancel-button-props="{ disabled: busy }"
    unmount-on-close
    @cancel="close"
  >
    <MangoRequestFeedback v-if="operationError" :message="(operationError)" />
    <div class="mango-entity-toolbar mango-entity-field-toolbar">
      <a-space wrap>
        <a-tag color="arcoblue">当前表：{{ currentEntity?.table_name || '-' }}</a-tag>
        <a-button
          :loading="fieldSyncLoading"
          :disabled="busy"
          type="primary"
          @click="syncCurrentEntityFields"
          data-testid="qa-views-data-factory-entity-button-同步当前表字段"
          >同步当前表字段</a-button
        >
        <a-button
          :loading="fieldPreviewLoading"
          :disabled="busy"
          @click="previewFieldValues"
          data-testid="qa-views-data-factory-entity-button-生成实际值"
          >生成实际值</a-button
        >
        <a-switch
          v-model="replaceFields"
          :disabled="busy"
          checked-text="替换"
          unchecked-text="追加"
        />
      </a-space>
      <VariableReferencePanel />
    </div>
    <a-table
      class="mango-native-scroll-table"
      row-key="name"
      :columns="fieldRuleColumns"
      :data="fieldRows"
      :loading="fieldLoading || fieldSyncLoading || fieldPreviewLoading"
      :pagination="false"
      :scroll="{ x: 1620, y: 460 }"
    >
      <template #columns>
        <a-table-column
          v-for="item of fieldRuleColumns"
          :key="item.key"
          :align="item.align"
          :data-index="item.key"
          :fixed="item.fixed"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'label'" #cell="{ record }">
            <a-input v-model="record.label" :disabled="busy" />
          </template>
          <template
            v-else-if="
              ['nullable', 'primary_key', 'autoincrement', 'db_type', 'platform_type'].includes(
                item.key
              )
            "
            #cell="{ record }"
          >
            <DataFactoryFieldTag :record="record" :field="item.key" />
          </template>
          <template v-else-if="item.key === 'generator_type'" #cell="{ record }">
            <a-select
              v-model="record.generator_type"
              :disabled="busy"
              :options="dataFactoryGeneratorOptions"
              :field-names="enumFieldNames"
              @change="() => changeGeneratorType(record)"
            />
          </template>
          <template v-else-if="item.key === 'generator_config'" #cell="{ record }">
            <a-space
              v-if="record.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD"
              direction="vertical"
              fill
            >
              <a-cascader
                :model-value="getDependencyCascaderValue(record)"
                :options="dependencyCascaderOptions"
                :disabled="busy"
                :loading="dependencyLoading"
                :load-more="loadDependencyCascaderMore"
                allow-clear
                allow-search
                path-mode
                placeholder="请选择模块/实体/字段"
                @change="(value) => changeDependencyCascader(record, value)"
                data-testid="qa-views-data-factory-entity-cascader-请选择模块-实体-字段"
              />
            </a-space>
            <a-space
              v-else-if="record.generator_type === GENERATOR_TYPE_ENUM"
              direction="vertical"
              fill
            >
              <a-select
                v-model="record.generator_config.value"
                :disabled="busy"
                :options="getEnumSelectOptions(record)"
                allow-clear
                placeholder="请选择默认枚举值"
                @change="refreshEnumConfigValue(record)"
                data-testid="qa-views-data-factory-entity-select-请选择默认枚举值"
              />
              <a-button
                size="mini"
                type="text"
                @click="openEnumEditor(record)"
                data-testid="qa-views-data-factory-entity-button-配置枚举-项"
              >
                配置枚举（{{ getEnumOptionRows(record).length }}项）
              </a-button>
            </a-space>
            <a-input
              v-else
              v-model="record.generator_config_value"
              :disabled="busy || isReadonlyGeneratorConfig(record)"
              :placeholder="getGeneratorConfigPlaceholder(record)"
            />
          </template>
          <template v-else-if="item.key === 'preview_value'" #cell="{ record }">
            <a-tooltip v-if="record.preview_message" :content="record.preview_message">
              <a-tag :color="record.preview_valid ? 'green' : 'red'">{{
                formatPreviewDisplayValue(record)
              }}</a-tag>
            </a-tooltip>
            <span v-else>{{ formatPreviewValue(record.preview_value) }}</span>
          </template>
          <template v-else-if="item.key === 'sort'" #cell="{ record }">
            <a-input-number v-model="record.sort" :disabled="busy" />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-modal>

  <EntityEnumEditor ref="enumRef" @apply="applyEnum" />
</template>
<script setup lang="ts">
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { computed, ref, watch } from 'vue'
  import type { Ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    getDataFactoryField,
    postDataFactoryDiscoverTable,
    postDataFactoryFieldBatchSave,
    postDataFactoryFieldPreviewValues,
  } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import DataFactoryFieldTag from '@/components/display/DataFactoryFieldTag.vue'
  import EntityEnumEditor from './EntityEnumEditor.vue'
  import { fieldRuleColumns, enumFieldNames } from '../config'
  import { optionId } from '../form'
  import * as generators from '../generators'
  import {
    normalizeFieldRow,
    buildFieldPayloadItem,
    formatPreviewDisplayValue,
    formatPreviewValue,
    changeGeneratorType,
    getEnumSelectOptions,
    getEnumOptionRows,
    refreshEnumConfigValue,
    isReadonlyGeneratorConfig,
    getGeneratorConfigPlaceholder,
    GENERATOR_TYPE_ENUM,
    GENERATOR_TYPE_DEPENDENCY_FIELD,
  } from '../generators'
  import { useEntityScope } from '../composables/useEntityScope'
  import { useEntityDependencies } from '../composables/useEntityDependencies'
  import type {
    EntityRecord,
    FieldRow,
    FieldRecord,
    TableSchema,
    PreviewField,
    EnumOption,
    EnumEditorHandle,
    DependencyOption,
  } from '../types'
  const emit = defineEmits<{ (event: 'saving-change', id: number, pending: boolean): void }>()
  const enumStore = useEnum(),
    userStore = useUserStore(),
    dependencies = useEntityDependencies()
  const {
    options: dependencyCascaderOptions,
    loading: dependencyLoading,
    error: dependencyError,
  } = dependencies
  const fieldVisible = ref(false),
    currentEntity = ref<EntityRecord | null>(null)
  const fieldRows: Ref<FieldRow[]> = ref([])
  const fieldLoading = ref(false),
    fieldSaving = ref(false),
    fieldSyncLoading = ref(false),
    fieldPreviewLoading = ref(false),
    loadError = ref(false),
    operationError = ref('')
  const replaceFields = ref(true),
    enumRef = ref<EnumEditorHandle | null>(null)
  const busy = computed(
    () =>
      fieldLoading.value || fieldSaving.value || fieldSyncLoading.value || fieldPreviewLoading.value
  )
  const dataFactoryGeneratorOptions = computed(() =>
    (enumStore.data_factory_generator_type || [])
      .filter((item) => !generators.REMOVED_GENERATOR_TYPES.includes(Number(item.key)))
      .map((item) => ({ ...item, title: generators.getGeneratorTypeTitle(item) }))
      .sort(
        (a, b) => generators.getGeneratorTypeOrder(a.key) - generators.getGeneratorTypeOrder(b.key)
      )
  )
  let session = 0,
    request = 0,
    revision = 0
  const scope = useEntityScope(close)
  watch(
    fieldRows,
    () => {
      ++revision
    },
    { deep: true, flush: 'sync' }
  )
  function open(record: EntityRecord) {
    if (
      !scope.isActive() ||
      fieldSaving.value ||
      fieldSyncLoading.value ||
      fieldPreviewLoading.value
    )
      return
    close()
    currentEntity.value = { ...record }
    fieldVisible.value = true
    replaceFields.value = true
    void loadFields()
  }
  function close() {
    ++session
    ++request
    fieldVisible.value = false
    currentEntity.value = null
    fieldRows.value = []
    fieldLoading.value = false
    loadError.value = false
    operationError.value = ''
    dependencies.clear()
    enumRef.value?.close()
  }
  async function loadFields() {
    if (!fieldVisible.value || !currentEntity.value || !scope.isActive()) return
    const current = ++request,
      version = scope.snapshot(),
      record = { ...currentEntity.value }
    fieldLoading.value = true
    loadError.value = false
    try {
      const response = await getDataFactoryField({ entity: record.id })
      if (current !== request || !scope.current(version)) return
      fieldRows.value = (response.data || []).map((row: FieldRecord) => normalizeFieldRow(row))
      void dependencies.load(record, fieldRows.value)
    } catch (loadFailure0) {
      if (current === request && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (current === request) fieldLoading.value = false
    }
  }
  async function syncCurrentEntityFields() {
    if (!currentEntity.value || !fieldVisible.value || busy.value || !scope.isActive()) return
    const record = { ...currentEntity.value },
      environment = userStore.selected_environment
    if (!record.table_name || optionId(record.datasource_alias) === null || environment == null) {
      Message.error('请先选择逻辑数据库和顶部测试环境')
      return
    }
    const current = session,
      version = scope.snapshot(),
      fields = fieldRows.value.map(buildFieldPayloadItem)
    fieldSyncLoading.value = true
    operationError.value = ''
    emit('saving-change', record.id, true)
    try {
      const response = await postDataFactoryDiscoverTable({
        datasource_alias_id: optionId(record.datasource_alias),
        project_product: optionId(record.project_product),
        test_env: environment,
        table_name: record.table_name,
        schema_name: record.schema_name || '',
      })
      if (current !== session || !scope.current(version)) return
      const schema: TableSchema = response.data || {},
        existing = new Map(fields.map((field) => [field.name, field]))
      fieldRows.value = (schema.columns || []).map((column, index) => {
        const old = existing.get(column.name)
        return normalizeFieldRow({
          ...old,
          ...column,
          generator_type:
            old?.generator_type ?? column.generator_type ?? column.recommend?.generator_type ?? 1,
          generator_config:
            old?.generator_config ??
            column.generator_config ??
            column.recommend?.generator_config ??
            {},
          label: old?.label || column.label || column.comment || column.name,
          sort: old?.sort ?? index,
        })
      })
      void dependencies.load(record, fieldRows.value)
      Message.success('字段同步完成')
    } catch (requestFailure) {
      if (current === session && scope.current(version))
        operationError.value = requestFailureMessage(requestFailure, '字段同步失败，可重试')
    } finally {
      fieldSyncLoading.value = false
      emit('saving-change', record.id, false)
    }
  }
  async function saveFields(): Promise<boolean> {
    if (
      !fieldVisible.value ||
      !currentEntity.value ||
      busy.value ||
      loadError.value ||
      !scope.isActive()
    )
      return false
    const id = currentEntity.value.id,
      current = session,
      version = scope.snapshot(),
      payload = {
        entity_id: id,
        replace: replaceFields.value,
        fields: fieldRows.value.map(buildFieldPayloadItem),
      }
    fieldSaving.value = true
    operationError.value = ''
    emit('saving-change', id, true)
    try {
      const response = await postDataFactoryFieldBatchSave(payload)
      if (current !== session || !scope.current(version)) return false
      Message.success(response.msg)
      close()
      return true
    } catch (requestFailure) {
      if (current === session && scope.current(version))
        operationError.value = requestFailureMessage(requestFailure, '字段规则保存失败，可重试')
      return false
    } finally {
      fieldSaving.value = false
      emit('saving-change', id, false)
    }
  }
  async function previewFieldValues() {
    if (
      !fieldVisible.value ||
      !currentEntity.value ||
      busy.value ||
      loadError.value ||
      !scope.isActive()
    )
      return
    const environment = userStore.selected_environment
    if (environment == null) {
      Message.error('请先在顶部选择测试环境')
      return
    }
    const id = currentEntity.value.id,
      current = session,
      version = scope.snapshot(),
      draftRevision = revision,
      payload = {
        entity_id: id,
        fields: fieldRows.value.map(buildFieldPayloadItem),
        test_env: environment,
      }
    fieldPreviewLoading.value = true
    operationError.value = ''
    emit('saving-change', id, true)
    try {
      const response = await postDataFactoryFieldPreviewValues(payload)
      if (current !== session || !scope.current(version) || draftRevision !== revision) return
      const values: PreviewField[] = response.data?.fields || [],
        map = new Map(values.map((item) => [item.name, item]))
      fieldRows.value = fieldRows.value.map((row) => {
        const value = map.get(row.name)
        return {
          ...row,
          preview_value: value?.value,
          preview_valid: value?.valid ?? true,
          preview_message: value?.message || '',
        }
      })
      const failed = values.filter((item) => item.valid === false).length
      if (failed) Message.warning(`实际值生成完成，${failed} 个字段生成失败`)
      else Message.success('实际值生成完成')
    } catch (requestFailure) {
      if (current === session && scope.current(version))
        operationError.value = requestFailureMessage(requestFailure, '实际值生成失败，可重试')
    } finally {
      fieldPreviewLoading.value = false
      emit('saving-change', id, false)
    }
  }
  const getDependencyCascaderValue = (row: FieldRow) =>
    dependencies.path(row.generator_config.dependency_entity_id, row.generator_config.field || 'id')
  function loadDependencyCascaderMore(
    option: DependencyOption,
    done: (children?: DependencyOption[]) => void
  ) {
    return dependencies.loadMore(option, done)
  }
  function changeDependencyCascader(row: FieldRow, value: unknown) {
    if (busy.value) return
    const path = Array.isArray(value) ? value : [],
      entity = path.find((item) => String(item).startsWith('entity:')),
      field = path.find((item) => String(item).startsWith('field:'))
    row.generator_config = entity
      ? {
          dependency_entity_id: Number(String(entity).replace('entity:', '')),
          field: field ? String(field).replace('field:', '') : 'id',
        }
      : {}
    refreshEnumConfigValue(row)
  }
  function openEnumEditor(row: FieldRow) {
    if (!busy.value) enumRef.value?.open(row)
  }
  function applyEnum(name: string, options: EnumOption[]) {
    if (busy.value || !fieldVisible.value) return
    const row = fieldRows.value.find((row) => row.name === name)
    if (!row) return
    const values = options.map((option) => option.value)
    row.enum_values = values
    row.generator_config = { ...row.generator_config, options, values }
    if (!values.some((value) => value === row.generator_config.value))
      row.generator_config.value = values[0]
    refreshEnumConfigValue(row)
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-entity-toolbar {
    margin-bottom: var(--m-page-gap);
  }
  .mango-entity-field-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    flex-wrap: wrap;
  }
</style>
