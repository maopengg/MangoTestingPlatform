<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :width="560"
    :title="editingId === null ? '新增' : '编辑'"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-form-item__require mango-simple-form-item" label="名称">
        <a-input
          v-model="draft.name"
          placeholder="请输入逻辑数据库名称"
          data-testid="qa-views-config-product-datasource-input-请输入逻辑数据库名称"
        />
      </a-form-item>
      <a-form-item class="mango-form-item__require mango-simple-form-item" label="数据库分类">
        <a-select
          v-model="draft.sourceCategory"
          :field-names="fieldNames"
          :options="enumStore.data_source_category"
          :loading="optionsLoading"
          placeholder="请选择数据库分类"
          value-key="key"
          @change="onAliasCategoryChange"
          data-testid="qa-views-config-product-datasource-select-请选择数据库分类"
        />
      </a-form-item>
      <a-form-item class="mango-form-item__require mango-simple-form-item" label="数据库类型">
        <a-select
          v-model="draft.dbType"
          :field-names="fieldNames"
          :options="aliasSourceTypeOptions"
          :loading="optionsLoading"
          placeholder="请选择数据库类型"
          allow-clear
          allow-search
          value-key="key"
          data-testid="qa-views-config-product-datasource-select-请选择数据库类型"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="描述">
        <a-textarea
          v-model="draft.description"
          :auto-size="{ minRows: 3, maxRows: 5 }"
          :max-length="50"
          placeholder="请输入描述"
          show-word-limit
          data-testid="qa-views-config-product-datasource-textarea-请输入描述"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postDataFactoryDatasourceAlias, putDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'
  import { createAliasDraft, aliasPayload } from '../form'
  import { useProductDatasourceScope } from '../composables/useProductDatasourceScope'
  import type { EntityId, LogicalSource } from '../types'
  const props = defineProps<{ productId: EntityId | null; optionsLoading: boolean }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum()
  const visible = ref(false),
    saving = ref(false),
    editingId = ref<number | null>(null)
  const draft = reactive(createAliasDraft())
  let session = 0
  const scope = useProductDatasourceScope(() => [props.productId], close)
  const aliasSourceTypeOptions = computed(() =>
    (enumStore.data_source_type || []).filter(
      (item) => enumStore.data_source_type_category[item.key] === draft.sourceCategory
    )
  )
  function onAliasCategoryChange() {
    draft.dbType = aliasSourceTypeOptions.value.length
      ? Number(aliasSourceTypeOptions.value[0].key)
      : null
  }
  function open(record?: LogicalSource) {
    if (saving.value || !scope.isActive() || props.productId === null) return
    ++session
    editingId.value = record?.id ?? null
    Object.assign(draft, createAliasDraft(record))
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || !scope.isActive() || props.productId === null)
      return false
    if (!draft.name.trim()) {
      Message.error('请输入逻辑数据库名称')
      return false
    }
    if (draft.dbType == null) {
      Message.error('请选择数据库类型')
      return false
    }
    if (draft.description.length > 50) {
      Message.error('描述不能超过50字')
      return false
    }
    const current = session,
      version = scope.snapshot(),
      id = editingId.value,
      payload = aliasPayload(draft, props.productId)
    saving.value = true
    try {
      const response = await (id === null
        ? postDataFactoryDatasourceAlias(payload)
        : putDataFactoryDatasourceAlias({ ...payload, id }))
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
