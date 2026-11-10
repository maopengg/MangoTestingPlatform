<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :width="560"
    :title="editingId === null ? '绑定环境数据库' : '编辑环境数据库'"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <template v-if="optionsError"><a-button size="small" :loading="optionsLoading" @click="loadOptions">重新加载</a-button></template>
    <a-form auto-label-width :disabled="saving" layout="horizontal" :model="draft" class="mango-binding-editor-form mango-simple-form">
      <a-form-item class="mango-form-item__require mango-simple-form-item" label="测试环境">
        <a-select
          v-model="draft.environment"
          :field-names="fieldNames"
          :options="bindingEnvironmentOptions"
          :disabled="editingId !== null"
          placeholder="请选择测试环境"
          value-key="key"
          data-testid="qa-views-config-product-datasource-select-请选择测试环境-2"
        />
      </a-form-item>
      <a-form-item class="mango-form-item__require mango-simple-form-item" label="数据库配置">
        <a-select
          v-model="draft.dataSource"
          :options="dataSourceOptions"
          :loading="optionsLoading"
          allow-search
          placeholder="请选择全局数据库配置"
          data-testid="qa-views-config-product-datasource-select-请选择全局数据库配置"
        />
      </a-form-item>
      <DataSourceTargetFields
        :disabled="saving"
        v-model="draft.target"
        :source-id="draft.dataSource"
        :source-type="
          dataSourceOptions.find((item) => item.value === draft.dataSource)?.db_type ?? -1
        "
      />
      <a-form-item class="mango-simple-form-item" label="读取权限">
        <a-switch v-model="draft.allowQuery" />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="写入权限">
        <a-switch v-model="draft.allowWrite" :disabled="draft.environment === 2" />
        <span v-if="draft.environment === 2" class="mango-muted-text">
          生产环境禁止开启写入权限
        </span>
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    postDataFactoryDatasourceBinding,
    putDataFactoryDatasourceBinding,
  } from '@/api/data-factory'
  import { getSystemDataSource } from '@/api/system/data_source'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'
  import DataSourceTargetFields from '@/components/forms/DataSourceTargetFields.vue'
  import { bindingDataSource, connectionName, sourceLabel, requestError } from '../form'
  import { useProductDatasourceScope } from '../composables/useProductDatasourceScope'
  import type {
    LogicalSource,
    LogicalBinding,
    SourceConnection,
    BindingTarget,
    EntityId,
  } from '../types'
  const props = defineProps<{
    alias: LogicalSource | null
    bindings: LogicalBinding[]
    productId: EntityId | null
  }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum()
  const visible = ref(false),
    saving = ref(false),
    optionsLoading = ref(false),
    optionsError = ref('')
  const editingId = ref<number | null>(null)
  const draft = reactive({
    environment: null as number | null,
    dataSource: null as number | null,
    allowQuery: true,
    allowWrite: false,
    target: { database_name: '', schema_name: '', redis_db: null } as BindingTarget,
  })
  const dataSourceOptions = ref<Array<{ value: number; db_type: number; label: string }>>([])
  let session = 0,
    optionsRequest = 0
  const scope = useProductDatasourceScope(() => [props.productId, props.alias?.id], close)
  const bindingEnvironmentOptions = computed(() => {
    const bound = new Set(
      props.bindings.filter((item) => item.environment !== null).map((item) => item.environment)
    )
    return (enumStore.environment_type || []).map((item) => ({
      ...item,
      disabled: editingId.value === null && bound.has(Number(item.key)),
      title:
        editingId.value === null && bound.has(Number(item.key))
          ? `${item.title}（已绑定）`
          : item.title,
    }))
  })
  function open(record?: LogicalBinding) {
    if (!scope.isActive() || saving.value || !props.alias || props.productId === null) return
    if (
      !record &&
      bindingEnvironmentOptions.value.length &&
      bindingEnvironmentOptions.value.every((item) => item.disabled)
    ) {
      Message.warning('当前逻辑数据库已绑定全部测试环境，请编辑现有绑定')
      return
    }
    ++session
    editingId.value = record?.id ?? null
    Object.assign(draft, {
      environment: record?.environment ?? null,
      dataSource: record
        ? bindingDataSource(record)?.id ??
          (typeof record.database === 'number' ? record.database : null)
        : null,
      allowQuery: record ? record.db_c_status === 1 : true,
      allowWrite: record?.db_rud_status === 1,
      target: {
        database_name: record?.database_name ?? '',
        schema_name: record?.schema_name ?? '',
        redis_db: record?.redis_db ?? null,
      },
    })
    visible.value = true
    dataSourceOptions.value = []
    void loadOptions()
  }
  function close() {
    ++session
    ++optionsRequest
    visible.value = false
    optionsLoading.value = false
    optionsError.value = ''
  }
  async function loadOptions() {
    if (!visible.value || !props.alias || !scope.isActive()) return
    const request = ++optionsRequest,
      version = scope.snapshot(),
      alias = { ...props.alias }
    optionsLoading.value = true
    optionsError.value = ''
    try {
      const response = await getSystemDataSource({ page: 1, pageSize: 999 })
      if (request !== optionsRequest || !scope.current(version)) return
      dataSourceOptions.value = (response.data || [])
        .filter(
          (item: SourceConnection) =>
            item.source_category === alias.source_category && item.db_type === alias.db_type
        )
        .map((item: SourceConnection) => ({
          value: item.id,
          db_type: item.db_type,
          label: [
            sourceLabel(item),
            connectionName(item) !== sourceLabel(item) ? connectionName(item) : null,
            `${item.host}:${item.port}`,
          ]
            .filter(Boolean)
            .join(' · '),
        }))
    } catch (error: unknown) {
      if (request === optionsRequest && scope.current(version))
        void (reportLoadError(error, "加载失败，请重试", false), optionsError.value = requestError(error))
    } finally {
      if (request === optionsRequest) optionsLoading.value = false
    }
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || optionsLoading.value || !scope.isActive() || !props.alias)
      return false
    if ((editingId.value === null && draft.environment == null) || draft.dataSource == null) {
      Message.error('请选择测试环境和数据库配置')
      return false
    }
    if (
      editingId.value === null &&
      props.bindings.some(
        (item) => Number(item.environment) === draft.environment && item.environment !== null
      )
    ) {
      Message.error('当前逻辑数据库已绑定该测试环境，请编辑现有绑定或先解绑')
      return false
    }
    const current = session,
      version = scope.snapshot(),
      id = editingId.value,
      payload = {
        data_source: draft.dataSource,
        ...draft.target,
        db_c_status: draft.allowQuery ? 1 : 0,
        db_rud_status: draft.environment === 2 ? 0 : draft.allowWrite ? 1 : 0,
      }
    saving.value = true
    try {
      const response = await (id === null
        ? postDataFactoryDatasourceBinding({
            ...payload,
            datasource_alias: props.alias.id,
            environment: draft.environment,
          })
        : putDataFactoryDatasourceBinding({ ...payload, id }))
      if (current !== session || !scope.current(version)) return false
      Message.success(response.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  defineExpose({ open, close })
</script>
