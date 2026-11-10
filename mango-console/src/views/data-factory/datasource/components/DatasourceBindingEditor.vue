<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :width="560"
    :title="editingId === null ? '新增绑定' : '编辑绑定'"
    :on-before-ok="save"
    :ok-loading="saving"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    
    <a-form auto-label-width class="mango-simple-form" :model="draft" layout="horizontal" :disabled="saving">
      <a-form-item class="mango-simple-form-item" label="测试环境" required>
        <a-select
          v-model="draft.environment"
          :options="enumStore.environment_type"
          :field-names="enumFieldNames"
          allow-search
          placeholder="请选择测试环境"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="数据库配置" required>
        <a-select
          v-model="draft.data_source"
          :options="dataSourceOptions"
          :field-names="{ value: 'id', label: 'display_name' }"
          :loading="optionsLoading"
          placeholder="请选择全局数据库配置"
          allow-search
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="读取权限"
        ><a-switch v-model="draft.allowQuery" size="small"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="写入权限"
        ><a-switch
          :model-value="!isProduction(draft.environment) && draft.allowWrite"
          @update:model-value="draft.allowWrite = $event"
          :disabled="isProduction(draft.environment)"
          size="small"
      /></a-form-item>
      <DataSourceTargetFields
        v-model="draft.target"
        :disabled="saving"
        :source-id="draft.data_source"
        :source-type="
          dataSourceOptions.find((item) => item.id === draft.data_source)?.db_type ?? -1
        "
      />
      <a-form-item class="mango-simple-form-item" label="描述"
        ><a-textarea v-model="draft.description" :auto-size="{ minRows: 2, maxRows: 4 }"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    postDataFactoryDatasourceBinding,
    putDataFactoryDatasourceBinding,
  } from '@/api/data-factory'
  import { getSystemDataSource } from '@/api/system/data_source'
  import { useEnum } from '@/store/modules/get-enum'
  import DataSourceTargetFields from '@/components/forms/DataSourceTargetFields.vue'
  import { enumFieldNames } from '../config'
  import { createBindingDraft, bindingPayload, isProduction } from '../form'
  import { useDatasourceScope } from '../composables/useDatasourceScope'
  import type { LogicalSource, LogicalBinding, SourceConnection } from '../types'
  const emit = defineEmits<{
    (event: 'saved', aliasId: number): void
    (event: 'saving-change', aliasId: number, id: number | null, pending: boolean): void
  }>()
  const enumStore = useEnum()
  const visible = ref(false),
    saving = ref(false),
    optionsLoading = ref(false),
    optionsError = ref(false)
  const alias = ref<LogicalSource | null>(null),
    editingId = ref<number | null>(null)
  const draft = reactive(createBindingDraft())
  const dataSourceOptions = ref<SourceConnection[]>([])
  let session = 0,
    optionsRequest = 0
  const scope = useDatasourceScope(close)
  function open(source: LogicalSource, record?: LogicalBinding) {
    if (saving.value || !scope.isActive()) return
    ++session
    alias.value = { ...source }
    editingId.value = record?.id ?? null
    Object.assign(draft, createBindingDraft(record))
    dataSourceOptions.value = []
    visible.value = true
    void loadOptions()
  }
  function close() {
    ++session
    ++optionsRequest
    visible.value = false
    alias.value = null
    editingId.value = null
    dataSourceOptions.value = []
    optionsLoading.value = false
    optionsError.value = false
    Object.assign(draft, createBindingDraft())
  }
  async function loadOptions() {
    if (!visible.value || !alias.value || !scope.isActive()) return
    const request = ++optionsRequest,
      version = scope.snapshot(),
      source = { ...alias.value },
      selected = draft.data_source
    optionsLoading.value = true
    optionsError.value = false
    try {
      const response = await getSystemDataSource({ page: 1, pageSize: 999 })
      if (request !== optionsRequest || !scope.current(version)) return
      dataSourceOptions.value = (response.data || []).filter(
        (item: SourceConnection) =>
          Number(item.source_category) === Number(source.source_category) &&
          Number(item.db_type) === Number(source.db_type)
      )
      if (
        selected !== null &&
        draft.data_source === selected &&
        !dataSourceOptions.value.some((item) => String(item.id) === String(selected))
      )
        draft.data_source = null
    } catch (loadFailure0) {
      if (request === optionsRequest && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), optionsError.value = true)
    } finally {
      if (request === optionsRequest) optionsLoading.value = false
    }
  }
  async function save(): Promise<boolean> {
    if (
      !visible.value ||
      saving.value ||
      optionsLoading.value ||
      optionsError.value ||
      !alias.value ||
      !scope.isActive()
    )
      return false
    if (draft.environment == null || draft.environment === '' || draft.data_source === null) {
      Message.error('请先选择测试环境和数据库配置')
      return false
    }
    const aliasId = alias.value.id,
      id = editingId.value,
      current = session,
      version = scope.snapshot()
    const value = bindingPayload(draft, aliasId),
      payload = id === null ? value : { ...value, id }
    saving.value = true
    emit('saving-change', aliasId, id, true)
    try {
      const response = await (id === null
        ? postDataFactoryDatasourceBinding(payload)
        : putDataFactoryDatasourceBinding(payload))
      if (current !== session || !scope.current(version)) return false
      Message.success(response.msg)
      emit('saved', aliasId)
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
      emit('saving-change', aliasId, id, false)
    }
  }
  defineExpose({ open, close })
</script>
